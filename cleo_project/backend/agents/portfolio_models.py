"""
Portfolio data models for risk-managed agentic portfolios
"""
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field


class PortfolioStatus(str, Enum):
    """Portfolio status"""
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"
    REBALANCING = "rebalancing"


class RiskLevel(str, Enum):
    """Risk level classification"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Position(BaseModel):
    """Individual position in a portfolio"""
    token_address: str
    token_symbol: str
    amount: Decimal
    value_usd: Decimal
    allocation_pct: Decimal  # Percentage of total portfolio
    entry_price: Decimal
    current_price: Decimal
    unrealized_pnl: Decimal
    unrealized_pnl_pct: Decimal
    last_updated: datetime = Field(default_factory=datetime.now)


class SectorExposure(BaseModel):
    """Sector exposure tracking"""
    sector: str  # e.g., "DeFi", "Gaming", "L1", "Stablecoins"
    total_value_usd: Decimal
    allocation_pct: Decimal
    positions: List[str]  # Token addresses in this sector


class FactorExposure(BaseModel):
    """Factor exposure (beta, correlation, etc.)"""
    factor_name: str  # e.g., "BTC_BETA", "ETH_BETA", "VOLATILITY"
    exposure_value: Decimal
    target_value: Optional[Decimal] = None
    deviation_pct: Optional[Decimal] = None


class RiskMetrics(BaseModel):
    """Portfolio risk metrics"""
    portfolio_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Volatility metrics
    realized_volatility_30d: Decimal = Decimal('0')
    realized_volatility_7d: Decimal = Decimal('0')
    target_volatility: Optional[Decimal] = None
    volatility_breach: bool = False
    
    # Drawdown metrics
    current_drawdown: Decimal = Decimal('0')
    max_drawdown: Decimal = Decimal('0')
    drawdown_duration_days: int = 0
    
    # Value at Risk (VaR)
    var_1d_95pct: Decimal = Decimal('0')  # 1-day 95% VaR
    var_1d_99pct: Decimal = Decimal('0')  # 1-day 99% VaR
    cvar_1d_95pct: Decimal = Decimal('0')  # Conditional VaR
    
    # Tracking error
    tracking_error: Optional[Decimal] = None
    benchmark: Optional[str] = None
    
    # Factor exposures
    factor_exposures: List[FactorExposure] = []
    
    # Concentration metrics
    max_position_pct: Decimal = Decimal('0')
    top_5_concentration_pct: Decimal = Decimal('0')
    herfindahl_index: Decimal = Decimal('0')  # Concentration measure
    
    # Leverage
    gross_exposure: Decimal = Decimal('0')
    net_exposure: Decimal = Decimal('0')
    leverage_ratio: Decimal = Decimal('1.0')


class PortfolioConstraints(BaseModel):
    """Portfolio constraints and limits"""
    portfolio_id: str
    
    # Position limits
    max_position_pct: Decimal = Decimal('0.10')  # 10% max per position
    min_position_pct: Decimal = Decimal('0.01')  # 1% min per position
    
    # Sector limits
    max_sector_pct: Decimal = Decimal('0.40')  # 40% max per sector
    sector_limits: Dict[str, Decimal] = {}  # Custom sector limits
    
    # Factor limits
    max_beta: Optional[Decimal] = None
    min_beta: Optional[Decimal] = None
    max_volatility: Optional[Decimal] = None
    
    # Leverage limits
    max_leverage: Decimal = Decimal('1.0')  # No leverage by default
    max_gross_exposure: Optional[Decimal] = None
    
    # Drawdown limits
    max_drawdown_pct: Decimal = Decimal('0.20')  # 20% max drawdown
    de_risk_on_drawdown: bool = True
    
    # Liquidity constraints
    min_liquidity_usd: Decimal = Decimal('10000')  # Minimum liquidity per position
    
    # Rebalancing rules
    rebalance_threshold_pct: Decimal = Decimal('0.05')  # 5% drift triggers rebalance
    auto_rebalance_enabled: bool = False
    max_rebalance_size_pct: Decimal = Decimal('0.05')  # 5% max shift per rebalance


class Portfolio(BaseModel):
    """Complete portfolio definition"""
    portfolio_id: str
    name: str
    owner_address: str
    status: PortfolioStatus = PortfolioStatus.ACTIVE
    
    # Portfolio value
    total_value_usd: Decimal = Decimal('0')
    initial_capital_usd: Decimal = Decimal('0')
    
    # Positions
    positions: Dict[str, Position] = {}  # token_address -> Position
    
    # Exposures
    sector_exposures: Dict[str, SectorExposure] = {}
    factor_exposures: List[FactorExposure] = []
    
    # Risk metrics
    current_risk_metrics: Optional[RiskMetrics] = None
    risk_metrics_history: List[RiskMetrics] = []
    
    # Constraints
    constraints: PortfolioConstraints
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    last_rebalanced: Optional[datetime] = None
    last_updated: datetime = Field(default_factory=datetime.now)


class RebalanceProposal(BaseModel):
    """Proposal for portfolio rebalancing"""
    proposal_id: str
    portfolio_id: str
    created_at: datetime = Field(default_factory=datetime.now)
    created_by: str  # Agent ID
    
    # Proposed changes
    trades: List[Dict[str, Any]] = []  # List of trade instructions
    target_allocations: Dict[str, Decimal] = {}  # token_address -> target allocation %
    
    # Rationale
    reason: str
    risk_improvement: Optional[Dict[str, Any]] = None
    expected_metrics: Optional[RiskMetrics] = None
    
    # Status
    status: str = "pending"  # pending, approved, rejected, executed
    requires_approval: bool = True
    approval_required_reason: Optional[str] = None
    
    # Human review
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None


class AuditLog(BaseModel):
    """Audit log entry for governance and compliance"""
    log_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Context
    portfolio_id: Optional[str] = None
    agent_id: str
    action_type: str  # e.g., "risk_check", "rebalance_proposal", "trade_execution"
    
    # Details
    action_description: str
    input_data: Dict[str, Any] = {}
    output_data: Dict[str, Any] = {}
    
    # Decision
    decision: Optional[str] = None  # "approved", "rejected", "auto_executed"
    decision_reason: Optional[str] = None
    
    # Human involvement
    human_reviewer: Optional[str] = None
    human_decision: Optional[str] = None

