"""
FastAPI endpoints for HITL payment review system
"""
import os
import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from web3 import Web3

from .models import Payment, Review, Operator, AuditLog
from .service import HITLService
from .worker import EvidenceGatherer

logger = logging.getLogger(__name__)

# Router for HITL endpoints
router = APIRouter(prefix="/api/hitl", tags=["HITL"])

# Global WebSocket manager (in production, use Redis pub/sub for multi-instance)
class ConnectionManager:
    """Manages WebSocket connections for operator notifications"""
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.operator_connections: dict = {}  # operator_id -> WebSocket
    
    async def connect(self, websocket: WebSocket, operator_id: Optional[str] = None):
        await websocket.accept()
        self.active_connections.append(websocket)
        if operator_id:
            self.operator_connections[operator_id] = websocket
        logger.info(f"WebSocket connected: {len(self.active_connections)} total")
    
    def disconnect(self, websocket: WebSocket, operator_id: Optional[str] = None):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if operator_id and operator_id in self.operator_connections:
            del self.operator_connections[operator_id]
        logger.info(f"WebSocket disconnected: {len(self.active_connections)} total")
    
    async def send_personal_message(self, message: dict, operator_id: str):
        """Send message to specific operator"""
        if operator_id in self.operator_connections:
            await self.operator_connections[operator_id].send_json(message)
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected operators"""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Error broadcasting to connection: {e}")

manager = ConnectionManager()

# Dependency to get database session
def get_db_session():
    """Get database session (to be injected from main app)"""
    # This will be set by the main app
    return get_db_session._session

get_db_session._session = None

# Dependency to get HITL service
def get_hitl_service(db: Session = Depends(get_db_session)) -> HITLService:
    return HITLService(db)

# Request/Response models
class PaymentObserveRequest(BaseModel):
    txHash: str
    chainId: int
    payer: str
    amountWei: str
    tokenAddress: Optional[str] = None

class PaymentObserveResponse(BaseModel):
    ok: bool
    status: str
    paymentId: Optional[str] = None
    jobId: Optional[str] = None
    error: Optional[str] = None

class ReviewActionRequest(BaseModel):
    operatorId: Optional[str] = None
    action: str  # approve, reject, request_info
    comment: Optional[str] = None

class ReviewActionResponse(BaseModel):
    ok: bool
    result: str
    reviewId: Optional[str] = None
    error: Optional[str] = None


@router.post("/payments/observe", response_model=PaymentObserveResponse)
async def observe_payment(
    request: PaymentObserveRequest,
    hitl_service: HITLService = Depends(get_hitl_service)
):
    """
    Observe a payment transaction and route it through HITL workflow.
    This endpoint is called when a payment is detected on-chain.
    """
    try:
        # Create payment record
        payment = await hitl_service.create_payment(
            tx_hash=request.txHash,
            chain_id=request.chainId,
            payer=request.payer,
            amount_wei=request.amountWei,
            token_address=request.tokenAddress
        )
        
        # Assess risk and route
        payment, should_enqueue = await hitl_service.assess_and_route_payment(payment)
        
        if should_enqueue:
            # Enqueue for review (in production, use RQ/Celery)
            # For now, we'll trigger evidence gathering asynchronously
            # In production: job = review_queue.enqueue(enrich_payment_job, payment.id, ...)
            
            # Notify operators via WebSocket
            await manager.broadcast({
                "type": "review:enqueue",
                "payment": {
                    "id": payment.id,
                    "tx_hash": payment.tx_hash,
                    "payer": payment.payer,
                    "amount": payment.amount,
                    "risk_score": float(payment.risk_score) if payment.risk_score else None
                }
            })
            
            return PaymentObserveResponse(
                ok=True,
                status="flagged",
                paymentId=payment.id
            )
        else:
            # Auto-approved
            await manager.broadcast({
                "type": "payment:finalized",
                "paymentId": payment.id,
                "status": "approved"
            })
            
            return PaymentObserveResponse(
                ok=True,
                status="approved",
                paymentId=payment.id
            )
            
    except Exception as e:
        logger.error(f"Error observing payment: {e}", exc_info=True)
        return PaymentObserveResponse(
            ok=False,
            status="error",
            error=str(e)
        )


@router.get("/admin/pending")
async def get_pending_reviews(
    limit: int = 200,
    hitl_service: HITLService = Depends(get_hitl_service)
):
    """Get pending payment reviews"""
    try:
        payments = await hitl_service.get_pending_reviews(limit=limit)
        return {
            "ok": True,
            "pending": [p.to_dict() for p in payments]
        }
    except Exception as e:
        logger.error(f"Error getting pending reviews: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/payment/{payment_id}")
async def get_payment(
    payment_id: str,
    hitl_service: HITLService = Depends(get_hitl_service)
):
    """Get payment details by ID"""
    payment = await hitl_service.get_payment(payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    return {
        "ok": True,
        "payment": payment.to_dict()
    }


@router.post("/admin/payment/{payment_id}/action", response_model=ReviewActionResponse)
async def review_payment_action(
    payment_id: str,
    request: ReviewActionRequest,
    hitl_service: HITLService = Depends(get_hitl_service)
):
    """Approve, reject, or request info for a payment"""
    try:
        if request.action not in ["approve", "reject", "request_info"]:
            raise HTTPException(status_code=400, detail="Invalid action")
        
        review = await hitl_service.review_payment(
            payment_id=payment_id,
            operator_id=request.operatorId,
            action=request.action,
            comment=request.comment
        )
        
        # Notify via WebSocket
        await manager.broadcast({
            "type": "review:action",
            "paymentId": payment_id,
            "action": request.action,
            "operatorId": request.operatorId
        })
        
        return ReviewActionResponse(
            ok=True,
            result=request.action,
            reviewId=review.id
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error reviewing payment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/audit/export")
async def export_audit_logs(
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = 1000,
    hitl_service: HITLService = Depends(get_hitl_service)
):
    """Export audit logs as JSON"""
    from datetime import datetime
    
    from_dt = datetime.fromisoformat(from_date) if from_date else None
    to_dt = datetime.fromisoformat(to_date) if to_date else None
    
    logs = await hitl_service.get_audit_logs(
        entity_type=entity_type,
        entity_id=entity_id,
        from_date=from_dt,
        to_date=to_dt,
        limit=limit
    )
    
    return {
        "ok": True,
        "logs": [log.to_dict() for log in logs]
    }


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for operator notifications"""
    await manager.connect(websocket)
    operator_id = None
    
    try:
        while True:
            data = await websocket.receive_json()
            
            # Handle operator identification
            if data.get("type") == "identify":
                operator_id = data.get("operatorId")
                # Reconnect with operator ID
                manager.disconnect(websocket)
                await manager.connect(websocket, operator_id)
                await websocket.send_json({"type": "identified", "operatorId": operator_id})
            
            # Handle ping/pong
            elif data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, operator_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        manager.disconnect(websocket, operator_id)
