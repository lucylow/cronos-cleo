"""
Orchestrator Agent - Coordinates all agents in the multi-agent system
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from decimal import Decimal

from .base_agent import BaseAgent
from .message_bus import AgentMessage
from .models import OptimizedRoute, ExecutionResult

logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    """Main orchestrator that coordinates all agents"""
    
    def __init__(self):
        super().__init__("orchestrator", "Orchestrator")
        self._active_requests: Dict[str, Dict] = {}
    
    async def handle_message(self, message: AgentMessage):
        """Handle incoming messages"""
        if message.message_type == "optimize_and_execute":
            # Full pipeline: optimize -> validate -> execute
            await self._handle_optimize_and_execute(message)
    
    async def _handle_optimize_and_execute(self, message: AgentMessage):
        """Handle full optimization and execution pipeline"""
        request_id = message.payload.get("request_id", f"req_{datetime.now().timestamp()}")
        token_in = message.payload.get("token_in")
        token_out = message.payload.get("token_out")
        amount_in = Decimal(str(message.payload.get("amount_in", 0)))
        max_slippage = Decimal(str(message.payload.get("max_slippage", 0.005)))
        
        self._active_requests[request_id] = {
            "original_message": message,
            "status": "optimizing",
            "start_time": datetime.now()
        }
        
        try:
            # Step 1: Request route optimization
            optimize_msg = AgentMessage(
                message_id=f"opt_{request_id}",
                sender=self.agent_id,
                receiver="route_optimizer",
                message_type="optimize_route",
                payload={
                    "token_in": token_in,
                    "token_out": token_out,
                    "amount_in": float(amount_in),
                    "max_slippage": float(max_slippage),
                    "strategy": "ai_optimized",
                    "request_id": request_id
                }
            )
            await self.send_message(optimize_msg)
            
        except Exception as e:
            logger.error(f"Orchestration error: {e}")
            # Send error response
            response = AgentMessage(
                message_id=f"resp_{message.message_id}",
                sender=self.agent_id,
                receiver=message.sender,
                message_type="execution_result",
                payload={
                    "success": False,
                    "error_message": str(e),
                    "request_id": request_id
                }
            )
            await self.send_message(response)
