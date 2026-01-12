"""
Portfolio Assistant Agent - Proposes reallocations and trade lists
Converses with PMs, explains risk/return, proposes reallocations consistent with constraints
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from decimal import Decimal

from .base_agent import BaseAgent
from .message_bus import AgentMessage
from .portfolio_models import (
    Portfolio, RebalanceProposal, Position, PortfolioConstraints, RiskMetrics
)
from .portfolio_storage import portfolio_storage

logger = logging.getLogger(__name__)


class PortfolioAssistantAgent(BaseAgent):
    """Agent that proposes portfolio reallocations and explains risk/return"""
    
    def __init__(self):
        super().__init__("portfolio_assistant", "Portfolio Assistant Agent")
        self.pending_proposals: Dict[str, RebalanceProposal] = {}
    
    async def handle_message(self, message: AgentMessage):
        """Handle incoming messages"""
        if message.message_type == "propose_rebalance":
            await self._handle_propose_rebalance(message)
        elif message.message_type == "explain_risk":
            await self._handle_explain_risk(message)
        elif message.message_type == "optimize_allocation":
            await self._handle_optimize_allocation(message)
    
    async def _handle_propose_rebalance(self, message: AgentMessage):
        """Propose a rebalance for a portfolio"""
        portfolio_id = message.payload.get("portfolio_id")
        reason = message.payload.get("reason", "routine_rebalance")
        auto_approve_threshold = message.payload.get("auto_approve_threshold", Decimal('0.02'))
        
        if not portfolio_id:
            return
        
        portfolio = portfolio_storage.get_portfolio(portfolio_id)
        if not portfolio:
            return
        
        try:
            proposal = await self.create_rebalance_proposal(
                portfolio, reason, auto_approve_threshold
            )
            
            # Save proposal
            portfolio_storage.create_rebalance_proposal(proposal)
            self.pending_proposals[proposal.proposal_id] = proposal
            
            response = AgentMessage(
                message_id=f"resp_{message.message_id}",
                sender=self.agent_id,
                receiver=message.sender,
                message_type="rebalance_proposal",
                payload={
                    "portfolio_id": portfolio_id,
                    "proposal": proposal.dict(),
                    "requires_approval": proposal.requires_approval
                }
            )
            await self.send_message(response)
            
        except Exception as e:
            logger.error(f"Error creating rebalance proposal: {e}", exc_info=True)
    
    async def create_rebalance_proposal(
        self,
        portfolio: Portfolio,
        reason: str,
        auto_approve_threshold: Decimal = Decimal('0.02')
    ) -> RebalanceProposal:
        """Create a rebalance proposal based on current portfolio state"""
        proposal_id = f"rebal_{portfolio.portfolio_id}_{int(datetime.now().timestamp())}"
        
        # Get current risk metrics
        current_metrics = portfolio.current_risk_metrics
        if not current_metrics:
            # Request risk metrics computation
            await self._request_risk_metrics(portfolio.portfolio_id)
            # For now, proceed with basic proposal
            current_metrics = RiskMetrics(portfolio_id=portfolio.portfolio_id)
        
        # Analyze current state and propose changes
        target_allocations = await self._compute_target_allocations(portfolio, current_metrics)
        trades = await self._generate_trade_list(portfolio, target_allocations)
        
        # Determine if approval is required
        requires_approval, approval_reason = self._check_approval_required(
            portfolio, trades, auto_approve_threshold
        )
        
        # Compute expected risk improvement
        risk_improvement = await self._estimate_risk_improvement(portfolio, target_allocations)
        
        proposal = RebalanceProposal(
            proposal_id=proposal_id,
            portfolio_id=portfolio.portfolio_id,
            created_by=self.agent_id,
            trades=trades,
            target_allocations=target_allocations,
            reason=reason,
            risk_improvement=risk_improvement,
            requires_approval=requires_approval,
            approval_required_reason=approval_reason
        )
        
        return proposal
    
    async def _compute_target_allocations(
        self,
        portfolio: Portfolio,
        metrics: RiskMetrics
    ) -> Dict[str, Decimal]:
        """Compute target allocations based on constraints and risk metrics"""
        constraints = portfolio.constraints
        target_allocations = {}
        
        # Start with current allocations
        current_total = sum(pos.value_usd for pos in portfolio.positions.values())
        if current_total == 0:
            return target_allocations
        
        for token_address, position in portfolio.positions.items():
            current_alloc = position.allocation_pct
            
            # Check if position violates constraints
            if current_alloc > constraints.max_position_pct:
                # Reduce to max
                target_allocations[token_address] = constraints.max_position_pct
            elif current_alloc < constraints.min_position_pct and current_alloc > 0:
                # Either increase to min or remove
                # For now, keep at current if above threshold
                target_allocations[token_address] = current_alloc
            else:
                # Keep current allocation (within bounds)
                target_allocations[token_address] = current_alloc
        
        # Check for constraint breaches and adjust
        if metrics.max_position_pct > constraints.max_position_pct:
            # Reduce largest position
            largest_pos = max(
                portfolio.positions.items(),
                key=lambda x: x[1].allocation_pct
            )
            target_allocations[largest_pos[0]] = constraints.max_position_pct
        
        # Normalize allocations to sum to 1.0
        total_target = sum(target_allocations.values())
        if total_target > 0:
            for token_address in target_allocations:
                target_allocations[token_address] = target_allocations[token_address] / total_target
        
        return target_allocations
    
    async def _generate_trade_list(
        self,
        portfolio: Portfolio,
        target_allocations: Dict[str, Decimal]
    ) -> List[Dict[str, Any]]:
        """Generate list of trades to achieve target allocations"""
        trades = []
        current_total = portfolio.total_value_usd
        
        if current_total == 0:
            return trades
        
        # Compute current allocations
        current_allocations = {}
        for token_address, position in portfolio.positions.items():
            current_allocations[token_address] = position.allocation_pct
        
        # Generate trades for each position
        all_tokens = set(list(portfolio.positions.keys()) + list(target_allocations.keys()))
        
        for token_address in all_tokens:
            current_alloc = current_allocations.get(token_address, Decimal('0'))
            target_alloc = target_allocations.get(token_address, Decimal('0'))
            
            # Check if rebalance needed
            drift = abs(target_alloc - current_alloc)
            if drift < portfolio.constraints.rebalance_threshold_pct:
                continue  # Within threshold, no trade needed
            
            # Compute trade size
            target_value = current_total * target_alloc
            current_value = current_total * current_alloc
            trade_value = target_value - current_value
            
            if abs(trade_value) < current_total * Decimal('0.001'):  # Less than 0.1%, skip
                continue
            
            # Determine trade direction
            if trade_value > 0:
                action = "buy"
            else:
                action = "sell"
            
            position = portfolio.positions.get(token_address)
            if position:
                trade_amount = abs(trade_value) / position.current_price if position.current_price > 0 else Decimal('0')
            else:
                # New position
                trade_amount = abs(trade_value)  # Will need price lookup
            
            trades.append({
                "token_address": token_address,
                "token_symbol": position.token_symbol if position else "UNKNOWN",
                "action": action,
                "amount_usd": float(abs(trade_value)),
                "amount_tokens": float(trade_amount),
                "current_allocation": float(current_alloc),
                "target_allocation": float(target_alloc),
                "drift": float(drift)
            })
        
        return trades
    
    def _check_approval_required(
        self,
        portfolio: Portfolio,
        trades: List[Dict[str, Any]],
        auto_approve_threshold: Decimal
    ) -> tuple[bool, Optional[str]]:
        """Check if rebalance requires human approval"""
        if not trades:
            return False, None
        
        total_trade_value = sum(t.get("amount_usd", 0) for t in trades)
        total_value = portfolio.total_value_usd
        
        if total_value == 0:
            return True, "Portfolio has zero value"
        
        trade_pct = Decimal(str(total_trade_value)) / total_value
        
        # Check if any single trade is too large
        max_trade = max((t.get("amount_usd", 0) for t in trades), default=0)
        max_trade_pct = Decimal(str(max_trade)) / total_value if total_value > 0 else Decimal('0')
        
        if max_trade_pct > portfolio.constraints.max_rebalance_size_pct:
            return True, f"Single trade exceeds max rebalance size ({max_trade_pct:.2%})"
        
        # Check if total rebalance is too large
        if trade_pct > auto_approve_threshold:
            return True, f"Total rebalance size exceeds auto-approve threshold ({trade_pct:.2%})"
        
        # Check for leverage changes
        # (Would check if trades change leverage significantly)
        
        # Check for new positions in restricted instruments
        # (Would check against blacklist/restrictions)
        
        return False, None
    
    async def _estimate_risk_improvement(
        self,
        portfolio: Portfolio,
        target_allocations: Dict[str, Decimal]
    ) -> Dict[str, Any]:
        """Estimate risk improvement from proposed rebalance"""
        current_metrics = portfolio.current_risk_metrics
        
        if not current_metrics:
            return {
                "estimated_volatility_change": 0.0,
                "estimated_concentration_change": 0.0,
                "estimated_drawdown_change": 0.0
            }
        
        # Simplified estimation
        # In production, would simulate portfolio with new allocations
        
        # Estimate concentration improvement
        current_max_pos = current_metrics.max_position_pct
        target_max_pos = max(target_allocations.values()) if target_allocations else Decimal('0')
        concentration_improvement = float(current_max_pos - target_max_pos)
        
        return {
            "estimated_volatility_change": 0.0,  # Would compute from covariance matrix
            "estimated_concentration_change": concentration_improvement,
            "estimated_drawdown_change": 0.0,  # Would run scenario tests
            "constraint_breaches_fixed": len([
                b for b in (await self._get_constraint_breaches(portfolio))
                if self._would_fix_breach(b, target_allocations)
            ])
        }
    
    async def _get_constraint_breaches(self, portfolio: Portfolio) -> List[Dict]:
        """Get current constraint breaches"""
        # This would be computed by market analysis agent
        # For now, return empty list
        return []
    
    def _would_fix_breach(self, breach: Dict, target_allocations: Dict[str, Decimal]) -> bool:
        """Check if proposed allocation would fix a breach"""
        # Simplified check
        return True
    
    async def _request_risk_metrics(self, portfolio_id: str):
        """Request risk metrics computation from market analysis agent"""
        message = AgentMessage(
            message_id=f"req_risk_{int(datetime.now().timestamp())}",
            sender=self.agent_id,
            receiver="market_analysis",
            message_type="compute_risk_metrics",
            payload={"portfolio_id": portfolio_id}
        )
        await self.send_message(message)
    
    async def _handle_explain_risk(self, message: AgentMessage):
        """Explain risk metrics to user"""
        portfolio_id = message.payload.get("portfolio_id")
        
        portfolio = portfolio_storage.get_portfolio(portfolio_id)
        if not portfolio:
            return
        
        metrics = portfolio.current_risk_metrics
        if not metrics:
            response = AgentMessage(
                message_id=f"resp_{message.message_id}",
                sender=self.agent_id,
                receiver=message.sender,
                message_type="risk_explanation",
                payload={
                    "portfolio_id": portfolio_id,
                    "explanation": "Risk metrics not yet computed. Please run risk analysis first."
                }
            )
            await self.send_message(response)
            return
        
        explanation = self._generate_risk_explanation(portfolio, metrics)
        
        response = AgentMessage(
            message_id=f"resp_{message.message_id}",
            sender=self.agent_id,
            receiver=message.sender,
            message_type="risk_explanation",
            payload={
                "portfolio_id": portfolio_id,
                "explanation": explanation
            }
        )
        await self.send_message(response)
    
    def _generate_risk_explanation(self, portfolio: Portfolio, metrics: RiskMetrics) -> str:
        """Generate human-readable risk explanation"""
        explanation_parts = []
        
        explanation_parts.append(f"Portfolio Risk Summary for {portfolio.name}")
        explanation_parts.append("")
        
        # Volatility
        explanation_parts.append(f"Volatility (30-day): {metrics.realized_volatility_30d:.2%}")
        if metrics.volatility_breach:
            explanation_parts.append("⚠️ WARNING: Volatility exceeds target threshold")
        
        # Drawdown
        explanation_parts.append(f"Current Drawdown: {metrics.current_drawdown:.2%}")
        explanation_parts.append(f"Maximum Drawdown: {metrics.max_drawdown:.2%}")
        if metrics.current_drawdown > portfolio.constraints.max_drawdown_pct:
            explanation_parts.append("⚠️ WARNING: Drawdown exceeds limit")
        
        # VaR
        explanation_parts.append(f"1-day VaR (95%): ${metrics.var_1d_95pct:,.2f}")
        explanation_parts.append(f"1-day VaR (99%): ${metrics.var_1d_99pct:,.2f}")
        
        # Concentration
        explanation_parts.append(f"Largest Position: {metrics.max_position_pct:.2%}")
        explanation_parts.append(f"Top 5 Concentration: {metrics.top_5_concentration_pct:.2%}")
        
        # Leverage
        explanation_parts.append(f"Leverage Ratio: {metrics.leverage_ratio:.2f}x")
        
        return "\n".join(explanation_parts)
    
    async def _handle_optimize_allocation(self, message: AgentMessage):
        """Optimize allocation for target risk/return profile"""
        portfolio_id = message.payload.get("portfolio_id")
        target_return = message.payload.get("target_return")
        target_volatility = message.payload.get("target_volatility")
        
        portfolio = portfolio_storage.get_portfolio(portfolio_id)
        if not portfolio:
            return
        
        # This would use optimization algorithms (mean-variance, Black-Litterman, etc.)
        # For now, return a basic proposal
        
        proposal = await self.create_rebalance_proposal(
            portfolio,
            reason="optimization",
            auto_approve_threshold=Decimal('0.05')
        )
        
        response = AgentMessage(
            message_id=f"resp_{message.message_id}",
            sender=self.agent_id,
            receiver=message.sender,
            message_type="optimization_result",
            payload={
                "portfolio_id": portfolio_id,
                "proposal": proposal.dict()
            }
        )
        await self.send_message(response)

