"""
Workflow data models and specifications
"""
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field
from decimal import Decimal


class WorkflowStatus(str, Enum):
    """Workflow execution status"""
    PENDING = "pending"
    RUNNING = "running"
    WAITING_HUMAN = "waiting_human"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class TaskStatus(str, Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING_RETRY = "waiting_retry"


class TriggerType(str, Enum):
    """Types of workflow triggers"""
    SCHEDULED = "scheduled"  # Cron/time-based
    EVENT = "event"  # Blockchain event, message queue event
    API = "api"  # REST API call
    MANUAL = "manual"  # Operator-initiated
    WEBHOOK = "webhook"  # External webhook


class TaskType(str, Enum):
    """Types of tasks in workflows"""
    ACTION = "action"  # Execute action (API call, contract call, etc.)
    DECISION = "decision"  # Rule-based decision
    HUMAN_REVIEW = "human_review"  # Human-in-the-loop approval
    CONDITION = "condition"  # Conditional branching
    PARALLEL = "parallel"  # Parallel execution
    SUBWORKFLOW = "subworkflow"  # Execute another workflow


class Transition(BaseModel):
    """Workflow transition/edge"""
    condition: Optional[str] = None  # Expression to evaluate
    target_state_id: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkflowState(BaseModel):
    """A state in the workflow"""
    id: str
    type: TaskType
    name: str
    description: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)  # Task-specific configuration
    transitions: List[Transition] = Field(default_factory=list)
    timeout_seconds: Optional[int] = None
    retry_policy: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkflowSpecification(BaseModel):
    """Declarative workflow specification"""
    workflow_id: str
    name: str
    description: Optional[str] = None
    version: str = "1.0.0"
    states: List[WorkflowState]
    initial_state_id: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


class Trigger(BaseModel):
    """Workflow trigger configuration"""
    trigger_id: str
    trigger_type: TriggerType
    workflow_id: str
    config: Dict[str, Any] = Field(default_factory=dict)  # Trigger-specific config
    enabled: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkflowExecution(BaseModel):
    """Workflow execution instance"""
    execution_id: str
    workflow_id: str
    workflow_version: str
    status: WorkflowStatus
    correlation_id: Optional[str] = None  # For tracing related executions
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Dict[str, Any] = Field(default_factory=dict)
    current_state_id: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    triggered_by: str  # User ID, system, event name, etc.
    trigger_type: TriggerType
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskExecution(BaseModel):
    """Task execution instance"""
    task_id: str
    execution_id: str
    state_id: str
    status: TaskStatus
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Dict[str, Any] = Field(default_factory=dict)
    started_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class HumanReviewRequest(BaseModel):
    """Human-in-the-loop review request"""
    review_id: str
    execution_id: str
    task_id: str
    workflow_id: str
    requested_by: str
    requested_at: datetime
    due_at: Optional[datetime] = None
    status: str = "pending"  # pending, approved, rejected, expired
    evidence: Dict[str, Any] = Field(default_factory=dict)  # Data for human to review
    context: Dict[str, Any] = Field(default_factory=dict)
    approver: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    comment: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Rule(BaseModel):
    """Rule for decision engine"""
    rule_id: str
    name: str
    condition: str  # Expression to evaluate
    action: str  # Action or transition to take
    priority: int = 0  # Higher priority rules evaluated first
    enabled: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DecisionTable(BaseModel):
    """Decision table for rule-based decisions"""
    table_id: str
    name: str
    rules: List[Rule]
    default_action: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

