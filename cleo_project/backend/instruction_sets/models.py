"""
Instruction Set Models for Recurring and Conditional Execution
"""
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import json


class InstructionSetType(str, Enum):
    """Type of instruction set"""
    RECURRING_PAYMENT = "RecurringPayment"
    PAYROLL = "Payroll"
    SUBSCRIPTION = "Subscription"
    DEX_REBALANCE = "DEXRebalance"
    YIELD_COMPOUND = "YieldCompound"
    RISK_MANAGED_PORTFOLIO = "RiskManagedPortfolio"
    CONDITIONAL_SETTLEMENT = "ConditionalSettlement"
    STREAMING_YIELD = "StreamingYield"
    NFT_RENTAL = "NFTRental"
    CUSTOM = "Custom"


class InstructionSetStatus(str, Enum):
    """Status of an instruction set"""
    ACTIVE = "Active"
    PAUSED = "Paused"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"
    FAILED = "Failed"


class ConditionType(str, Enum):
    """Type of condition to evaluate"""
    TIME_BASED = "TimeBased"  # block.timestamp >= X
    PRICE_RANGE = "PriceRange"  # price within [min, max]
    PRICE_THRESHOLD = "PriceThreshold"  # price >= X or price <= X
    BALANCE_MIN = "BalanceMin"  # balance >= X
    BALANCE_MAX = "BalanceMax"  # balance <= X
    VAULT_UTILIZATION = "VaultUtilization"  # utilization within range
    HEALTH_FACTOR = "HealthFactor"  # health factor >= X
    POOL_LIQUIDITY = "PoolLiquidity"  # liquidity >= X
    VOLATILITY = "Volatility"  # volatility <= X
    EXTERNAL_FLAG = "ExternalFlag"  # off-chain signal
    GOVERNANCE_FLAG = "GovernanceFlag"  # DAO/governance flag
    ORACLE_STATE = "OracleState"  # oracle feed state
    COMPOSITE = "Composite"  # AND/OR of multiple conditions


class ActionType(str, Enum):
    """Type of action to execute"""
    TRANSFER = "Transfer"
    SWAP = "Swap"
    SWAP_MULTI_DEX = "SwapMultiDEX"
    LP_DEPOSIT = "LPDeposit"
    LP_WITHDRAW = "LPWithdraw"
    STAKE = "Stake"
    UNSTAKE = "Unstake"
    BORROW = "Borrow"
    REPAY = "Repay"
    BRIDGE = "Bridge"
    COMPOUND = "Compound"
    HARVEST = "Harvest"
    CUSTOM_CALL = "CustomCall"
    PIPELINE = "Pipeline"  # Execute a settlement pipeline


@dataclass
class Condition:
    """Represents a condition that must be satisfied for execution"""
    condition_type: ConditionType
    parameters: Dict[str, Any]  # Condition-specific parameters
    description: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "condition_type": self.condition_type.value,
            "parameters": self.parameters,
            "description": self.description
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Condition":
        return cls(
            condition_type=ConditionType(data["condition_type"]),
            parameters=data["parameters"],
            description=data.get("description")
        )


@dataclass
class Action:
    """Represents an action to execute"""
    action_type: ActionType
    target: str  # Contract address or identifier
    parameters: Dict[str, Any]  # Action-specific parameters
    is_critical: bool = True  # Whether failure should abort execution
    condition: Optional[Condition] = None  # Optional per-action condition
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_type": self.action_type.value,
            "target": self.target,
            "parameters": self.parameters,
            "is_critical": self.is_critical,
            "condition": self.condition.to_dict() if self.condition else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Action":
        condition_data = data.get("condition")
        return cls(
            action_type=ActionType(data["action_type"]),
            target=data["target"],
            parameters=data["parameters"],
            is_critical=data.get("is_critical", True),
            condition=Condition.from_dict(condition_data) if condition_data else None
        )


