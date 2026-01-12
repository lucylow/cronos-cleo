"""
Market Analysis Agent - Computes risk metrics for portfolios
Volatility, VaR, drawdown, factor exposures, scenario testing
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal
import statistics

from .base_agent import BaseAgent
from .message_bus import AgentMessage
from .portfolio_models import (
    Portfolio, RiskMetrics, FactorExposure, Position, RiskLevel
)
from .portfolio_storage import portfolio_storage

logger = logging.getLogger(__name__)


class MarketAnalysisAgent(BaseAgent):
    """Agent responsible for computing portfolio risk metrics"""
    
    def __init__(self, liquidity_monitor=None, mcp_client=None):
        super().__init__("market_analysis", "Market Analysis Agent")
        self.liquidity_monitor = liquidity_monitor
        self.mcp_client = mcp_client
        self.price_history: Dict[str, List[Dict]] = {}  # token -> [{timestamp, price}]
        self.portfolio_values_history: Dict[str, List[Dict]] = {}  # portfolio_id -> [{timestamp, value}]
    
    async def handle_message(self, message: AgentMessage):
        """Handle incoming messages"""
        if message.message_type == "compute_risk_metrics":
            await self._handle_compute_risk_metrics(message)
        elif message.message_type == "update_price_data":
            await self._handle_update_price_data(message)
        elif message.message_type == "scenario_test":
            await self._handle_scenario_test(message)
    
    async def _handle_compute_risk_metrics(self, message: AgentMessage):
        """Compute risk metrics for a portfolio"""
        portfolio_id = message.payload.get("portfolio_id")
        if not portfolio_id:
            logger.error("Missing portfolio_id in compute_risk_metrics request")
            return
        
        portfolio = portfolio_storage.get_portfolio(portfolio_id)
        if not portfolio:
            logger.error(f"Portfolio {portfolio_id} not found")
            return
        
        try:
            # Compute all risk metrics
            risk_metrics = await self.compute_portfolio_risk_metrics(portfolio)
            
            # Save metrics
            portfolio_storage.save_risk_metrics(portfolio_id, risk_metrics)
            
            # Update portfolio
            portfolio.current_risk_metrics = risk_metrics
            portfolio_storage.update_portfolio(portfolio)
            
            # Send response
            response = AgentMessage(
                message_id=f"resp_{message.message_id}",
                sender=self.agent_id,
                receiver=message.sender,
                message_type="risk_metrics_computed",
                payload={
                    "portfolio_id": portfolio_id,
                    "risk_metrics": risk_metrics.dict(),
                    "breaches": await self._check_constraint_breaches(portfolio, risk_metrics)
                }
            )
            await self.send_message(response)
            
        except Exception as e:
            logger.error(f"Error computing risk metrics: {e}", exc_info=True)
            response = AgentMessage(
                message_id=f"resp_{message.message_id}",
                sender=self.agent_id,
                receiver=message.sender,
                message_type="error",
                payload={"error": str(e)}
            )
            await self.send_message(response)
    
    async def compute_portfolio_risk_metrics(self, portfolio: Portfolio) -> RiskMetrics:
        """Compute comprehensive risk metrics for a portfolio"""
        metrics = RiskMetrics(portfolio_id=portfolio.portfolio_id)
        
        # Update portfolio value
        total_value = sum(pos.value_usd for pos in portfolio.positions.values())
        portfolio.total_value_usd = total_value
        
        # Compute volatility
        metrics.realized_volatility_30d = await self._compute_volatility(portfolio, days=30)
        metrics.realized_volatility_7d = await self._compute_volatility(portfolio, days=7)
        
        if portfolio.constraints.max_volatility:
            metrics.volatility_breach = metrics.realized_volatility_30d > portfolio.constraints.max_volatility
        
        # Compute drawdown
        drawdown_data = await self._compute_drawdown(portfolio)
        metrics.current_drawdown = drawdown_data["current"]
        metrics.max_drawdown = drawdown_data["max"]
        metrics.drawdown_duration_days = drawdown_data["duration_days"]
        
        # Compute VaR
        var_data = await self._compute_var(portfolio)
        metrics.var_1d_95pct = var_data["var_95"]
        metrics.var_1d_99pct = var_data["var_99"]
        metrics.cvar_1d_95pct = var_data["cvar_95"]
        
        # Compute factor exposures
        metrics.factor_exposures = await self._compute_factor_exposures(portfolio)
        
        # Compute concentration metrics
        concentration = await self._compute_concentration(portfolio)
        metrics.max_position_pct = concentration["max_position"]
        metrics.top_5_concentration_pct = concentration["top_5"]
        metrics.herfindahl_index = concentration["herfindahl"]
        
        # Compute leverage
        leverage_data = await self._compute_leverage(portfolio)
        metrics.gross_exposure = leverage_data["gross"]
        metrics.net_exposure = leverage_data["net"]
        metrics.leverage_ratio = leverage_data["ratio"]
        
        return metrics
    
    async def _compute_volatility(self, portfolio: Portfolio, days: int) -> Decimal:
        """Compute realized volatility over N days"""
        portfolio_id = portfolio.portfolio_id
        
        # Get portfolio value history
        if portfolio_id not in self.portfolio_values_history:
            return Decimal('0')
        
        history = self.portfolio_values_history[portfolio_id]
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_values = [
            h["value"] for h in history
            if h["timestamp"] >= cutoff_date
        ]
        
        if len(recent_values) < 2:
            return Decimal('0')
        
        # Compute daily returns
        returns = []
        for i in range(1, len(recent_values)):
            if recent_values[i-1] > 0:
                ret = (recent_values[i] - recent_values[i-1]) / recent_values[i-1]
                returns.append(float(ret))
        
        if not returns:
            return Decimal('0')
        
        # Annualized volatility (assuming daily returns)
        std_dev = statistics.stdev(returns) if len(returns) > 1 else 0.0
        annualized_vol = std_dev * (365 ** 0.5)
        
        return Decimal(str(annualized_vol))
    
    async def _compute_drawdown(self, portfolio: Portfolio) -> Dict[str, Any]:
        """Compute current and maximum drawdown"""
        portfolio_id = portfolio.portfolio_id
        
        if portfolio_id not in self.portfolio_values_history:
            return {
                "current": Decimal('0'),
                "max": Decimal('0'),
                "duration_days": 0
            }
        
        history = self.portfolio_values_history[portfolio_id]
        if not history:
            return {
                "current": Decimal('0'),
                "max": Decimal('0'),
                "duration_days": 0
            }
        
        # Sort by timestamp
        history = sorted(history, key=lambda x: x["timestamp"])
        values = [h["value"] for h in history]
        current_value = portfolio.total_value_usd
        
        # Find peak
        peak = max(values) if values else current_value
        if peak == 0:
            return {
                "current": Decimal('0'),
                "max": Decimal('0'),
                "duration_days": 0
            }
        
        # Current drawdown
        current_dd = (peak - current_value) / peak if peak > 0 else Decimal('0')
        
        # Maximum drawdown (from peak to trough)
        max_dd = Decimal('0')
        peak_value = values[0]
        for value in values:
            if value > peak_value:
                peak_value = value
            else:
                dd = (peak_value - value) / peak_value if peak_value > 0 else Decimal('0')
                if dd > max_dd:
                    max_dd = dd
        
        # Drawdown duration (simplified)
        duration_days = 0
        if current_dd > 0:
            # Find when we hit the peak
            peak_idx = values.index(peak) if peak in values else 0
            if peak_idx < len(history):
                peak_time = history[peak_idx]["timestamp"]
                duration_days = (datetime.now() - peak_time).days
        
        return {
            "current": current_dd,
            "max": max_dd,
            "duration_days": duration_days
        }
    
    async def _compute_var(self, portfolio: Portfolio) -> Dict[str, Decimal]:
        """Compute Value at Risk (VaR) using historical simulation"""
        portfolio_id = portfolio.portfolio_id
        
        if portfolio_id not in self.portfolio_values_history:
            return {
                "var_95": Decimal('0'),
                "var_99": Decimal('0'),
                "cvar_95": Decimal('0')
            }
        
        history = self.portfolio_values_history[portfolio_id]
        if len(history) < 2:
            return {
                "var_95": Decimal('0'),
                "var_99": Decimal('0'),
                "cvar_95": Decimal('0')
            }
        
        # Compute daily returns
        history = sorted(history, key=lambda x: x["timestamp"])
        returns = []
        for i in range(1, len(history)):
            prev_value = history[i-1]["value"]
            curr_value = history[i]["value"]
            if prev_value > 0:
                ret = (curr_value - prev_value) / prev_value
                returns.append(float(ret))
        
        if not returns:
            return {
                "var_95": Decimal('0'),
                "var_99": Decimal('0'),
                "cvar_95": Decimal('0')
            }
        
        # Sort returns
        returns_sorted = sorted(returns)
        n = len(returns_sorted)
        current_value = portfolio.total_value_usd
        
        # VaR at 95% (5th percentile)
        var_95_idx = int(n * 0.05)
        var_95_pct = returns_sorted[var_95_idx] if var_95_idx < n else returns_sorted[0]
        var_95 = abs(Decimal(str(var_95_pct)) * current_value)
        
        # VaR at 99% (1st percentile)
        var_99_idx = int(n * 0.01)
        var_99_pct = returns_sorted[var_99_idx] if var_99_idx < n else returns_sorted[0]
        var_99 = abs(Decimal(str(var_99_pct)) * current_value)
        
        # CVaR (Conditional VaR) - average of worst 5%
        tail_returns = returns_sorted[:var_95_idx+1] if var_95_idx < n else returns_sorted
        cvar_95_pct = statistics.mean(tail_returns) if tail_returns else 0.0
        cvar_95 = abs(Decimal(str(cvar_95_pct)) * current_value)
        
        return {
            "var_95": var_95,
            "var_99": var_99,
            "cvar_95": cvar_95
        }
    
    async def _compute_factor_exposures(self, portfolio: Portfolio) -> List[FactorExposure]:
        """Compute factor exposures (beta, correlations, etc.)"""
        exposures = []
        
        # Simplified: compute BTC and ETH beta
        # In production, use actual price data and regression
        
        btc_exposure = Decimal('0')
        eth_exposure = Decimal('0')
        
        # Estimate based on token types (simplified)
        for position in portfolio.positions.values():
            symbol = position.token_symbol.upper()
            if 'BTC' in symbol or 'WBTC' in symbol:
                btc_exposure += position.allocation_pct
            elif 'ETH' in symbol or 'WETH' in symbol:
                eth_exposure += position.allocation_pct
        
        exposures.append(FactorExposure(
            factor_name="BTC_BETA",
            exposure_value=btc_exposure,
            target_value=portfolio.constraints.max_beta if portfolio.constraints.max_beta else None
        ))
        
        exposures.append(FactorExposure(
            factor_name="ETH_BETA",
            exposure_value=eth_exposure,
            target_value=portfolio.constraints.max_beta if portfolio.constraints.max_beta else None
        ))
        
        return exposures
    
    async def _compute_concentration(self, portfolio: Portfolio) -> Dict[str, Decimal]:
        """Compute concentration metrics"""
        if not portfolio.positions:
            return {
                "max_position": Decimal('0'),
                "top_5": Decimal('0'),
                "herfindahl": Decimal('0')
            }
        
        allocations = [pos.allocation_pct for pos in portfolio.positions.values()]
        allocations_sorted = sorted(allocations, reverse=True)
        
        max_position = allocations_sorted[0] if allocations_sorted else Decimal('0')
        top_5 = sum(allocations_sorted[:5]) if len(allocations_sorted) >= 5 else sum(allocations_sorted)
        
        # Herfindahl index (sum of squared allocations)
        herfindahl = sum(alloc ** 2 for alloc in allocations)
        
        return {
            "max_position": max_position,
            "top_5": top_5,
            "herfindahl": herfindahl
        }
    
    async def _compute_leverage(self, portfolio: Portfolio) -> Dict[str, Decimal]:
        """Compute leverage metrics"""
        # Simplified: assume no leverage for now
        # In production, check for borrowed positions, margin, etc.
        gross = portfolio.total_value_usd
        net = portfolio.total_value_usd
        ratio = Decimal('1.0')
        
        return {
            "gross": gross,
            "net": net,
            "ratio": ratio
        }
    
    async def _check_constraint_breaches(self, portfolio: Portfolio, metrics: RiskMetrics) -> List[Dict[str, Any]]:
        """Check for constraint breaches"""
        breaches = []
        constraints = portfolio.constraints
        
        # Check position limits
        if metrics.max_position_pct > constraints.max_position_pct:
            breaches.append({
                "type": "position_limit",
                "metric": "max_position_pct",
                "value": float(metrics.max_position_pct),
                "limit": float(constraints.max_position_pct),
                "severity": "high"
            })
        
        # Check volatility
        if constraints.max_volatility and metrics.realized_volatility_30d > constraints.max_volatility:
            breaches.append({
                "type": "volatility_limit",
                "metric": "realized_volatility_30d",
                "value": float(metrics.realized_volatility_30d),
                "limit": float(constraints.max_volatility),
                "severity": "high"
            })
        
        # Check drawdown
        if metrics.current_drawdown > constraints.max_drawdown_pct:
            breaches.append({
                "type": "drawdown_limit",
                "metric": "current_drawdown",
                "value": float(metrics.current_drawdown),
                "limit": float(constraints.max_drawdown_pct),
                "severity": "critical"
            })
        
        # Check leverage
        if metrics.leverage_ratio > constraints.max_leverage:
            breaches.append({
                "type": "leverage_limit",
                "metric": "leverage_ratio",
                "value": float(metrics.leverage_ratio),
                "limit": float(constraints.max_leverage),
                "severity": "high"
            })
        
        return breaches
    
    async def _handle_update_price_data(self, message: AgentMessage):
        """Update price data for a token"""
        token_address = message.payload.get("token_address")
        price = message.payload.get("price")
        
        if not token_address or price is None:
            return
        
        if token_address not in self.price_history:
            self.price_history[token_address] = []
        
        self.price_history[token_address].append({
            "timestamp": datetime.now(),
            "price": Decimal(str(price))
        })
        
        # Keep only last 1000 entries per token
        if len(self.price_history[token_address]) > 1000:
            self.price_history[token_address] = self.price_history[token_address][-1000:]
    
    async def _handle_scenario_test(self, message: AgentMessage):
        """Run scenario/stress test on portfolio"""
        portfolio_id = message.payload.get("portfolio_id")
        scenario = message.payload.get("scenario", "market_crash")  # market_crash, rate_shock, etc.
        
        portfolio = portfolio_storage.get_portfolio(portfolio_id)
        if not portfolio:
            return
        
        # Run scenario simulation
        scenario_result = await self.run_scenario_test(portfolio, scenario)
        
        response = AgentMessage(
            message_id=f"resp_{message.message_id}",
            sender=self.agent_id,
            receiver=message.sender,
            message_type="scenario_test_result",
            payload={
                "portfolio_id": portfolio_id,
                "scenario": scenario,
                "result": scenario_result
            }
        )
        await self.send_message(response)
    
    async def run_scenario_test(self, portfolio: Portfolio, scenario: str) -> Dict[str, Any]:
        """Run stress test scenario"""
        # Simplified scenario testing
        # In production, use historical data or Monte Carlo simulation
        
        scenarios = {
            "market_crash": {"btc_drop": Decimal('0.50'), "eth_drop": Decimal('0.40')},
            "rate_shock": {"btc_drop": Decimal('0.20'), "eth_drop": Decimal('0.15')},
            "flash_crash": {"btc_drop": Decimal('0.30'), "eth_drop": Decimal('0.25')}
        }
        
        scenario_params = scenarios.get(scenario, scenarios["market_crash"])
        
        # Estimate portfolio loss
        estimated_loss = Decimal('0')
        for position in portfolio.positions.values():
            symbol = position.token_symbol.upper()
            if 'BTC' in symbol or 'WBTC' in symbol:
                estimated_loss += position.value_usd * scenario_params["btc_drop"]
            elif 'ETH' in symbol or 'WETH' in symbol:
                estimated_loss += position.value_usd * scenario_params["eth_drop"]
            else:
                # Assume correlation with market
                estimated_loss += position.value_usd * Decimal('0.30')
        
        loss_pct = (estimated_loss / portfolio.total_value_usd) if portfolio.total_value_usd > 0 else Decimal('0')
        
        return {
            "scenario": scenario,
            "estimated_loss_usd": float(estimated_loss),
            "estimated_loss_pct": float(loss_pct),
            "post_scenario_value_usd": float(portfolio.total_value_usd - estimated_loss),
            "breaches_constraints": loss_pct > portfolio.constraints.max_drawdown_pct
        }
    
    async def update_portfolio_value_history(self, portfolio_id: str, value: Decimal):
        """Update portfolio value history for volatility/drawdown calculations"""
        if portfolio_id not in self.portfolio_values_history:
            self.portfolio_values_history[portfolio_id] = []
        
        self.portfolio_values_history[portfolio_id].append({
            "timestamp": datetime.now(),
            "value": value
        })
        
        # Keep only last 1000 entries
        if len(self.portfolio_values_history[portfolio_id]) > 1000:
            self.portfolio_values_history[portfolio_id] = self.portfolio_values_history[portfolio_id][-1000:]

