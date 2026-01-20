"""
Database models for Multi-Leg Transactions & Batching
Institutional-grade transaction tracking with full audit trails
"""
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
import json

Base = declarative_base()


class LegType(str, Enum):
    """Types of transaction legs"""
    DEBIT = "debit"
    CREDIT = "credit"
    SWAP = "swap"
    TRANSFER = "transfer"
    APPROVAL = "approval"
    DEPOSIT = "deposit"
    WITHDRAW = "withdraw"
    FEE = "fee"
    NOTIFICATION = "notification"
    CUSTOM = "custom"


class LegStatus(str, Enum):
    """Status of a transaction leg"""
    PENDING = "pending"
    PREPARED = "prepared"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATED = "compensated"
    CANCELLED = "cancelled"


class TransactionStatus(str, Enum):
    """Status of a multi-leg transaction"""
    PENDING = "pending"
    PREPARING = "preparing"
    EXECUTING = "executing"
    COMPLETED = "completed"
    PARTIALLY_FAILED = "partially_failed"
    FAILED = "failed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    CANCELLED = "cancelled"


class BatchStatus(str, Enum):
    """Status of a batch"""
    PENDING = "pending"
    COLLECTING = "collecting"
    READY = "ready"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MultiLegTransaction(Base):
    """Main transaction record for multi-leg operations"""
    __tablename__ = 'multi_leg_transactions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(String(64), unique=True, nullable=False, index=True)
    idempotency_key = Column(String(128), unique=True, nullable=True, index=True)
    
    status = Column(SQLEnum(TransactionStatus), default=TransactionStatus.PENDING, nullable=False)
    transaction_type = Column(String(50), nullable=False)  # e.g., "swap", "payment", "settlement"
    
    # Initiator information
    initiator = Column(String(42), nullable=False)  # Ethereum address
    initiator_type = Column(String(20), default="user")  # user, system, agent
    
    # Timing
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    deadline = Column(DateTime, nullable=True)
    
    # Execution tracking
    on_chain_tx_hash = Column(String(66), nullable=True, index=True)
    block_number = Column(Integer, nullable=True)
    
    # Metadata
    extra_metadata = Column('metadata', Text, nullable=True)  # JSON string for additional data
    error_message = Column(Text, nullable=True)
    
    # Relationships
    legs = relationship("TransactionLeg", back_populates="transaction", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="transaction", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "transaction_id": self.transaction_id,
            "idempotency_key": self.idempotency_key,
            "status": self.status.value,
            "transaction_type": self.transaction_type,
            "initiator": self.initiator,
            "initiator_type": self.initiator_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "on_chain_tx_hash": self.on_chain_tx_hash,
            "block_number": self.block_number,
            "metadata": json.loads(self.extra_metadata) if self.extra_metadata else {},
            "error_message": self.error_message,
            "legs_count": len(self.legs) if self.legs else 0
        }


class TransactionLeg(Base):
    """Individual leg of a multi-leg transaction"""
    __tablename__ = 'transaction_legs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    leg_id = Column(String(64), unique=True, nullable=False, index=True)
    transaction_id = Column(String(64), ForeignKey('multi_leg_transactions.transaction_id'), nullable=False)
    
    leg_type = Column(SQLEnum(LegType), nullable=False)
    status = Column(SQLEnum(LegStatus), default=LegStatus.PENDING, nullable=False)
    sequence = Column(Integer, nullable=False)  # Order of execution
    
    # Leg details
    target_address = Column(String(42), nullable=True)  # Contract or account address
    function_name = Column(String(100), nullable=True)
    function_data = Column(Text, nullable=True)  # Encoded function call data
    
    # Amounts
    amount_in = Column(String(78), nullable=True)  # Use string for large numbers
    amount_out = Column(String(78), nullable=True)
    token_in = Column(String(42), nullable=True)
    token_out = Column(String(42), nullable=True)
    
    # Execution tracking
    executed_at = Column(DateTime, nullable=True)
    on_chain_tx_hash = Column(String(66), nullable=True)
    gas_used = Column(Integer, nullable=True)
    
    # Compensation
    requires_compensation = Column(Boolean, default=False, nullable=False)
    compensation_leg_id = Column(String(64), nullable=True)  # Reference to compensating leg
    compensated_at = Column(DateTime, nullable=True)
    
    # Metadata
    extra_metadata = Column('metadata', Text, nullable=True)  # JSON string
    error_message = Column(Text, nullable=True)
    
    # Relationships
    transaction = relationship("MultiLegTransaction", back_populates="legs")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "leg_id": self.leg_id,
            "transaction_id": self.transaction_id,
            "leg_type": self.leg_type.value,
            "status": self.status.value,
            "sequence": self.sequence,
            "target_address": self.target_address,
            "function_name": self.function_name,
            "amount_in": self.amount_in,
            "amount_out": self.amount_out,
            "token_in": self.token_in,
            "token_out": self.token_out,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "on_chain_tx_hash": self.on_chain_tx_hash,
            "gas_used": self.gas_used,
            "requires_compensation": self.requires_compensation,
            "compensation_leg_id": self.compensation_leg_id,
            "compensated_at": self.compensated_at.isoformat() if self.compensated_at else None,
            "metadata": json.loads(self.extra_metadata) if self.extra_metadata else {},
            "error_message": self.error_message
        }


