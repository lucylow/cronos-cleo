"""
Performance Monitor Agent - Tracks system performance
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from decimal import Decimal

from .base_agent import BaseAgent
from .message_bus import AgentMessage

logger = logging.getLogger(__name__)


class PerformanceMonitorAgent(BaseAgent):
    """Agent responsible for monitoring system performance"""
    
    def __init__(self):
        super().__init__("performance_monitor", "Performance Monitor")
        self.metrics = {
            "total_swaps": 0,
            "successful_swaps": 0,
            "failed_swaps": 0,
            "total_volume": Decimal('0'),
            "average_slippage": Decimal('0'),
            "total_gas_used": Decimal('0'),
            "execution_times": []
        }
        self.recent_swaps: List[Dict[str, Any]] = []
    
    async def handle_message(self, message: AgentMessage):
        """Handle incoming messages"""
        if message.message_type == "swap_completed":
            await self._record_swap(message.payload)
        
        elif message.message_type == "get_performance_metrics":
            response = AgentMessage(
                message_id=f"resp_{message.message_id}",
                sender=self.agent_id,
                receiver=message.sender,
                message_type="performance_metrics",
                payload={
                    "metrics": self.metrics,
                    "recent_swaps": self.recent_swaps[-10:]  # Last 10 swaps
                }
            )
            await self.send_message(response)
    
    async def _record_swap(self, payload: Dict[str, Any]):
        """Record swap performance metrics"""
        self.metrics["total_swaps"] += 1
        
        if payload.get("success"):
            self.metrics["successful_swaps"] += 1
        else:
            self.metrics["failed_swaps"] += 1
        
        # Update average slippage
        actual_slippage = payload.get("actual_slippage")
        if actual_slippage is not None:
            slippage = Decimal(str(actual_slippage))
            total = self.metrics["successful_swaps"]
            current_avg = self.metrics["average_slippage"]
            self.metrics["average_slippage"] = (current_avg * (total - 1) + slippage) / total
        
        # Record gas usage
        gas_used = payload.get("gas_used")
        if gas_used:
            self.metrics["total_gas_used"] += Decimal(str(gas_used))
        
        # Store recent swap
        self.recent_swaps.append({
            "request_id": payload.get("request_id"),
            "success": payload.get("success"),
            "slippage": actual_slippage,
            "gas_used": gas_used,
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep only last 100 swaps
        if len(self.recent_swaps) > 100:
            self.recent_swaps = self.recent_swaps[-100:]

