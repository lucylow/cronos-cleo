"""
Human-In-The-Loop (HITL) Service for Payment Review
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from .models import (
    Base, Payment, Review, Operator, AuditLog,
    PaymentStatus, ReviewAction
)

logger = logging.getLogger(__name__)


class RiskResult:
    """Risk scoring result"""
    def __init__(self, flagged: bool, score: float, reason: Optional[str] = None):
        self.flagged = flagged
        self.score = score
        self.reason = reason


class HITLService:
    """
    Human-In-The-Loop service for payment review workflows.
    Handles risk scoring, queueing, and review management.
    """
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    async def simple_risk_score(
        self,
        tx_hash: str,
        payer: str,
        amount_wei: str,
        token_address: Optional[str] = None
    ) -> RiskResult:
        """
        Simple risk scoring based on heuristics.
        Returns RiskResult with flagged status, score, and reason.
        """
        amount = int(amount_wei)
        score = 0.0
        reasons = []
        
        # High amount threshold (e.g., 100 CRO in wei)
        HIGH_AMOUNT_WEI = 100 * 10**18
        MEDIUM_AMOUNT_WEI = 10 * 10**18
        
        if amount >= HIGH_AMOUNT_WEI:
            score += 70
            reasons.append('high_amount')
        elif amount >= MEDIUM_AMOUNT_WEI:
            score += 30
            reasons.append('medium_amount')
        
        # Check frequency: if payer has many payments in last hour -> higher risk
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent_count = self.db.query(func.count(Payment.id)).filter(
            and_(
                Payment.payer == payer,
                Payment.created_at > one_hour_ago
            )
        ).scalar() or 0
        
        if recent_count >= 5:
            score += 30
            reasons.append('high_frequency')
        elif recent_count >= 2:
            score += 10
            reasons.append('medium_frequency')
        
        # TODO: Integrate wallet history, known-bad blacklists, onchain heuristics
        flagged = score >= 50
        return RiskResult(
            flagged=flagged,
            score=score,
            reason=','.join(reasons) if reasons else None
        )
    
    async def create_payment(
        self,
        tx_hash: str,
        chain_id: int,
        payer: str,
        amount_wei: str,
        token_address: Optional[str] = None
    ) -> Payment:
        """Create a payment record"""
        # Check if payment already exists
        existing = self.db.query(Payment).filter(Payment.tx_hash == tx_hash).first()
        if existing:
            return existing
        
        payment = Payment(
            tx_hash=tx_hash,
            chain_id=chain_id,
            payer=payer,
            token_address=token_address,
            amount=amount_wei,
            status=PaymentStatus.PENDING_VERIFICATION.value
        )
        
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)
        
        await self.insert_audit(
            entity_type='payment',
            entity_id=payment.id,
            actor='system',
            action='created',
            details={'tx_hash': tx_hash, 'payer': payer}
        )
        
        return payment
    
    async def assess_and_route_payment(
        self,
        payment: Payment
    ) -> Tuple[Payment, bool]:
        """
        Assess payment risk and route accordingly.
        Returns (payment, should_enqueue) tuple.
        """
        risk = await self.simple_risk_score(
            tx_hash=payment.tx_hash,
            payer=payment.payer,
            amount_wei=payment.amount,
            token_address=payment.token_address
        )
        
        # Update payment with risk score
        payment.risk_score = Decimal(str(risk.score))
        payment.flagged_reason = risk.reason
        payment.updated_at = datetime.utcnow()
        
        if risk.flagged:
            payment.status = PaymentStatus.FLAGGED.value
            should_enqueue = True
            await self.insert_audit(
                entity_type='payment',
                entity_id=payment.id,
                actor='system',
                action='flagged_for_review',
                details={'risk_score': risk.score, 'reason': risk.reason}
            )
        else:
            payment.status = PaymentStatus.APPROVED.value
            should_enqueue = False
            await self.insert_audit(
                entity_type='payment',
                entity_id=payment.id,
                actor='system',
                action='auto_approved',
                details={'risk_score': risk.score}
            )
        
        self.db.commit()
        self.db.refresh(payment)
        
        return payment, should_enqueue
    
    async def get_pending_reviews(
        self,
        limit: int = 200
    ) -> List[Payment]:
        """Get pending flagged payments"""
        return self.db.query(Payment).filter(
            Payment.status.in_([
                PaymentStatus.FLAGGED.value,
                PaymentStatus.PENDING_MANUAL.value
            ])
        ).order_by(Payment.created_at.desc()).limit(limit).all()
    
    async def get_payment(self, payment_id: str) -> Optional[Payment]:
        """Get payment by ID"""
        return self.db.query(Payment).filter(Payment.id == payment_id).first()
    
    async def get_payment_by_tx_hash(self, tx_hash: str) -> Optional[Payment]:
        """Get payment by transaction hash"""
        return self.db.query(Payment).filter(Payment.tx_hash == tx_hash).first()
    
    async def review_payment(
        self,
        payment_id: str,
        operator_id: Optional[str],
        action: str,
        comment: Optional[str] = None,
        evidence: Optional[Dict[str, Any]] = None
    ) -> Review:
        """
        Create a review record for a payment action.
        Returns the created Review.
        """
        if action not in [a.value for a in ReviewAction]:
            raise ValueError(f"Invalid action: {action}")
        
        payment = await self.get_payment(payment_id)
        if not payment:
            raise ValueError(f"Payment {payment_id} not found")
        
        # Create review record
        review = Review(
            payment_id=payment_id,
            operator_id=operator_id,
            action=action,
            comment=comment,
            evidence=evidence or {}
        )
        
        self.db.add(review)
        
        # Update payment status
        if action == ReviewAction.APPROVED.value:
            payment.status = PaymentStatus.APPROVED.value
        elif action == ReviewAction.REJECTED.value:
            payment.status = PaymentStatus.REJECTED.value
        elif action == ReviewAction.REQUESTED_INFO.value:
            payment.status = PaymentStatus.PENDING_MANUAL.value
        
        payment.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(review)
        
        await self.insert_audit(
            entity_type='review',
            entity_id=review.id,
            actor=operator_id or 'unknown',
            action=action,
            details={'payment_id': payment_id, 'comment': comment}
        )
        
        await self.insert_audit(
            entity_type='payment',
            entity_id=payment_id,
            actor=operator_id or 'unknown',
            action=action,
            details={'comment': comment}
        )
        
        return review
    
    async def insert_audit(
        self,
        entity_type: str,
        entity_id: Optional[str],
        actor: str,
        action: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Insert audit log entry"""
        audit = AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            actor=actor,
            action=action,
            details=details or {}
        )
        self.db.add(audit)
        self.db.commit()
    
    async def get_audit_logs(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[AuditLog]:
        """Get audit logs with filters"""
        query = self.db.query(AuditLog)
        
        if entity_type:
            query = query.filter(AuditLog.entity_type == entity_type)
        if entity_id:
            query = query.filter(AuditLog.entity_id == entity_id)
        if from_date:
            query = query.filter(AuditLog.created_at >= from_date)
        if to_date:
            query = query.filter(AuditLog.created_at <= to_date)
        
        return query.order_by(AuditLog.created_at.desc()).limit(limit).all()
    
    async def create_operator(
        self,
        email: str,
        name: Optional[str] = None,
        role: str = 'reviewer'
    ) -> Operator:
        """Create an operator"""
        operator = Operator(
            email=email,
            name=name,
            role=role
        )
        self.db.add(operator)
        self.db.commit()
        self.db.refresh(operator)
        return operator
    
    async def get_operator(self, operator_id: str) -> Optional[Operator]:
        """Get operator by ID"""
        return self.db.query(Operator).filter(Operator.id == operator_id).first()
    
    async def get_operator_by_email(self, email: str) -> Optional[Operator]:
        """Get operator by email"""
        return self.db.query(Operator).filter(Operator.email == email).first()
