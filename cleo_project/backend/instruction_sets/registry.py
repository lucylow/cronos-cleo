"""
Instruction Set Registry and Manager
Manages instruction sets: create, update, execute, monitor
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from web3 import Web3
import hashlib
import json

from .models import (
    InstructionSet, InstructionSetType, InstructionSetStatus,
    Condition, Action, Schedule, Limits
)
from .condition_evaluator import ConditionEvaluator


class InstructionSetRegistry:
    """Registry for managing instruction sets"""
    
    def __init__(
        self,
        w3: Web3,
        condition_evaluator: ConditionEvaluator,
        pipeline_executor=None,
        x402_executor=None
    ):
        self.w3 = w3
        self.condition_evaluator = condition_evaluator
        self.pipeline_executor = pipeline_executor
        self.x402_executor = x402_executor
        
        # In-memory storage (in production, use database)
        self.instruction_sets: Dict[str, InstructionSet] = {}
        self.execution_history: Dict[str, List[Dict[str, Any]]] = {}
    
    def create_instruction_set(
        self,
        owner: str,
        instruction_type: InstructionSetType,
        schedule: Schedule,
        conditions: List[Condition],
        actions: List[Action],
        limits: Limits,
        metadata: Optional[Dict[str, Any]] = None
    ) -> InstructionSet:
        """
        Create a new instruction set
        
        Args:
            owner: Owner/creator address
            instruction_type: Type of instruction set
            schedule: Schedule configuration
            conditions: List of conditions
            actions: List of actions
            limits: Safety limits
            metadata: Optional metadata
            
        Returns:
            Created InstructionSet
        """
        instruction_id = self._generate_instruction_id(owner)
        
        instruction_set = InstructionSet(
            instruction_id=instruction_id,
            owner=owner,
            instruction_type=instruction_type,
            status=InstructionSetStatus.ACTIVE,
            schedule=schedule,
            conditions=conditions,
            actions=actions,
            limits=limits,
            metadata=metadata or {}
        )
        
        self.instruction_sets[instruction_id] = instruction_set
        self.execution_history[instruction_id] = []
        
        return instruction_set
    
    def get_instruction_set(self, instruction_id: str) -> Optional[InstructionSet]:
        """Get instruction set by ID"""
        return self.instruction_sets.get(instruction_id)
    
    def get_user_instruction_sets(self, owner: str) -> List[InstructionSet]:
        """Get all instruction sets for a user"""
        return [
            inst for inst in self.instruction_sets.values()
            if inst.owner.lower() == owner.lower()
        ]
    
    def update_instruction_set(
        self,
        instruction_id: str,
        owner: str,
        schedule: Optional[Schedule] = None,
        conditions: Optional[List[Condition]] = None,
        actions: Optional[List[Action]] = None,
        limits: Optional[Limits] = None,
        status: Optional[InstructionSetStatus] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[InstructionSet]:
        """
        Update an instruction set (only owner can update)
        
        Returns:
            Updated InstructionSet or None if not found/unauthorized
        """
        instruction_set = self.instruction_sets.get(instruction_id)
        if not instruction_set:
            return None
        
        if instruction_set.owner.lower() != owner.lower():
            return None  # Unauthorized
        
        if schedule:
            instruction_set.schedule = schedule
        if conditions is not None:
            instruction_set.conditions = conditions
        if actions is not None:
            instruction_set.actions = actions
        if limits:
            instruction_set.limits = limits
        if status:
            instruction_set.status = status
        if metadata:
            instruction_set.metadata.update(metadata)
        
        instruction_set.updated_at = int(datetime.now().timestamp())
        return instruction_set
    
    def pause_instruction_set(self, instruction_id: str, owner: str) -> bool:
        """Pause an instruction set"""
        instruction_set = self.instruction_sets.get(instruction_id)
        if not instruction_set or instruction_set.owner.lower() != owner.lower():
            return False
        
        instruction_set.status = InstructionSetStatus.PAUSED
        instruction_set.updated_at = int(datetime.now().timestamp())
        return True
    
    def resume_instruction_set(self, instruction_id: str, owner: str) -> bool:
        """Resume a paused instruction set"""
        instruction_set = self.instruction_sets.get(instruction_id)
        if not instruction_set or instruction_set.owner.lower() != owner.lower():
            return False
        
        if instruction_set.status == InstructionSetStatus.PAUSED:
            instruction_set.status = InstructionSetStatus.ACTIVE
            instruction_set.updated_at = int(datetime.now().timestamp())
            return True
        return False
    
    def cancel_instruction_set(self, instruction_id: str, owner: str) -> bool:
        """Cancel an instruction set"""
        instruction_set = self.instruction_sets.get(instruction_id)
        if not instruction_set or instruction_set.owner.lower() != owner.lower():
            return False
        
        instruction_set.status = InstructionSetStatus.CANCELLED
        instruction_set.updated_at = int(datetime.now().timestamp())
        return True
    
    async def check_execution_due(self, instruction_id: str) -> bool:
        """
        Check if an instruction set is due for execution
        
        Returns:
            True if due and ready to execute
        """
        instruction_set = self.instruction_sets.get(instruction_id)
        if not instruction_set:
            return False
        
        # Check status
        if instruction_set.status != InstructionSetStatus.ACTIVE:
            return False
        
        # Check limits
        if instruction_set.limits.pause_switch or instruction_set.limits.circuit_breaker_active:
            return False
        
        # Check schedule
        current_timestamp = int(datetime.now().timestamp())
        if current_timestamp < instruction_set.schedule.next_execution:
            return False
        
        # Check max executions
        if instruction_set.schedule.max_executions:
            if instruction_set.schedule.execution_count >= instruction_set.schedule.max_executions:
                return False
        
        # Check end time
        if instruction_set.schedule.end_time:
            if current_timestamp > instruction_set.schedule.end_time:
                return False
        
        return True
    
    async def evaluate_conditions(self, instruction_id: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Evaluate all conditions for an instruction set
        
        Returns:
            True if all conditions pass
        """
        instruction_set = self.instruction_sets.get(instruction_id)
        if not instruction_set:
            return False
        
        return await self.condition_evaluator.evaluate_conditions(
            instruction_set.conditions,
            context
        )
    
    async def execute_instruction_set(
        self,
        instruction_id: str,
        private_key: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute an instruction set (if conditions are met)
        
        Args:
            instruction_id: Instruction set ID
            private_key: Private key for execution (if needed)
            context: Optional context for condition evaluation
            
        Returns:
            Execution result
        """
        instruction_set = self.instruction_sets.get(instruction_id)
        if not instruction_set:
            return {"success": False, "error": "Instruction set not found"}
        
        # Check if due
        if not await self.check_execution_due(instruction_id):
            return {"success": False, "error": "Instruction set not due for execution"}
        
        # Evaluate conditions
        conditions_passed = await self.evaluate_conditions(instruction_id, context)
        if not conditions_passed:
            return {"success": False, "error": "Conditions not met"}
        
        # Check limits
        if not self._check_limits(instruction_set):
            return {"success": False, "error": "Limits exceeded"}
        
        # Execute actions
        try:
            execution_result = await self._execute_actions(
                instruction_set,
                private_key,
                context
            )
            
            # Update instruction set state
            instruction_set.schedule.execution_count += 1
            instruction_set.schedule.next_execution = (
                int(datetime.now().timestamp()) + instruction_set.schedule.interval_seconds
            )
            instruction_set.last_execution = int(datetime.now().timestamp())
            instruction_set.last_execution_tx = execution_result.get("tx_hash")
            instruction_set.updated_at = int(datetime.now().timestamp())
            
            # Record execution history
            self.execution_history[instruction_id].append({
                "timestamp": instruction_set.last_execution,
                "tx_hash": instruction_set.last_execution_tx,
                "result": execution_result,
                "execution_count": instruction_set.schedule.execution_count
            })
            
            # Check if completed
            if instruction_set.schedule.max_executions:
                if instruction_set.schedule.execution_count >= instruction_set.schedule.max_executions:
                    instruction_set.status = InstructionSetStatus.COMPLETED
            
            return execution_result
            
        except Exception as e:
            # Record failure
            self.execution_history[instruction_id].append({
                "timestamp": int(datetime.now().timestamp()),
                "error": str(e),
                "execution_count": instruction_set.schedule.execution_count
            })
            return {"success": False, "error": str(e)}
    
    async def _execute_actions(
        self,
        instruction_set: InstructionSet,
        private_key: Optional[str],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Execute all actions in an instruction set
        
        Returns:
            Execution result
        """
        results = []
        total_gas = 0
        
        for action in instruction_set.actions:
            # Check per-action condition if present
            if action.condition:
                condition_passed = await self.condition_evaluator.evaluate_condition(
                    action.condition,
                    context
                )
                if not condition_passed:
                    if action.is_critical:
                        raise Exception(f"Critical action condition failed: {action.action_type}")
                    continue  # Skip non-critical action
            
            # Execute action based on type
            action_result = await self._execute_action(action, private_key, context)
            results.append(action_result)
            
            if action_result.get("gas_used"):
                total_gas += action_result["gas_used"]
            
            # Check gas limit
            if instruction_set.limits.max_gas_per_execution:
                if total_gas > instruction_set.limits.max_gas_per_execution:
                    raise Exception("Gas limit exceeded")
            
            # If critical action failed, abort
            if action.is_critical and not action_result.get("success"):
                raise Exception(f"Critical action failed: {action.action_type}")
        
        return {
            "success": True,
            "actions_executed": len(results),
            "total_gas": total_gas,
            "action_results": results,
            "tx_hash": results[-1].get("tx_hash") if results else None
        }
    
    async def _execute_action(
        self,
        action: Action,
        private_key: Optional[str],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Execute a single action
        
        Returns:
            Action execution result
        """
        # This is a simplified implementation
        # In production, would integrate with x402 executor, pipeline executor, etc.
        
        if action.action_type == ActionType.PIPELINE:
            # Execute via pipeline executor
            pipeline_id = action.parameters.get("pipeline_id")
            if self.pipeline_executor and pipeline_id:
                result = await self.pipeline_executor.execute_pipeline(pipeline_id, private_key)
                return result
        
        elif action.action_type in [ActionType.SWAP, ActionType.SWAP_MULTI_DEX]:
            # Execute via x402 executor
            if self.x402_executor:
                # Build swap parameters from action
                routes = action.parameters.get("routes", [])
                token_in = action.parameters.get("token_in")
                token_out = action.parameters.get("token_out")
                amount_in = action.parameters.get("amount_in")
                min_total_out = action.parameters.get("min_total_out")
                
                result = await self.x402_executor.execute_swap(
                    routes=routes,
                    total_amount_in=amount_in,
                    token_in=token_in,
                    token_out=token_out,
                    min_total_out=min_total_out
                )
                return result
        
        # Default: return mock result
        return {
            "success": True,
            "action_type": action.action_type.value,
            "target": action.target,
            "tx_hash": f"0x{'0' * 64}",
            "gas_used": 100000
        }
    
    def _check_limits(self, instruction_set: InstructionSet) -> bool:
        """Check if execution would violate limits"""
        limits = instruction_set.limits
        
        # Check pause switch
        if limits.pause_switch:
            return False
        
        # Check circuit breaker
        if limits.circuit_breaker_active:
            return False
        
        # Check cumulative cap
        if limits.cumulative_cap:
            if limits.cumulative_spent >= limits.cumulative_cap:
                return False
        
        return True
    
    def _generate_instruction_id(self, owner: str) -> str:
        """Generate unique instruction set ID"""
        timestamp = int(datetime.now().timestamp())
        data = f"{owner}{timestamp}{len(self.instruction_sets)}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def get_execution_history(self, instruction_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get execution history for an instruction set"""
        history = self.execution_history.get(instruction_id, [])
        return history[-limit:] if limit else history
    
    def get_all_active_instruction_sets(self) -> List[InstructionSet]:
        """Get all active instruction sets"""
        return [
            inst for inst in self.instruction_sets.values()
            if inst.status == InstructionSetStatus.ACTIVE
        ]
