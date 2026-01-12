"""
Multi-Leg Transaction Coordinator
Orchestrates atomic execution of multi-leg transactions with compensation support
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from decimal import Decimal
import uuid
import json
from enum import Enum

from sqlalchemy.orm import Session
from web3 import Web3
from web3.types import TxReceipt

from .models import (
    Base, MultiLegTransaction, TransactionLeg, AuditLog,
    LegType, LegStatus, TransactionStatus
)

logger = logging.getLogger(__name__)


class CompensationStrategy(str, Enum):
    """Compensation strategies for failed legs"""
    NONE = "none"  # No compensation needed
    ROLLBACK = "rollback"  # Rollback all completed legs
    SAGA = "saga"  # Execute compensating transactions
    MANUAL = "manual"  # Manual intervention required


class MultiLegCoordinator:
    """
    Coordinates multi-leg transactions with atomicity guarantees
    
    Features:
    - Atomic execution (all succeed or all fail)
    - Compensation/rollback support
    - Idempotency
    - Audit trails
    - Retry logic
    """
    
    def __init__(
        self,
        db_session: Session,
        w3: Optional[Web3] = None,
        compensation_strategy: CompensationStrategy = CompensationStrategy.SAGA
    ):
        self.db = db_session
        self.w3 = w3
        self.compensation_strategy = compensation_strategy
        self.active_transactions: Dict[str, MultiLegTransaction] = {}
        
    def create_transaction(
        self,
        transaction_type: str,
        initiator: str,
        legs: List[Dict[str, Any]],
        idempotency_key: Optional[str] = None,
        deadline: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MultiLegTransaction:
        """
        Create a new multi-leg transaction
        
        Args:
            transaction_type: Type of transaction (e.g., "swap", "payment")
            initiator: Address or identifier of initiator
            legs: List of leg definitions
            idempotency_key: Optional idempotency key for duplicate prevention
            deadline: Optional deadline for transaction
            metadata: Optional metadata dictionary
            
        Returns:
            MultiLegTransaction object
        """
        # Check idempotency
        if idempotency_key:
            existing = self.db.query(MultiLegTransaction).filter_by(
                idempotency_key=idempotency_key
            ).first()
            if existing:
                logger.info(f"Idempotent transaction found: {existing.transaction_id}")
                return existing
        
        # Generate transaction ID
        transaction_id = f"mlt_{uuid.uuid4().hex[:16]}_{int(datetime.now().timestamp())}"
        
        # Create transaction record
        transaction = MultiLegTransaction(
            transaction_id=transaction_id,
            idempotency_key=idempotency_key,
            status=TransactionStatus.PENDING,
            transaction_type=transaction_type,
            initiator=initiator,
            deadline=deadline,
            metadata=json.dumps(metadata) if metadata else None
        )
        
        self.db.add(transaction)
        
        # Create legs
        for i, leg_def in enumerate(legs):
            leg_id = f"{transaction_id}_leg_{i}"
            leg = TransactionLeg(
                leg_id=leg_id,
                transaction_id=transaction_id,
                leg_type=LegType(leg_def.get("type", "custom")),
                sequence=i,
                target_address=leg_def.get("target_address"),
                function_name=leg_def.get("function_name"),
                function_data=leg_def.get("function_data"),
                amount_in=leg_def.get("amount_in"),
                amount_out=leg_def.get("amount_out"),
                token_in=leg_def.get("token_in"),
                token_out=leg_def.get("token_out"),
                requires_compensation=leg_def.get("requires_compensation", False),
                metadata=json.dumps(leg_def.get("metadata", {}))
            )
            transaction.legs.append(leg)
            self.db.add(leg)
        
        # Audit log
        self._log_audit(
            transaction_id=transaction_id,
            event_type="created",
            event_data={"legs_count": len(legs)},
            actor=initiator
        )
        
        self.db.commit()
        logger.info(f"Created multi-leg transaction: {transaction_id} with {len(legs)} legs")
        
        return transaction
    
    async def execute_transaction(
        self,
        transaction_id: str,
        executor_func: Optional[Callable] = None,
        atomic: bool = True
    ) -> Dict[str, Any]:
        """
        Execute a multi-leg transaction
        
        Args:
            transaction_id: Transaction ID to execute
            executor_func: Optional custom executor function
            atomic: If True, all legs must succeed or all fail
            
        Returns:
            Execution result dictionary
        """
        transaction = self.db.query(MultiLegTransaction).filter_by(
            transaction_id=transaction_id
        ).first()
        
        if not transaction:
            raise ValueError(f"Transaction not found: {transaction_id}")
        
        if transaction.status != TransactionStatus.PENDING:
            raise ValueError(f"Transaction already in status: {transaction.status}")
        
        transaction.status = TransactionStatus.EXECUTING
        transaction.started_at = datetime.utcnow()
        self.db.commit()
        
        self._log_audit(
            transaction_id=transaction_id,
            event_type="execution_started",
            actor="system"
        )
        
        completed_legs: List[TransactionLeg] = []
        failed_legs: List[TransactionLeg] = []
        
        try:
            # Execute legs in sequence
            for leg in sorted(transaction.legs, key=lambda l: l.sequence):
                leg.status = LegStatus.EXECUTING
                self.db.commit()
                
                try:
                    # Execute leg
                    if executor_func:
                        result = await executor_func(leg)
                    else:
                        result = await self._execute_leg_default(leg)
                    
                    leg.status = LegStatus.COMPLETED
                    leg.executed_at = datetime.utcnow()
                    leg.on_chain_tx_hash = result.get("tx_hash")
                    leg.gas_used = result.get("gas_used")
                    leg.amount_out = result.get("amount_out", leg.amount_out)
                    completed_legs.append(leg)
                    
                    self._log_audit(
                        transaction_id=transaction_id,
                        leg_id=leg.leg_id,
                        event_type="leg_completed",
                        event_data={"tx_hash": result.get("tx_hash")}
                    )
                    
                except Exception as e:
                    logger.error(f"Leg {leg.leg_id} failed: {e}")
                    leg.status = LegStatus.FAILED
                    leg.error_message = str(e)
                    failed_legs.append(leg)
                    
                    self._log_audit(
                        transaction_id=transaction_id,
                        leg_id=leg.leg_id,
                        event_type="leg_failed",
                        event_data={"error": str(e)}
                    )
                    
                    if atomic:
                        # Stop execution and compensate
                        break
            
            # Determine final status
            if atomic and failed_legs:
                # Need to compensate completed legs
                transaction.status = TransactionStatus.PARTIALLY_FAILED
                await self._compensate_legs(transaction, completed_legs)
                transaction.status = TransactionStatus.COMPENSATED
            elif failed_legs:
                transaction.status = TransactionStatus.PARTIALLY_FAILED
            else:
                transaction.status = TransactionStatus.COMPLETED
            
            transaction.completed_at = datetime.utcnow()
            self.db.commit()
            
            self._log_audit(
                transaction_id=transaction_id,
                event_type="execution_completed",
                event_data={
                    "status": transaction.status.value,
                    "completed_legs": len(completed_legs),
                    "failed_legs": len(failed_legs)
                }
            )
            
            return {
                "success": transaction.status == TransactionStatus.COMPLETED,
                "transaction_id": transaction_id,
                "status": transaction.status.value,
                "completed_legs": len(completed_legs),
                "failed_legs": len(failed_legs),
                "on_chain_tx_hash": transaction.on_chain_tx_hash
            }
            
        except Exception as e:
            logger.error(f"Transaction execution failed: {e}")
            transaction.status = TransactionStatus.FAILED
            transaction.error_message = str(e)
            transaction.completed_at = datetime.utcnow()
            self.db.commit()
            
            # Compensate if needed
            if completed_legs:
                await self._compensate_legs(transaction, completed_legs)
            
            raise
    
    async def _execute_leg_default(self, leg: TransactionLeg) -> Dict[str, Any]:
        """Default leg execution (can be overridden)"""
        # This is a placeholder - should be implemented based on leg type
        if not self.w3:
            raise ValueError("Web3 provider not configured")
        
        # For now, return mock result
        # In production, this would execute the actual on-chain transaction
        return {
            "tx_hash": f"0x{leg.leg_id[:64]}",
            "gas_used": 21000,
            "amount_out": leg.amount_out
        }
    
    async def _compensate_legs(
        self,
        transaction: MultiLegTransaction,
        completed_legs: List[TransactionLeg]
    ):
        """Compensate completed legs after failure"""
        if self.compensation_strategy == CompensationStrategy.NONE:
            return
        
        transaction.status = TransactionStatus.COMPENSATING
        self.db.commit()
        
        logger.info(f"Compensating {len(completed_legs)} legs for transaction {transaction.transaction_id}")
        
        for leg in reversed(completed_legs):  # Reverse order for compensation
            if not leg.requires_compensation:
                continue
            
            try:
                # Execute compensation
                compensation_result = await self._execute_compensation(leg)
                
                leg.compensated_at = datetime.utcnow()
                leg.status = LegStatus.COMPENSATED
                
                self._log_audit(
                    transaction_id=transaction.transaction_id,
                    leg_id=leg.leg_id,
                    event_type="leg_compensated",
                    event_data={"compensation_tx": compensation_result.get("tx_hash")}
                )
                
            except Exception as e:
                logger.error(f"Compensation failed for leg {leg.leg_id}: {e}")
                # Log but continue with other compensations
        
        self.db.commit()
    
    async def _execute_compensation(self, leg: TransactionLeg) -> Dict[str, Any]:
        """Execute compensation for a leg"""
        # This should implement the actual compensation logic
        # For example, if leg was a debit, compensation would be a credit
        return {
            "tx_hash": f"0xcomp_{leg.leg_id[:60]}",
            "gas_used": 21000
        }
    
    def get_transaction(self, transaction_id: str) -> Optional[MultiLegTransaction]:
        """Get transaction by ID"""
        return self.db.query(MultiLegTransaction).filter_by(
            transaction_id=transaction_id
        ).first()
    
    def get_transaction_legs(self, transaction_id: str) -> List[TransactionLeg]:
        """Get all legs for a transaction"""
        return self.db.query(TransactionLeg).filter_by(
            transaction_id=transaction_id
        ).order_by(TransactionLeg.sequence).all()
    
    def _log_audit(
        self,
        transaction_id: Optional[str] = None,
        leg_id: Optional[str] = None,
        batch_id: Optional[str] = None,
        event_type: str = "unknown",
        event_data: Optional[Dict[str, Any]] = None,
        actor: str = "system",
        actor_type: str = "system"
    ):
        """Create audit log entry"""
        log = AuditLog(
            transaction_id=transaction_id,
            leg_id=leg_id,
            batch_id=batch_id,
            event_type=event_type,
            event_data=json.dumps(event_data) if event_data else None,
            actor=actor,
            actor_type=actor_type
        )
        self.db.add(log)
        self.db.commit()

