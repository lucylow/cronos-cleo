"""
Background worker for HITL payment review system
Gathers evidence and enriches payment records
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from web3 import Web3
from sqlalchemy.orm import Session

from .models import Payment, PaymentStatus
from .service import HITLService

logger = logging.getLogger(__name__)


class EvidenceGatherer:
    """Gathers on-chain evidence for payment reviews"""
    
    def __init__(self, w3: Web3, db_session: Session):
        self.w3 = w3
        self.db = db_session
        self.hitl_service = HITLService(db_session)
    
    async def gather_evidence(self, payment: Payment) -> Dict[str, Any]:
        """
        Gather on-chain evidence for a payment.
        Returns evidence dictionary.
        """
        try:
            tx_hash = payment.tx_hash
            
            # Get transaction details
            tx = self.w3.eth.get_transaction(tx_hash)
            receipt = self.w3.eth.get_transaction_receipt(tx_hash)
            
            # Get block details
            block = None
            if tx and tx.get('blockNumber'):
                block = self.w3.eth.get_block(tx['blockNumber'])
            
            # Get payer balance
            payer_balance = None
            if payment.payer:
                try:
                    payer_balance = self.w3.eth.get_balance(payment.payer)
                except Exception as e:
                    logger.warning(f"Could not get balance for {payment.payer}: {e}")
            
            evidence = {
                "tx": {
                    "hash": tx_hash,
                    "from": tx.get('from') if tx else None,
                    "to": tx.get('to') if tx else None,
                    "value": str(tx.get('value', 0)) if tx else None,
                    "gas": tx.get('gas') if tx else None,
                    "gasPrice": str(tx.get('gasPrice', 0)) if tx else None,
                },
                "receipt": {
                    "status": receipt.get('status') if receipt else None,
                    "blockNumber": receipt.get('blockNumber') if receipt else None,
                    "gasUsed": receipt.get('gasUsed') if receipt else None,
                },
                "block": {
                    "number": block.get('number') if block else None,
                    "timestamp": block.get('timestamp') if block else None,
                } if block else None,
                "payerBalance": str(payer_balance) if payer_balance else None,
                "fetchedAt": datetime.utcnow().isoformat()
            }
            
            return evidence
            
        except Exception as e:
            logger.error(f"Error gathering evidence for payment {payment.id}: {e}", exc_info=True)
            return {
                "error": str(e),
                "fetchedAt": datetime.utcnow().isoformat()
            }
    
    async def enrich_payment(self, payment_id: str) -> Dict[str, Any]:
        """
        Enrich a payment with evidence and update status.
        Called by background worker.
        """
        payment = self.hitl_service.db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            logger.warning(f"Payment {payment_id} not found")
            return {"error": "payment_not_found"}
        
        # Gather evidence
        evidence = await self.gather_evidence(payment)
        
        # Update payment status to flagged (if not already)
        if payment.status == PaymentStatus.PENDING_VERIFICATION.value:
            payment.status = PaymentStatus.FLAGGED.value
            self.hitl_service.db.commit()
        
        # Log enrichment
        await self.hitl_service.insert_audit(
            entity_type='payment',
            entity_id=payment_id,
            actor='system',
            action='job_enriched',
            details={'evidence_summary': 'evidence_attached'}
        )
        
        return {
            "payment_id": payment_id,
            "status": "waiting_for_human",
            "evidence": evidence
        }


# For use with RQ or Celery worker
def enrich_payment_job(payment_id: str, rpc_url: str, database_url: str):
    """
    Job function for RQ/Celery worker.
    This is a synchronous wrapper for async evidence gathering.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from web3 import Web3
    from datetime import datetime
    
    # Setup
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    db_session = Session()
    
    try:
        gatherer = EvidenceGatherer(w3, db_session)
        
        # Run async function in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(gatherer.enrich_payment(payment_id))
            return result
        finally:
            loop.close()
    finally:
        db_session.close()