class Batch(Base):
    """Batch of transactions/legs to be executed together"""
    __tablename__ = 'batches'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(String(64), unique=True, nullable=False, index=True)
    
    status = Column(SQLEnum(BatchStatus), default=BatchStatus.PENDING, nullable=False)
    batch_type = Column(String(50), nullable=False)  # "time_window", "business_logic", "gas_optimization"
    
    # Batching strategy
    strategy = Column(String(50), nullable=False)
    max_size = Column(Integer, default=100, nullable=False)
    time_window_seconds = Column(Integer, nullable=True)
    
    # Timing
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ready_at = Column(DateTime, nullable=True)
    executed_at = Column(DateTime, nullable=True)
    deadline = Column(DateTime, nullable=True)
    
    # Execution
    on_chain_tx_hash = Column(String(66), nullable=True, index=True)
    block_number = Column(Integer, nullable=True)
    gas_used = Column(Integer, nullable=True)
    gas_saved = Column(Integer, nullable=True)  # Estimated gas saved vs individual txs
    
    # Results
    success_count = Column(Integer, default=0, nullable=False)
    failure_count = Column(Integer, default=0, nullable=False)
    
    # Metadata
    extra_metadata = Column('metadata', Text, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Relationships
    batch_items = relationship("BatchItem", back_populates="batch", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "batch_id": self.batch_id,
            "status": self.status.value,
            "batch_type": self.batch_type,
            "strategy": self.strategy,
            "max_size": self.max_size,
            "time_window_seconds": self.time_window_seconds,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "ready_at": self.ready_at.isoformat() if self.ready_at else None,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "on_chain_tx_hash": self.on_chain_tx_hash,
            "block_number": self.block_number,
            "gas_used": self.gas_used,
            "gas_saved": self.gas_saved,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "metadata": json.loads(self.extra_metadata) if self.extra_metadata else {},
            "error_message": self.error_message,
            "items_count": len(self.batch_items) if self.batch_items else 0
        }


class BatchItem(Base):
    """Item in a batch (can be a transaction or leg)"""
    __tablename__ = 'batch_items'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(String(64), ForeignKey('batches.batch_id'), nullable=False)
    
    # Reference to transaction or leg
    transaction_id = Column(String(64), nullable=True, index=True)
    leg_id = Column(String(64), nullable=True, index=True)
    
    item_type = Column(String(20), nullable=False)  # "transaction" or "leg"
    sequence = Column(Integer, nullable=False)
    
    # Execution result
    executed = Column(Boolean, default=False, nullable=False)
    success = Column(Boolean, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Relationships
    batch = relationship("Batch", back_populates="batch_items")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "batch_id": self.batch_id,
            "transaction_id": self.transaction_id,
            "leg_id": self.leg_id,
            "item_type": self.item_type,
            "sequence": self.sequence,
            "executed": self.executed,
            "success": self.success,
            "error_message": self.error_message
        }


class AuditLog(Base):
    """Audit trail for compliance and reconciliation"""
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(String(64), ForeignKey('multi_leg_transactions.transaction_id'), nullable=True)
    leg_id = Column(String(64), nullable=True)
    batch_id = Column(String(64), nullable=True)
    
    event_type = Column(String(50), nullable=False)  # "created", "executed", "failed", "compensated"
    event_data = Column(Text, nullable=True)  # JSON string
    
    actor = Column(String(42), nullable=True)  # Who performed the action
    actor_type = Column(String(20), default="system")  # user, system, agent, contract
    
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    transaction = relationship("MultiLegTransaction", back_populates="audit_logs")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "transaction_id": self.transaction_id,
            "leg_id": self.leg_id,
            "batch_id": self.batch_id,
            "event_type": self.event_type,
            "event_data": json.loads(self.event_data) if self.event_data else {},
            "actor": self.actor,
            "actor_type": self.actor_type,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


class ReconciliationRecord(Base):
    """Records for on-chain vs off-chain reconciliation"""
    __tablename__ = 'reconciliation_records'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    record_id = Column(String(64), unique=True, nullable=False, index=True)
    
    transaction_id = Column(String(64), nullable=True, index=True)
    on_chain_tx_hash = Column(String(66), nullable=True, index=True)
    
    # Reconciliation data
    off_chain_amount = Column(String(78), nullable=True)
    on_chain_amount = Column(String(78), nullable=True)
    discrepancy = Column(String(78), nullable=True)
    
    status = Column(String(20), default="pending", nullable=False)  # pending, matched, discrepancy
    reconciled_at = Column(DateTime, nullable=True)
    
    # Metadata
    extra_metadata = Column('metadata', Text, nullable=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "record_id": self.record_id,
            "transaction_id": self.transaction_id,
            "on_chain_tx_hash": self.on_chain_tx_hash,
            "off_chain_amount": self.off_chain_amount,
            "on_chain_amount": self.on_chain_amount,
            "discrepancy": self.discrepancy,
            "status": self.status,
            "reconciled_at": self.reconciled_at.isoformat() if self.reconciled_at else None,
            "metadata": json.loads(self.extra_metadata) if self.extra_metadata else {}
        }