@dataclass
class Schedule:
    """Schedule configuration for recurring execution"""
    interval_seconds: int  # Interval between executions (can use block intervals too)
    next_execution: int  # Unix timestamp or block number
    end_time: Optional[int] = None  # Optional end time
    max_executions: Optional[int] = None  # Optional max execution count
    execution_count: int = 0  # Current execution count
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "interval_seconds": self.interval_seconds,
            "next_execution": self.next_execution,
            "end_time": self.end_time,
            "max_executions": self.max_executions,
            "execution_count": self.execution_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Schedule":
        return cls(
            interval_seconds=data["interval_seconds"],
            next_execution=data["next_execution"],
            end_time=data.get("end_time"),
            max_executions=data.get("max_executions"),
            execution_count=data.get("execution_count", 0)
        )


@dataclass
class Limits:
    """Safety limits and caps for instruction set"""
    max_notional_per_run: Optional[int] = None  # Max value per execution
    cumulative_cap: Optional[int] = None  # Total cumulative cap
    cumulative_spent: int = 0  # Current cumulative spent
    max_slippage_bps: Optional[int] = None  # Max slippage in basis points (e.g., 50 = 0.5%)
    max_gas_per_execution: Optional[int] = None  # Max gas per execution
    per_beneficiary_cap: Optional[Dict[str, int]] = None  # Per-address caps
    circuit_breaker_active: bool = False  # Circuit breaker flag
    pause_switch: bool = False  # Manual pause switch
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_notional_per_run": self.max_notional_per_run,
            "cumulative_cap": self.cumulative_cap,
            "cumulative_spent": self.cumulative_spent,
            "max_slippage_bps": self.max_slippage_bps,
            "max_gas_per_execution": self.max_gas_per_execution,
            "per_beneficiary_cap": self.per_beneficiary_cap,
            "circuit_breaker_active": self.circuit_breaker_active,
            "pause_switch": self.pause_switch
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Limits":
        return cls(
            max_notional_per_run=data.get("max_notional_per_run"),
            cumulative_cap=data.get("cumulative_cap"),
            cumulative_spent=data.get("cumulative_spent", 0),
            max_slippage_bps=data.get("max_slippage_bps"),
            max_gas_per_execution=data.get("max_gas_per_execution"),
            per_beneficiary_cap=data.get("per_beneficiary_cap"),
            circuit_breaker_active=data.get("circuit_breaker_active", False),
            pause_switch=data.get("pause_switch", False)
        )


@dataclass
class InstructionSet:
    """Complete instruction set with all configuration"""
    instruction_id: str
    owner: str  # Creator/owner address
    instruction_type: InstructionSetType
    status: InstructionSetStatus
    schedule: Schedule
    conditions: List[Condition]  # Global conditions (all must pass)
    actions: List[Action]  # Actions to execute
    limits: Limits
    created_at: int = field(default_factory=lambda: int(datetime.now().timestamp()))
    updated_at: int = field(default_factory=lambda: int(datetime.now().timestamp()))
    last_execution: Optional[int] = None
    last_execution_tx: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional metadata
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "instruction_id": self.instruction_id,
            "owner": self.owner,
            "instruction_type": self.instruction_type.value,
            "status": self.status.value,
            "schedule": self.schedule.to_dict(),
            "conditions": [c.to_dict() for c in self.conditions],
            "actions": [a.to_dict() for a in self.actions],
            "limits": self.limits.to_dict(),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_execution": self.last_execution,
            "last_execution_tx": self.last_execution_tx,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InstructionSet":
        return cls(
            instruction_id=data["instruction_id"],
            owner=data["owner"],
            instruction_type=InstructionSetType(data["instruction_type"]),
            status=InstructionSetStatus(data["status"]),
            schedule=Schedule.from_dict(data["schedule"]),
            conditions=[Condition.from_dict(c) for c in data.get("conditions", [])],
            actions=[Action.from_dict(a) for a in data.get("actions", [])],
            limits=Limits.from_dict(data.get("limits", {})),
            created_at=data.get("created_at", int(datetime.now().timestamp())),
            updated_at=data.get("updated_at", int(datetime.now().timestamp())),
            last_execution=data.get("last_execution"),
            last_execution_tx=data.get("last_execution_tx"),
            metadata=data.get("metadata", {})
        )
