"""
Base class for all agents in the C.L.E.O. system
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from .message_bus import message_bus, AgentMessage

logger = logging.getLogger(__name__)


class BaseAgent:
    """Base class for all agents in the C.L.E.O. system"""
    
    def __init__(self, agent_id: str, agent_name: str):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.is_running = False
        self.message_queue = asyncio.Queue(maxsize=1000)
        self.subscriptions = set()
        self._start_time: Optional[datetime] = None
        logger.info(f"Initialized agent: {agent_name} ({agent_id})")
    
    async def start(self):
        """Start the agent's main loop"""
        self.is_running = True
        self._start_time = datetime.now()
        asyncio.create_task(self._message_processor())
        logger.info(f"Agent {self.agent_name} started")
    
    async def stop(self):
        """Stop the agent"""
        self.is_running = False
        logger.info(f"Agent {self.agent_name} stopped")
    
    async def send_message(self, message: AgentMessage):
        """Send message to another agent via message bus"""
        await message_bus.publish(message)
    
    async def receive_message(self, message: AgentMessage):
        """Receive message from message bus"""
        if message.receiver == self.agent_id or message.receiver == "broadcast":
            try:
                await self.message_queue.put(message)
            except asyncio.QueueFull:
                logger.warning(f"Message queue full for {self.agent_name}, dropping message")
    
    async def _message_processor(self):
        """Process incoming messages"""
        while self.is_running:
            try:
                # Use timeout to allow periodic checks
                message = await asyncio.wait_for(
                    self.message_queue.get(),
                    timeout=1.0
                )
                await self.handle_message(message)
                self.message_queue.task_done()
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Agent {self.agent_name} error processing message: {e}")
    
    async def handle_message(self, message: AgentMessage):
        """Handle incoming message - to be implemented by subclasses"""
        logger.warning(f"Agent {self.agent_name} received unhandled message: {message.message_type}")
    
    async def broadcast_event(self, event_type: str, payload: Dict[str, Any]):
        """Broadcast an event to all subscribed agents"""
        message = AgentMessage(
            message_id=f"event_{datetime.now().timestamp()}",
            sender=self.agent_id,
            receiver="broadcast",
            message_type=event_type,
            payload=payload
        )
        await self.send_message(message)

