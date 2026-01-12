"""
Data models for the C.L.E.O. multi-agent system
"""
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class Token(BaseModel):
    """Token data model"""
    address: str
    symbol: str
    decimals: int
    name: str


class DEXPool(BaseModel):
    """DEX Pool data model"""
    dex_name: str
    pool_address: str
    token0: Token
    token1: Token
    reserve0: Decimal = Decimal('0')
    reserve1: Decimal = Decimal('0')
    reserve_usd: Decimal = Decimal('0')
    fee_tier: int = 300  # 0.3% default for V2
    last_updated: datetime = Field(default_factory=datetime.now)


class RouteSplit(BaseModel):
    """Individual route split for multi-DEX execution"""
    dex_name: str
    pool_address: str
    token_in: Token
    token_out: Token
    amount_in: Decimal
    expected_amount_out: Decimal
    min_amount_out: Decimal
    path: List[str]
    slippage_tolerance: Decimal = Decimal('0.005')  # 0.5%


class OptimizedRoute(BaseModel):
    """Complete optimized route for execution"""
    route_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    token_in: Token
    token_out: Token
    total_amount_in: Decimal
    total_expected_out: Decimal
    total_min_out: Decimal
    splits: List[RouteSplit]
    predicted_slippage: Decimal
    expected_gas: Decimal
    confidence_score: float = 0.0
    risk_score: float = 0.0


class ExecutionResult(BaseModel):
    """Execution result from x402"""
    success: bool
    tx_hash: Optional[str] = None
    actual_amount_out: Optional[Decimal] = None
    actual_slippage: Optional[Decimal] = None
    gas_used: Optional[Decimal] = None
    block_number: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    error_message: Optional[str] = None

