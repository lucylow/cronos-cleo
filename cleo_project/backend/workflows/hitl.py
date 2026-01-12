"""
Human-In-The-Loop (HITL) System - Review and approval workflows
"""
import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum

from .models import HumanReviewRequest, WorkflowExecution, TaskStatus

logger = logging.getLogger(__name__)


class ReviewStatus(str, Enum):
    """Human review request status"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    DELEGATED = "delegated"


class HITLService:
    """
    Human-In-The-Loop service for review and approval workflows.
    Supports review queues, approvals, rejections, escalations, and delegation.
    """
    
    def __init__(self, storage: Optional[Any] = None):
        self.storage = storage
        self.pending_reviews: Dict[str, HumanReviewRequest] = {}
        self.review_callbacks: Dict[str, asyncio.Event] = {}  # review_id -> event
        self.review_results: Dict[str, Dict[str, Any]] = {}  # review_id -> result
        
        # Role-based access (simplified - enhance with proper RBAC)
        self.user_roles: Dict[str, List[str]] = {}  # user_id -> roles
        self.role_permissions: Dict[str, List[str]] = {}  # role -> permissions
    
    async def request_review(
        self,
        execution_id: str,
        task_id: str,
        workflow_id: str,
        requested_by: str,
        evidence: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        due_in_hours: Optional[int] = 24,
        required_roles: Optional[List[str]] = None,
        sla_seconds: Optional[int] = None
    ) -> HumanReviewRequest:
        """
        Request human review/approval
        
        Args:
            execution_id: Workflow execution ID
            task_id: Task ID requesting review
            workflow_id: Workflow ID
            requested_by: User/system requesting review
            evidence: Data/context for human to review
            context: Additional context
            due_in_hours: Hours until review is due
            required_roles: Roles that can approve (None = any authenticated user)
            sla_seconds: SLA in seconds (overrides due_in_hours)
        
        Returns:
            HumanReviewRequest instance
        """
        review_id = f"review_{uuid.uuid4().hex[:16]}"
        
        due_at = None
        if sla_seconds:
            due_at = datetime.now() + timedelta(seconds=sla_seconds)
        elif due_in_hours:
            due_at = datetime.now() + timedelta(hours=due_in_hours)
        
        review = HumanReviewRequest(
            review_id=review_id,
            execution_id=execution_id,
            task_id=task_id,
            workflow_id=workflow_id,
            requested_by=requested_by,
            requested_at=datetime.now(),
            due_at=due_at,
            status=ReviewStatus.PENDING.value,
            evidence=evidence,
            context=context or {},
            metadata={
                "required_roles": required_roles or [],
                "sla_seconds": sla_seconds
            }
        )
        
        self.pending_reviews[review_id] = review
        self.review_callbacks[review_id] = asyncio.Event()
        
        if self.storage:
            await self.storage.save_review_request(review)
        
        logger.info(
            f"Human review requested: {review_id} for execution {execution_id}, "
            f"due at {due_at}"
        )
        
        # Start SLA monitoring
        if due_at:
            asyncio.create_task(self._monitor_review_sla(review_id, due_at))
        
        return review
    
    async def _monitor_review_sla(self, review_id: str, due_at: datetime):
        """Monitor review SLA and expire if overdue"""
        try:
            wait_seconds = (due_at - datetime.now()).total_seconds()
            if wait_seconds > 0:
                await asyncio.sleep(wait_seconds)
            
            # Check if review is still pending
            review = self.pending_reviews.get(review_id)
            if review and review.status == ReviewStatus.PENDING.value:
                review.status = ReviewStatus.EXPIRED.value
                review.reviewed_at = datetime.now()
                
                if self.storage:
                    await self.storage.save_review_request(review)
                
                # Notify waiting workflow
                if review_id in self.review_callbacks:
                    self.review_callbacks[review_id].set()
                
                logger.warning(f"Review {review_id} expired (SLA breach)")
        
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error monitoring review SLA: {e}", exc_info=True)
    
    async def approve_review(
        self,
        review_id: str,
        approver: str,
        comment: Optional[str] = None
    ) -> bool:
        """
        Approve a review request
        
        Returns:
            True if approved successfully
        """
        review = self.pending_reviews.get(review_id)
        if not review:
            logger.warning(f"Review {review_id} not found")
            return False
        
        if review.status != ReviewStatus.PENDING.value:
            logger.warning(f"Review {review_id} already {review.status}")
            return False
        
        # Check permissions (simplified)
        required_roles = review.metadata.get("required_roles", [])
        if required_roles:
            user_roles = self.user_roles.get(approver, [])
            if not any(role in user_roles for role in required_roles):
                logger.warning(f"User {approver} lacks required roles for review {review_id}")
                return False
        
        # Approve
        review.status = ReviewStatus.APPROVED.value
        review.approver = approver
        review.reviewed_at = datetime.now()
        review.comment = comment
        
        if self.storage:
            await self.storage.save_review_request(review)
        
        # Notify waiting workflow
        self.review_results[review_id] = {
            "status": "approved",
            "approver": approver,
            "comment": comment
        }
        
        if review_id in self.review_callbacks:
            self.review_callbacks[review_id].set()
        
        logger.info(f"Review {review_id} approved by {approver}")
        return True
    
    async def reject_review(
        self,
        review_id: str,
        approver: str,
        comment: Optional[str] = None
    ) -> bool:
        """Reject a review request"""
        review = self.pending_reviews.get(review_id)
        if not review or review.status != ReviewStatus.PENDING.value:
            return False
        
        # Check permissions
        required_roles = review.metadata.get("required_roles", [])
        if required_roles:
            user_roles = self.user_roles.get(approver, [])
            if not any(role in user_roles for role in required_roles):
                return False
        
        review.status = ReviewStatus.REJECTED.value
        review.approver = approver
        review.reviewed_at = datetime.now()
        review.comment = comment
        
        if self.storage:
            await self.storage.save_review_request(review)
        
        self.review_results[review_id] = {
            "status": "rejected",
            "approver": approver,
            "comment": comment
        }
        
        if review_id in self.review_callbacks:
            self.review_callbacks[review_id].set()
        
        logger.info(f"Review {review_id} rejected by {approver}")
        return True
    
    async def wait_for_review(self, review_id: str, timeout_seconds: Optional[int] = None) -> Dict[str, Any]:
        """
        Wait for a review to complete (used by workflow engine)
        
        Returns:
            Review result dictionary
        """
        if review_id not in self.review_callbacks:
            return {"status": "not_found"}
        
        event = self.review_callbacks[review_id]
        
        try:
            if timeout_seconds:
                await asyncio.wait_for(event.wait(), timeout=timeout_seconds)
            else:
                await event.wait()
            
            return self.review_results.get(review_id, {"status": "pending"})
        
        except asyncio.TimeoutError:
            logger.warning(f"Review {review_id} wait timed out")
            return {"status": "timeout"}
    
    async def get_pending_reviews(
        self,
        user_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        role: Optional[str] = None
    ) -> List[HumanReviewRequest]:
        """Get pending review requests (filtered by user/role if provided)"""
        reviews = list(self.pending_reviews.values())
        
        # Filter by status
        reviews = [r for r in reviews if r.status == ReviewStatus.PENDING.value]
        
        # Filter by workflow
        if workflow_id:
            reviews = [r for r in reviews if r.workflow_id == workflow_id]
        
        # Filter by role/permissions
        if user_id or role:
            filtered = []
            for review in reviews:
                required_roles = review.metadata.get("required_roles", [])
                if not required_roles:
                    filtered.append(review)
                elif user_id:
                    user_roles = self.user_roles.get(user_id, [])
                    if any(r in user_roles for r in required_roles):
                        filtered.append(review)
                elif role:
                    if role in required_roles:
                        filtered.append(review)
            reviews = filtered
        
        return reviews
    
    async def get_review(self, review_id: str) -> Optional[HumanReviewRequest]:
        """Get a review request by ID"""
        if review_id in self.pending_reviews:
            return self.pending_reviews[review_id]
        
        if self.storage:
            return await self.storage.get_review_request(review_id)
        
        return None
    
    def assign_user_role(self, user_id: str, role: str):
        """Assign a role to a user (simplified RBAC)"""
        if user_id not in self.user_roles:
            self.user_roles[user_id] = []
        if role not in self.user_roles[user_id]:
            self.user_roles[user_id].append(role)
            logger.info(f"Assigned role {role} to user {user_id}")
    
    def remove_user_role(self, user_id: str, role: str):
        """Remove a role from a user"""
        if user_id in self.user_roles:
            if role in self.user_roles[user_id]:
                self.user_roles[user_id].remove(role)
                logger.info(f"Removed role {role} from user {user_id}")

