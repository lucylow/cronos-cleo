"""
Workflow Execution Engine - Core orchestration engine
"""
import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from enum import Enum

from .models import (
    WorkflowSpecification, WorkflowExecution, TaskExecution,
    WorkflowStatus, TaskStatus, TaskType, Transition, WorkflowState
)

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """
    Central workflow orchestration engine.
    Executes workflows according to specifications with state management, retries, and error handling.
    """
    
    def __init__(self, storage: Optional[Any] = None):
        """
        Initialize workflow engine
        
        Args:
            storage: Optional storage backend for persistence (WorkflowStorage)
        """
        self.storage = storage
        self.workflow_specs: Dict[str, WorkflowSpecification] = {}
        self.active_executions: Dict[str, WorkflowExecution] = {}
        self.task_executors: Dict[TaskType, Callable] = {}
        self.metrics_collector = None  # Will be set by observability module
        
        # Register default task executors
        self._register_default_executors()
    
    def _register_default_executors(self):
        """Register default task executors"""
        self.task_executors[TaskType.ACTION] = self._execute_action_task
        self.task_executors[TaskType.DECISION] = self._execute_decision_task
        self.task_executors[TaskType.CONDITION] = self._execute_condition_task
    
    async def register_workflow(self, spec: WorkflowSpecification):
        """Register a workflow specification"""
        self.workflow_specs[spec.workflow_id] = spec
        logger.info(f"Registered workflow: {spec.workflow_id} v{spec.version}")
    
    async def start_workflow(
        self,
        workflow_id: str,
        input_data: Dict[str, Any],
        triggered_by: str = "system",
        trigger_type: str = "api",
        correlation_id: Optional[str] = None
    ) -> WorkflowExecution:
        """
        Start a workflow execution
        
        Args:
            workflow_id: ID of workflow to execute
            input_data: Input data for workflow
            triggered_by: Who/what triggered this workflow
            trigger_type: Type of trigger
            correlation_id: Optional correlation ID for tracing
        
        Returns:
            WorkflowExecution instance
        """
        if workflow_id not in self.workflow_specs:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        spec = self.workflow_specs[workflow_id]
        execution_id = f"exec_{uuid.uuid4().hex[:16]}"
        
        execution = WorkflowExecution(
            execution_id=execution_id,
            workflow_id=workflow_id,
            workflow_version=spec.version,
            status=WorkflowStatus.PENDING,
            correlation_id=correlation_id or execution_id,
            input_data=input_data,
            current_state_id=spec.initial_state_id,
            started_at=datetime.now(),
            triggered_by=triggered_by,
            trigger_type=trigger_type
        )
        
        self.active_executions[execution_id] = execution
        
        if self.storage:
            await self.storage.save_execution(execution)
        
        # Start execution asynchronously
        asyncio.create_task(self._execute_workflow(execution_id))
        
        logger.info(f"Started workflow execution: {execution_id} for workflow {workflow_id}")
        return execution
    
    async def _execute_workflow(self, execution_id: str):
        """Execute workflow (internal async task)"""
        execution = self.active_executions.get(execution_id)
        if not execution:
            logger.error(f"Execution {execution_id} not found")
            return
        
        try:
            execution.status = WorkflowStatus.RUNNING
            spec = self.workflow_specs[execution.workflow_id]
            
            while execution.status == WorkflowStatus.RUNNING:
                current_state = self._get_state(spec, execution.current_state_id)
                if not current_state:
                    execution.status = WorkflowStatus.FAILED
                    execution.error = f"State {execution.current_state_id} not found"
                    break
                
                # Execute current state/task
                next_state_id = await self._execute_state(execution, current_state)
                
                if next_state_id is None:
                    # Workflow completed
                    execution.status = WorkflowStatus.COMPLETED
                    execution.completed_at = datetime.now()
                    break
                
                execution.current_state_id = next_state_id
            
        except Exception as e:
            logger.error(f"Workflow execution error: {e}", exc_info=True)
            execution.status = WorkflowStatus.FAILED
            execution.error = str(e)
            execution.completed_at = datetime.now()
        finally:
            if self.storage:
                await self.storage.save_execution(execution)
            
            # Record metrics
            if self.metrics_collector:
                duration = (execution.completed_at or datetime.now()) - execution.started_at
                self.metrics_collector.record_workflow_execution(
                    execution.workflow_id,
                    execution.status,
                    duration.total_seconds()
                )
    
    async def _execute_state(
        self,
        execution: WorkflowExecution,
        state: WorkflowState
    ) -> Optional[str]:
        """
        Execute a workflow state and return next state ID
        
        Returns:
            Next state ID, or None if workflow should complete
        """
        task_id = f"{execution.execution_id}_{state.id}"
        
        task_execution = TaskExecution(
            task_id=task_id,
            execution_id=execution.execution_id,
            state_id=state.id,
            status=TaskStatus.RUNNING,
            input_data=execution.input_data,
            started_at=datetime.now()
        )
        
        try:
            # Get executor for this task type
            executor = self.task_executors.get(state.type)
            if not executor:
                raise ValueError(f"No executor for task type: {state.type}")
            
            # Execute task with retry logic
            output_data = await self._execute_with_retry(
                executor,
                execution,
                state,
                task_execution
            )
            
            task_execution.status = TaskStatus.COMPLETED
            task_execution.output_data = output_data or {}
            task_execution.completed_at = datetime.now()
            
            # Update execution output data
            execution.output_data.update(output_data or {})
            
            # Determine next state
            next_state_id = self._evaluate_transitions(
                execution,
                state,
                output_data
            )
            
            return next_state_id
            
        except Exception as e:
            logger.error(f"Task execution error in state {state.id}: {e}", exc_info=True)
            task_execution.status = TaskStatus.FAILED
            task_execution.error = str(e)
            task_execution.completed_at = datetime.now()
            
            # Check if state is critical (fail entire workflow)
            if state.config.get("is_critical", True):
                execution.status = WorkflowStatus.FAILED
                execution.error = f"Critical task {state.id} failed: {str(e)}"
                return None
            
            # Try to find error transition
            for transition in state.transitions:
                if transition.condition == "on_error":
                    return transition.target_state_id
            
            # No error handler, fail workflow
            execution.status = WorkflowStatus.FAILED
            execution.error = f"Task {state.id} failed with no error handler"
            return None
        
        finally:
            if self.storage:
                await self.storage.save_task_execution(task_execution)
    
    async def _execute_with_retry(
        self,
        executor: Callable,
        execution: WorkflowExecution,
        state: WorkflowState,
        task_execution: TaskExecution
    ) -> Dict[str, Any]:
        """Execute task with retry policy"""
        retry_policy = state.retry_policy or {"max_retries": 0, "backoff_seconds": 1}
        max_retries = retry_policy.get("max_retries", 0)
        backoff_seconds = retry_policy.get("backoff_seconds", 1)
        
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                return await executor(execution, state, task_execution)
            except Exception as e:
                last_error = e
                task_execution.retry_count = attempt + 1
                
                if attempt < max_retries:
                    wait_time = backoff_seconds * (2 ** attempt)  # Exponential backoff
                    logger.warning(
                        f"Task {state.id} failed (attempt {attempt + 1}/{max_retries + 1}), "
                        f"retrying in {wait_time}s: {e}"
                    )
                    task_execution.status = TaskStatus.WAITING_RETRY
                    await asyncio.sleep(wait_time)
                else:
                    raise last_error
        
        raise last_error
    
    async def _execute_action_task(
        self,
        execution: WorkflowExecution,
        state: WorkflowState,
        task_execution: TaskExecution
    ) -> Dict[str, Any]:
        """Execute an action task"""
        action_type = state.config.get("action_type")
        action_config = state.config.get("action_config", {})
        
        # This would delegate to action executors
        # For now, return empty output
        logger.info(f"Executing action task: {state.id}, type: {action_type}")
        
        return {"result": "completed", "state_id": state.id}
    
    async def _execute_decision_task(
        self,
        execution: WorkflowExecution,
        state: WorkflowState,
        task_execution: TaskExecution
    ) -> Dict[str, Any]:
        """Execute a decision task using rules engine"""
        # This would use the rules engine to evaluate conditions
        # For now, evaluate first matching transition
        logger.info(f"Executing decision task: {state.id}")
        
        return {"decision": "next"}
    
    async def _execute_condition_task(
        self,
        execution: WorkflowExecution,
        state: WorkflowState,
        task_execution: TaskExecution
    ) -> Dict[str, Any]:
        """Execute a condition task (evaluate transitions)"""
        logger.info(f"Executing condition task: {state.id}")
        return {}
    
    def _evaluate_transitions(
        self,
        execution: WorkflowExecution,
        state: WorkflowState,
        output_data: Dict[str, Any]
    ) -> Optional[str]:
        """Evaluate transitions to determine next state"""
        if not state.transitions:
            return None  # End of workflow
        
        # Evaluate transitions in order
        for transition in state.transitions:
            if transition.condition is None or transition.condition == "true":
                return transition.target_state_id
            
            # Evaluate condition expression (simplified - would use expression engine)
            # In production, use a proper expression evaluator
            try:
                # Simple condition evaluation (would be enhanced with expression engine)
                if self._evaluate_condition(transition.condition, execution, output_data):
                    return transition.target_state_id
            except Exception as e:
                logger.warning(f"Error evaluating condition {transition.condition}: {e}")
        
        # No transition matched - workflow ends
        return None
    
    def _evaluate_condition(
        self,
        condition: str,
        execution: WorkflowExecution,
        output_data: Dict[str, Any]
    ) -> bool:
        """Evaluate a condition expression (simplified implementation)"""
        # In production, use a proper expression engine (e.g., simpleeval, jsonpath-rw)
        # For now, simple string matching
        if condition == "true":
            return True
        if condition == "false":
            return False
        
        # Simple variable substitution (enhance with proper expression engine)
        context = {
            "input": execution.input_data,
            "output": output_data,
            "execution": execution.dict()
        }
        
        # Placeholder - would use expression evaluator
        return True
    
    def _get_state(self, spec: WorkflowSpecification, state_id: str) -> Optional[WorkflowState]:
        """Get state by ID from specification"""
        for state in spec.states:
            if state.id == state_id:
                return state
        return None
    
    async def get_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Get workflow execution by ID"""
        if execution_id in self.active_executions:
            return self.active_executions[execution_id]
        
        if self.storage:
            return await self.storage.get_execution(execution_id)
        
        return None
    
    async def cancel_execution(self, execution_id: str, reason: str = "User cancelled"):
        """Cancel a running workflow execution"""
        execution = await self.get_execution(execution_id)
        if execution:
            execution.status = WorkflowStatus.CANCELLED
            execution.error = reason
            execution.completed_at = datetime.now()
            
            if self.storage:
                await self.storage.save_execution(execution)
    
    def register_task_executor(self, task_type: TaskType, executor: Callable):
        """Register a custom task executor"""
        self.task_executors[task_type] = executor
        logger.info(f"Registered executor for task type: {task_type}")

