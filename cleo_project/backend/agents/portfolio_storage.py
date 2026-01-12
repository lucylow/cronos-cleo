"""
Portfolio storage layer for risk-managed agentic portfolios
In-memory storage (can be replaced with MongoDB/PostgreSQL in production)
"""
import json
from datetime import datetime
from typing import Dict, List, Optional
from decimal import Decimal

from .portfolio_models import (
    Portfolio, Position, RiskMetrics, PortfolioConstraints,
    RebalanceProposal, AuditLog, PortfolioStatus
)


class PortfolioStorage:
    """In-memory storage for portfolios (replace with database in production)"""
    
    def __init__(self):
        self.portfolios: Dict[str, Portfolio] = {}
        self.rebalance_proposals: Dict[str, RebalanceProposal] = {}
        self.audit_logs: List[AuditLog] = []
        self.portfolio_risk_history: Dict[str, List[RiskMetrics]] = {}  # portfolio_id -> history
    
    # Portfolio CRUD
    def create_portfolio(self, portfolio: Portfolio) -> bool:
        """Create a new portfolio"""
        if portfolio.portfolio_id in self.portfolios:
            return False
        self.portfolios[portfolio.portfolio_id] = portfolio
        self.portfolio_risk_history[portfolio.portfolio_id] = []
        return True
    
    def get_portfolio(self, portfolio_id: str) -> Optional[Portfolio]:
        """Get portfolio by ID"""
        return self.portfolios.get(portfolio_id)
    
    def update_portfolio(self, portfolio: Portfolio) -> bool:
        """Update portfolio"""
        if portfolio.portfolio_id not in self.portfolios:
            return False
        portfolio.last_updated = datetime.now()
        self.portfolios[portfolio.portfolio_id] = portfolio
        return True
    
    def list_portfolios(self, owner_address: Optional[str] = None) -> List[Portfolio]:
        """List all portfolios, optionally filtered by owner"""
        portfolios = list(self.portfolios.values())
        if owner_address:
            portfolios = [p for p in portfolios if p.owner_address.lower() == owner_address.lower()]
        return portfolios
    
    def delete_portfolio(self, portfolio_id: str) -> bool:
        """Delete portfolio"""
        if portfolio_id in self.portfolios:
            del self.portfolios[portfolio_id]
            if portfolio_id in self.portfolio_risk_history:
                del self.portfolio_risk_history[portfolio_id]
            return True
        return False
    
    # Position management
    def update_position(self, portfolio_id: str, position: Position) -> bool:
        """Update or add a position in a portfolio"""
        portfolio = self.get_portfolio(portfolio_id)
        if not portfolio:
            return False
        portfolio.positions[position.token_address] = position
        portfolio.last_updated = datetime.now()
        return True
    
    def remove_position(self, portfolio_id: str, token_address: str) -> bool:
        """Remove a position from a portfolio"""
        portfolio = self.get_portfolio(portfolio_id)
        if not portfolio:
            return False
        if token_address in portfolio.positions:
            del portfolio.positions[token_address]
            portfolio.last_updated = datetime.now()
            return True
        return False
    
    # Risk metrics
    def save_risk_metrics(self, portfolio_id: str, metrics: RiskMetrics) -> bool:
        """Save risk metrics for a portfolio"""
        portfolio = self.get_portfolio(portfolio_id)
        if not portfolio:
            return False
        
        portfolio.current_risk_metrics = metrics
        portfolio.risk_metrics_history.append(metrics)
        
        # Keep history in separate store too
        if portfolio_id not in self.portfolio_risk_history:
            self.portfolio_risk_history[portfolio_id] = []
        self.portfolio_risk_history[portfolio_id].append(metrics)
        
        # Keep only last 1000 entries per portfolio
        if len(self.portfolio_risk_history[portfolio_id]) > 1000:
            self.portfolio_risk_history[portfolio_id] = self.portfolio_risk_history[portfolio_id][-1000:]
        
        return True
    
    def get_risk_history(self, portfolio_id: str, limit: int = 100) -> List[RiskMetrics]:
        """Get risk metrics history for a portfolio"""
        return self.portfolio_risk_history.get(portfolio_id, [])[-limit:]
    
    # Rebalance proposals
    def create_rebalance_proposal(self, proposal: RebalanceProposal) -> bool:
        """Create a rebalance proposal"""
        if proposal.proposal_id in self.rebalance_proposals:
            return False
        self.rebalance_proposals[proposal.proposal_id] = proposal
        return True
    
    def get_rebalance_proposal(self, proposal_id: str) -> Optional[RebalanceProposal]:
        """Get rebalance proposal by ID"""
        return self.rebalance_proposals.get(proposal_id)
    
    def update_rebalance_proposal(self, proposal: RebalanceProposal) -> bool:
        """Update rebalance proposal"""
        if proposal.proposal_id not in self.rebalance_proposals:
            return False
        self.rebalance_proposals[proposal.proposal_id] = proposal
        return True
    
    def list_rebalance_proposals(self, portfolio_id: Optional[str] = None, status: Optional[str] = None) -> List[RebalanceProposal]:
        """List rebalance proposals"""
        proposals = list(self.rebalance_proposals.values())
        if portfolio_id:
            proposals = [p for p in proposals if p.portfolio_id == portfolio_id]
        if status:
            proposals = [p for p in proposals if p.status == status]
        return proposals
    
    # Audit logging
    def log_audit_event(self, log: AuditLog) -> bool:
        """Add audit log entry"""
        self.audit_logs.append(log)
        # Keep only last 10000 entries
        if len(self.audit_logs) > 10000:
            self.audit_logs = self.audit_logs[-10000:]
        return True
    
    def get_audit_logs(
        self,
        portfolio_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        action_type: Optional[str] = None,
        limit: int = 100
    ) -> List[AuditLog]:
        """Get audit logs with filters"""
        logs = self.audit_logs
        if portfolio_id:
            logs = [l for l in logs if l.portfolio_id == portfolio_id]
        if agent_id:
            logs = [l for l in logs if l.agent_id == agent_id]
        if action_type:
            logs = [l for l in logs if l.action_type == action_type]
        return logs[-limit:]


# Global storage instance
portfolio_storage = PortfolioStorage()

