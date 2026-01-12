"""
Execution Agent - Orchestrates x402 atomic batch execution
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


class ExecutionAgent(BaseAgent):
    """Agent responsible for executing optimized routes via x402"""
    
    def __init__(self, x402_executor=None):
        super().__init__("execution_agent", "Execution Agent")
        self.x402_executor = x402_executor
        self._pending_executions: Dict[str, Dict] = {}
    
    async def handle_message(self, message: AgentMessage):
        """Handle incoming messages"""
        if message.message_type == "execute_route":
            route_data = message.payload.get("route")
            request_id = message.payload.get("request_id")
            
            # Convert route data to OptimizedRoute if needed
            route = OptimizedRoute(**route_data) if isinstance(route_data, dict) else route_data
            
            # Store pending execution
            self._pending_executions[request_id] = {
                "route": route,
                "original_message": message
            }
            
            # Execute route
            execution_result = await self.execute_route(route)
            
            response = AgentMessage(
                message_id=f"resp_{message.message_id}",
                sender=self.agent_id,
                receiver=message.sender,
                message_type="execution_result",
                payload={
                    "success": execution_result.success,
                    "tx_hash": execution_result.tx_hash,
                    "actual_amount_out": float(execution_result.actual_amount_out) if execution_result.actual_amount_out else None,
                    "actual_slippage": float(execution_result.actual_slippage) if execution_result.actual_slippage else None,
                    "gas_used": float(execution_result.gas_used) if execution_result.gas_used else None,
                    "block_number": execution_result.block_number,
                    "error_message": execution_result.error_message,
                    "request_id": request_id
                }
            )
            await self.send_message(response)
    
    async def execute_route(self, route: OptimizedRoute) -> ExecutionResult:
        """
        Execute optimized route via x402 facilitator
        
        Args:
            route: OptimizedRoute to execute
            
        Returns:
            ExecutionResult with execution details
        """
        if not self.x402_executor:
            return ExecutionResult(
                success=False,
                error_message="x402 executor not initialized"
            )
        
        try:
            # Convert route splits to x402 format
            routes = []
            for split in route.splits:
                routes.append({
                    "dexId": split.dex_name.lower().replace(" ", "_"),
                    "path": split.path,
                    "amountIn": int(float(split.amount_in) * 10**split.token_in.decimals),
                    "minAmountOut": int(float(split.min_amount_out) * 10**split.token_out.decimals)
                })
            
            # Execute via x402
            result = await self.x402_executor.execute_swap(
                routes=routes,
                total_amount_in=float(route.total_amount_in),
                token_in=route.token_in.symbol,
                token_out=route.token_out.symbol,
                min_total_out=float(route.total_min_out),
                max_slippage=float(route.predicted_slippage)
            )
            
            if result.get("success"):
                # Calculate actual slippage
                actual_amount_out = Decimal(result.get("total_received", 0)) / Decimal(10**route.token_out.decimals)
                actual_slippage = None
                if route.total_amount_in > 0 and actual_amount_out > 0:
                    # Simplified slippage calculation
                    expected_out = route.total_expected_out
                    if expected_out > 0:
                        actual_slippage = abs((actual_amount_out - expected_out) / expected_out)
                
                return ExecutionResult(
                    success=True,
                    tx_hash=result.get("tx_hash"),
                    actual_amount_out=actual_amount_out,
                    actual_slippage=actual_slippage,
                    gas_used=Decimal(result.get("gas_used", 0)),
                    block_number=result.get("block_number"),
                    timestamp=datetime.now()
                )
            else:
                return ExecutionResult(
                    success=False,
                    error_message=result.get("error", "Execution failed"),
                    timestamp=datetime.now()
                )
        
        except Exception as e:
            logger.error(f"Execution error: {e}")
            return ExecutionResult(
                success=False,
                error_message=str(e),
                timestamp=datetime.now()
            )
    
    async def simulate_execution(self, route: OptimizedRoute) -> Dict[str, Any]:
        """Simulate execution without actually sending transaction"""
        if not self.x402_executor:
            return {"error": "x402 executor not initialized"}
        
        try:
            routes = []
            for split in route.splits:
                routes.append({
                    "dexId": split.dex_name.lower().replace(" ", "_"),
                    "path": split.path,
                    "amountIn": int(float(split.amount_in) * 10**split.token_in.decimals),
                    "minAmountOut": int(float(split.min_amount_out) * 10**split.token_out.decimals)
                })
            
            result = await self.x402_executor.simulate_execution(
                routes=routes,
                total_amount_in=float(route.total_amount_in),
                token_in=route.token_in.symbol,
                token_out=route.token_out.symbol
            )
            
            return result
        
        except Exception as e:
            logger.error(f"Simulation error: {e}")
            return {"error": str(e)}
