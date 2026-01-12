"""
Workflow Triggers - Time-based, event-based, API, and webhook triggers
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import json

from .models import Trigger, TriggerType, WorkflowExecution
from .engine import WorkflowEngine

logger = logging.getLogger(__name__)


class TriggerManager:
    """
    Manages workflow triggers (scheduled, event-based, webhook, etc.)
    """
    
    def __init__(self, workflow_engine: WorkflowEngine):
        self.workflow_engine = workflow_engine
        self.triggers: Dict[str, Trigger] = {}
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.event_listeners: Dict[str, List[Callable]] = {}  # event_type -> listeners
        
    async def register_trigger(self, trigger: Trigger):
        """Register and activate a trigger"""
        self.triggers[trigger.trigger_id] = trigger
        
        if trigger.enabled:
            await self._activate_trigger(trigger)
        
        logger.info(f"Registered trigger: {trigger.trigger_id} ({trigger.trigger_type})")
    
    async def _activate_trigger(self, trigger: Trigger):
        """Activate a trigger based on its type"""
        if trigger.trigger_type == TriggerType.SCHEDULED:
            await self._activate_scheduled_trigger(trigger)
        elif trigger.trigger_type == TriggerType.EVENT:
            await self._activate_event_trigger(trigger)
        elif trigger.trigger_type == TriggerType.WEBHOOK:
            # Webhooks are handled via API endpoints
            pass
    
    async def _activate_scheduled_trigger(self, trigger: Trigger):
        """Activate a scheduled/cron trigger"""
        cron_expr = trigger.config.get("cron")
        interval_seconds = trigger.config.get("interval_seconds")
        
        async def scheduled_loop():
            try:
                while trigger.trigger_id in self.triggers and trigger.enabled:
                    if cron_expr:
                        # Parse cron expression and calculate next execution time
                        # Simplified: use interval if cron parsing not available
                        await asyncio.sleep(interval_seconds or 60)
                    elif interval_seconds:
                        await asyncio.sleep(interval_seconds)
                    else:
                        await asyncio.sleep(60)  # Default: every minute
                    
                    if trigger.enabled and trigger.trigger_id in self.triggers:
                        await self._fire_trigger(trigger, {"triggered_at": datetime.now().isoformat()})
            except asyncio.CancelledError:
                logger.info(f"Scheduled trigger {trigger.trigger_id} cancelled")
            except Exception as e:
                logger.error(f"Error in scheduled trigger {trigger.trigger_id}: {e}", exc_info=True)
        
        task = asyncio.create_task(scheduled_loop())
        self.active_tasks[trigger.trigger_id] = task
    
    async def _activate_event_trigger(self, trigger: Trigger):
        """Activate an event-based trigger"""
        event_type = trigger.config.get("event_type")
        
        async def event_handler(event_data: Dict[str, Any]):
            await self._fire_trigger(trigger, event_data)
        
        if event_type not in self.event_listeners:
            self.event_listeners[event_type] = []
        
        self.event_listeners[event_type].append(event_handler)
        logger.info(f"Registered event listener for {event_type} -> workflow {trigger.workflow_id}")
    
    async def fire_event(self, event_type: str, event_data: Dict[str, Any]):
        """Fire an event to trigger event-based workflows"""
        listeners = self.event_listeners.get(event_type, [])
        
        for listener in listeners:
            try:
                await listener(event_data)
            except Exception as e:
                logger.error(f"Error in event listener: {e}", exc_info=True)
    
    async def _fire_trigger(self, trigger: Trigger, input_data: Dict[str, Any]):
        """Fire a trigger to start a workflow"""
        try:
            execution = await self.workflow_engine.start_workflow(
                workflow_id=trigger.workflow_id,
                input_data=input_data,
                triggered_by=f"trigger:{trigger.trigger_id}",
                trigger_type=trigger.trigger_type.value
            )
            logger.info(f"Triggered workflow {trigger.workflow_id} via trigger {trigger.trigger_id}, execution: {execution.execution_id}")
        except Exception as e:
            logger.error(f"Error firing trigger {trigger.trigger_id}: {e}", exc_info=True)
    
    async def disable_trigger(self, trigger_id: str):
        """Disable a trigger"""
        if trigger_id in self.triggers:
            self.triggers[trigger_id].enabled = False
            
            # Cancel active task
            if trigger_id in self.active_tasks:
                self.active_tasks[trigger_id].cancel()
                del self.active_tasks[trigger_id]
            
            logger.info(f"Disabled trigger: {trigger_id}")
    
    async def enable_trigger(self, trigger_id: str):
        """Enable a trigger"""
        if trigger_id in self.triggers:
            trigger = self.triggers[trigger_id]
            trigger.enabled = True
            await self._activate_trigger(trigger)
            logger.info(f"Enabled trigger: {trigger_id}")
    
    async def remove_trigger(self, trigger_id: str):
        """Remove a trigger"""
        await self.disable_trigger(trigger_id)
        if trigger_id in self.triggers:
            del self.triggers[trigger_id]


class BlockchainEventTrigger:
    """
    Specialized trigger for blockchain events (e.g., Cronos contract events)
    Integrates with Web3 event monitoring
    """
    
    def __init__(self, trigger_manager: TriggerManager, w3_provider=None):
        self.trigger_manager = trigger_manager
        self.w3_provider = w3_provider
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}
    
    async def register_blockchain_trigger(
        self,
        trigger_id: str,
        workflow_id: str,
        contract_address: str,
        event_name: str,
        event_abi: List[Dict],
        filter_args: Optional[Dict[str, Any]] = None
    ):
        """Register a blockchain event trigger"""
        trigger = Trigger(
            trigger_id=trigger_id,
            trigger_type=TriggerType.EVENT,
            workflow_id=workflow_id,
            config={
                "event_type": "blockchain",
                "contract_address": contract_address,
                "event_name": event_name,
                "event_abi": event_abi,
                "filter_args": filter_args or {}
            }
        )
        
        await self.trigger_manager.register_trigger(trigger)
        
        # Start monitoring blockchain events
        if self.w3_provider:
            await self._start_event_monitoring(trigger)
    
    async def _start_event_monitoring(self, trigger: Trigger):
        """Start monitoring blockchain events"""
        config = trigger.config
        contract_address = config["contract_address"]
        event_name = config["event_name"]
        
        async def monitor_loop():
            try:
                # This would integrate with Web3 event filters
                # For now, placeholder implementation
                logger.info(f"Started monitoring blockchain events for trigger {trigger.trigger_id}")
                
                while trigger.enabled:
                    # In production, use Web3 event filters to monitor for events
                    # event_filter = contract.events.EventName.createFilter(fromBlock='latest')
                    # for event in event_filter.get_new_entries():
                    #     await self.trigger_manager.fire_event("blockchain", {"event": event})
                    
                    await asyncio.sleep(5)  # Polling interval
                    
            except asyncio.CancelledError:
                logger.info(f"Blockchain event monitoring cancelled for {trigger.trigger_id}")
            except Exception as e:
                logger.error(f"Error monitoring blockchain events: {e}", exc_info=True)
        
        task = asyncio.create_task(monitor_loop())
        self.monitoring_tasks[trigger.trigger_id] = task

