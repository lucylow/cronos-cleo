"""
Database models for Human-In-The-Loop (HITL) payment review system
"""
from sqlalchemy import Column, String, Integer, Numeric, DateTime, Text, ForeignKey, Boolean, JSON, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
import json
import uuid

Base = declarative_base()


class PaymentStatus(str, Enum):
    """Payment status"""
    PENDING_VERIFICATION = "pending_verification"
    VERIFIED = "verified"
    FLAGGED = "flagged"
    APPROVED = "approved"
    REJECTED = "rejected"
    REFUNDED = "refunded"
    PENDING_MANUAL = "pending_manual"


class ReviewAction(str, Enum):
    """Review action types"""
    APPROVED = "approved"
    REJECTED = "rejected"
    REQUESTED_INFO = "requested_info"


class Operator(Base):
    """Human reviewers/operators"""
    __tablename__ = 'operators'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=True)
    role = Column(String(50), default='reviewer', nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    reviews = relationship("Review", back_populates="operator")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Payment(Base):
    """Payment records for HITL review"""
    __tablename__ = 'hitl_payments'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tx_hash = Column(String(66), unique=True, nullable=False, index=True)
    chain_id = Column(Integer, nullable=False)
    payer = Column(String(42), nullable=False, index=True)
    token_address = Column(String(42), nullable=True)  # null for native CRO
    amount = Column(String(78), nullable=False)  # Store as string for large numbers (wei)
    status = Column(String(50), default=PaymentStatus.PENDING_VERIFICATION.value, nullable=False, index=True)
    risk_score = Column(Numeric(5, 2), nullable=True)
    flagged_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    reviews = relationship("Review", back_populates="payment", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_payments_status', 'status'),
        Index('idx_payments_tx_hash', 'tx_hash'),
        Index('idx_payments_created', 'created_at'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tx_hash": self.tx_hash,
            "chain_id": self.chain_id,
            "payer": self.payer,
            "token_address": self.token_address,
            "amount": self.amount,
            "status": self.status,
            "risk_score": float(self.risk_score) if self.risk_score else None,
            "flagged_reason": self.flagged_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class Review(Base):
    """Review records: each human action creates a review"""
    __tablename__ = 'hitl_reviews'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    payment_id = Column(String(36), ForeignKey('hitl_payments.id', ondelete='CASCADE'), nullable=False, index=True)
    operator_id = Column(String(36), ForeignKey('operators.id'), nullable=True)
    action = Column(String(50), nullable=False)  # approved, rejected, requested_info
    comment = Column(Text, nullable=True)
    evidence = Column(JSON, nullable=True)  # Store evidence as JSON
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    payment = relationship("Payment", back_populates="reviews")
    operator = relationship("Operator", back_populates="reviews")
    
    __table_args__ = (
        Index('idx_reviews_payment', 'payment_id'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "payment_id": self.payment_id,
            "operator_id": self.operator_id,
            "action": self.action,
            "comment": self.comment,
            "evidence": self.evidence,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class AuditLog(Base):
    """Audit log (append-only)"""
    __tablename__ = 'hitl_audit_logs'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(String(36), nullable=True, index=True)
    actor = Column(String(255), nullable=False)  # operator ID, 'system', etc.
    action = Column(String(100), nullable=False)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    __table_args__ = (
        Index('idx_audit_entity', 'entity_type', 'entity_id'),
        Index('idx_audit_created', 'created_at'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "actor": self.actor,
            "action": self.action,
            "details": self.details,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
