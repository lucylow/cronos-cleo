"""
Reconciliation Service
Reconciles on-chain state with off-chain ledger records
"""
import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from decimal import Decimal
import uuid

from sqlalchemy.orm import Session
from web3 import Web3

from .models import (
    ReconciliationRecord, MultiLegTransaction, TransactionLeg,
    AuditLog
)

logger = logging.getLogger(__name__)


class ReconciliationService:
    """
    Service for reconciling on-chain transactions with off-chain records
    
    Features:
    - On-chain vs off-chain comparison
    - Discrepancy detection
    - Automated reconciliation
    - Audit trails
    """
    
    def __init__(self, db_session: Session, w3: Web3):
        self.db = db_session
        self.w3 = w3
    
    def create_reconciliation_record(
        self,
        transaction_id: Optional[str] = None,
        on_chain_tx_hash: Optional[str] = None,
        off_chain_amount: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ReconciliationRecord:
        """
        Create a reconciliation record
        
        Args:
            transaction_id: Transaction ID
            on_chain_tx_hash: On-chain transaction hash
            off_chain_amount: Off-chain recorded amount
            metadata: Optional metadata
            
        Returns:
            ReconciliationRecord
        """
        record_id = f"recon_{uuid.uuid4().hex[:16]}_{int(datetime.now().timestamp())}"
        
        record = ReconciliationRecord(
            record_id=record_id,
            transaction_id=transaction_id,
            on_chain_tx_hash=on_chain_tx_hash,
            off_chain_amount=off_chain_amount,
            status="pending",
            metadata=json.dumps(metadata) if metadata else None
        )
        
        self.db.add(record)
        self.db.commit()
        
        logger.info(f"Created reconciliation record: {record_id}")
        
        return record
    
    async def reconcile_transaction(
        self,
        transaction_id: str,
        on_chain_tx_hash: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Reconcile a transaction's on-chain and off-chain state
        
        Args:
            transaction_id: Transaction ID to reconcile
            on_chain_tx_hash: Optional on-chain transaction hash
            
        Returns:
            Reconciliation result
        """
        transaction = self.db.query(MultiLegTransaction).filter_by(
            transaction_id=transaction_id
        ).first()
        
        if not transaction:
            raise ValueError(f"Transaction not found: {transaction_id}")
        
        # Get on-chain transaction hash if not provided
        if not on_chain_tx_hash:
            on_chain_tx_hash = transaction.on_chain_tx_hash
        
        if not on_chain_tx_hash:
            return {
                "status": "pending",
                "message": "No on-chain transaction hash available"
            }
        
        # Fetch on-chain transaction receipt
        try:
            tx_hash_bytes = bytes.fromhex(on_chain_tx_hash.replace('0x', ''))
            receipt = self.w3.eth.get_transaction_receipt(tx_hash_bytes)
        except Exception as e:
            logger.error(f"Failed to fetch on-chain transaction: {e}")
            return {
                "status": "error",
                "message": f"Failed to fetch on-chain transaction: {e}"
            }
        
        # Calculate off-chain total
        legs = self.db.query(TransactionLeg).filter_by(
            transaction_id=transaction_id
        ).all()
        
        off_chain_total = Decimal(0)
        for leg in legs:
            if leg.amount_out:
                off_chain_total += Decimal(leg.amount_out)
        
        # Compare with on-chain state
        # This is simplified - in production, you'd parse events/logs from receipt
        on_chain_amount = str(receipt.gasUsed)  # Placeholder - should parse actual amounts
        
        discrepancy = None
        if off_chain_total != Decimal(on_chain_amount):
            discrepancy = str(off_chain_total - Decimal(on_chain_amount))
        
        # Create or update reconciliation record
        record = self.db.query(ReconciliationRecord).filter_by(
            transaction_id=transaction_id
        ).first()
        
        if not record:
            record = self.create_reconciliation_record(
                transaction_id=transaction_id,
                on_chain_tx_hash=on_chain_tx_hash,
                off_chain_amount=str(off_chain_total)
            )
        
        record.on_chain_amount = on_chain_amount
        record.discrepancy = discrepancy
        record.status = "matched" if not discrepancy else "discrepancy"
        record.reconciled_at = datetime.utcnow()
        
        self.db.commit()
        
        return {
            "status": record.status,
            "transaction_id": transaction_id,
            "off_chain_amount": str(off_chain_total),
            "on_chain_amount": on_chain_amount,
            "discrepancy": discrepancy,
            "reconciled_at": record.reconciled_at.isoformat() if record.reconciled_at else None
        }
    
    def get_reconciliation_records(
        self,
        transaction_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[ReconciliationRecord]:
        """Get reconciliation records"""
        query = self.db.query(ReconciliationRecord)
        
        if transaction_id:
            query = query.filter_by(transaction_id=transaction_id)
        
        if status:
            query = query.filter_by(status=status)
        
        return query.order_by(ReconciliationRecord.reconciled_at.desc()).all()
    
    async def batch_reconcile(
        self,
        transaction_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Reconcile multiple transactions in batch
        
        Args:
            transaction_ids: List of transaction IDs
            
        Returns:
            Batch reconciliation results
        """
        results = {
            "total": len(transaction_ids),
            "matched": 0,
            "discrepancies": 0,
            "errors": 0,
            "details": []
        }
        
        for transaction_id in transaction_ids:
            try:
                result = await self.reconcile_transaction(transaction_id)
                results["details"].append({
                    "transaction_id": transaction_id,
                    "status": result["status"]
                })
                
                if result["status"] == "matched":
                    results["matched"] += 1
                elif result["status"] == "discrepancy":
                    results["discrepancies"] += 1
                else:
                    results["errors"] += 1
                    
            except Exception as e:
                logger.error(f"Reconciliation failed for {transaction_id}: {e}")
                results["errors"] += 1
                results["details"].append({
                    "transaction_id": transaction_id,
                    "status": "error",
                    "error": str(e)
                })
        
        return results

