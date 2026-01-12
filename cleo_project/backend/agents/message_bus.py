"""
Message bus for inter-agent communication
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AgentMessage(BaseModel):
    """Message format for inter-agent communication"""
    message_id: str
    sender: str
    receiver: str
    message_type: str
    payload: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)
    priority: int = 1  # 1=Low, 5=Critical


class MessageBus:
    """Message bus for inter-agent communication"""
    
    def __init__(self):
        self.agents: Dict[str, Any] = {}  # Will hold BaseAgent instances
        self.channels: Dict[str, List[str]] = {}  # channel -> list of agent IDs
        logger.info("Message bus initialized")
    
    def register_agent(self, agent):
        """Register an agent with the message bus"""
        self.agents[agent.agent_id] = agent
        logger.info(f"Registered agent {agent.agent_name} ({agent.agent_id}) to message bus")
    
    async def publish(self, message: AgentMessage):
        """Publish a message to the bus"""
        if message.receiver == "broadcast":
            # Send to all agents
            for agent_id, agent in self.agents.items():
                if agent_id != message.sender:  # Don't send to self
                    try:
                        await agent.receive_message(message)
                    except Exception as e:
                        logger.error(f"Error sending message to {agent_id}: {e}")
        elif message.receiver in self.agents:
            # Send to specific agent
            try:
                await self.agents[message.receiver].receive_message(message)
            except Exception as e:
                logger.error(f"Error sending message to {message.receiver}: {e}")
        
        # Log high priority messages
        if message.priority >= 4:
            logger.info(f"High priority message: {message.message_type} from {message.sender} to {message.receiver}")
    
    def subscribe(self, agent_id: str, channel: str):
        """Subscribe an agent to a channel"""
        if channel not in self.channels:
            self.channels[channel] = []
        if agent_id not in self.channels[channel]:
            self.channels[channel].append(agent_id)
            logger.info(f"Agent {agent_id} subscribed to channel {channel}")
    
    def unsubscribe(self, agent_id: str, channel: str):
        """Unsubscribe an agent from a channel"""
        if channel in self.channels and agent_id in self.channels[channel]:
            self.channels[channel].remove(agent_id)
            logger.info(f"Agent {agent_id} unsubscribed from channel {channel}")


# Global message bus instance
message_bus = MessageBus()

