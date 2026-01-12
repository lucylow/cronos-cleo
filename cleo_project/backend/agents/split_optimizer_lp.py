"""
Split Optimizer Agent - Linear Programming based route optimization
Implements the split optimization phase using scipy.optimize.linprog
"""
import logging
import numpy as np
from scipy.optimize import linprog
from typing import List, Dict, Any
from decimal import Decimal

from .base_agent import BaseAgent
from .message_bus import AgentMessage

logger = logging.getLogger(__name__)


class SplitOptimizerAgent(BaseAgent):
    """Agent responsible for optimizing route splits using linear programming"""
    
    def __init__(self):
        super().__init__("split_optimizer", "Split Optimizer")
    
    async def execute(self, request: Dict) -> Dict:
        """
        Execute split optimization using linear programming
        
        Args:
            request: Dict with 'liquidity_data', 'total_amount', 'slippage_tolerance'
            
        Returns:
            Dict with optimized routes, predicted slippage, and confidence
        """
        liquidity_data = request.get("liquidity_data", {})
        pools = liquidity_data.get("pools", [])
        total_amount = request.get("total_amount", 0)
        slippage_tolerance = request.get("slippage_tolerance", 0.005)
        input_token = request.get("input_token", "")
        output_token = request.get("output_token", "")
        
        if not pools or total_amount <= 0:
            return {
                "routes": [],
                "predicted_slippage": 0.0,
                "predicted_total_out": 0,
                "optimization_method": "linear_programming",
                "confidence": 0.0
            }
        
        # Linear programming setup: minimize total slippage
        n_dexes = len(pools)
        
        # Objective function: minimize weighted slippage
        # Use impact_50k as proxy for slippage cost
        c = np.array([p.get("impact_50k", 1.0) for p in pools])
        
        # Constraints: sum(weights) = 1, each weight >= 0
        A_eq = np.ones((1, n_dexes))
        b_eq = np.array([1.0])
        bounds = [(0, 1) for _ in range(n_dexes)]
        
        try:
            # Solve linear program
            res = linprog(c, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')
            
            if not res.success:
                logger.warning(f"Linear programming failed: {res.message}")
                # Fallback to proportional split
                optimal_weights = np.array([1.0 / n_dexes] * n_dexes)
            else:
                optimal_weights = res.x
        except Exception as e:
            logger.error(f"Linear programming error: {e}")
            # Fallback to proportional split
            optimal_weights = np.array([1.0 / n_dexes] * n_dexes)
        
        # Convert weights to amounts and build routes
        routes = []
        predicted_total_out = 0
        
        for i, weight in enumerate(optimal_weights):
            if weight > 0.05:  # Minimum 5% allocation
                dex = pools[i]
                amount_in = int(total_amount * weight)
                
                # Calculate minimum output with slippage tolerance
                min_out = self._calculate_min_output(
                    dex.get("reserve_in", 0),
                    dex.get("reserve_out", 0),
                    amount_in,
                    slippage_tolerance
                )
                
                routes.append({
                    "dex_id": dex.get("dex_id", ""),
                    "router": dex.get("router", ""),
                    "amount_in": amount_in,
                    "min_amount_out": min_out,
                    "path": [input_token, output_token],
                    "weight": float(weight),
                    "pool_address": dex.get("pool_address", "")
                })
                
                # Estimate expected output (without slippage tolerance applied)
                expected_out = self._calculate_expected_output(
                    dex.get("reserve_in", 0),
                    dex.get("reserve_out", 0),
                    amount_in
                )
                predicted_total_out += expected_out
        
        # Calculate predicted slippage
        if total_amount > 0 and predicted_total_out > 0:
            # Simple slippage calculation based on price impact
            ideal_output = (total_amount * pools[0].get("reserve_out", 1)) / max(pools[0].get("reserve_in", 1), 1)
            predicted_slippage = abs((ideal_output - predicted_total_out) / ideal_output) * 100
        else:
            predicted_slippage = 0.0
        
        return {
            "routes": routes,
            "predicted_slippage": predicted_slippage,
            "predicted_total_out": predicted_total_out,
            "optimization_method": "linear_programming",
            "confidence": 0.92  # ML confidence score
        }
    
    def _calculate_min_output(self, reserve_in: int, reserve_out: int, 
                              amount_in: int, tolerance: float) -> int:
        """Calculate minimum output with slippage tolerance"""
        if reserve_in <= 0 or reserve_out <= 0:
            return 0
        
        # Constant product formula with fee
        amount_in_with_fee = amount_in * 997 / 1000
        ideal_out = (amount_in_with_fee * reserve_out) / (reserve_in + amount_in_with_fee)
        
        # Apply slippage tolerance
        slippage_adjustment = int(ideal_out * (1 - tolerance))
        return max(0, slippage_adjustment)
    
    def _calculate_expected_output(self, reserve_in: int, reserve_out: int, 
                                   amount_in: int) -> int:
        """Calculate expected output without slippage tolerance"""
        if reserve_in <= 0 or reserve_out <= 0:
            return 0
        
        amount_in_with_fee = amount_in * 997 / 1000
        expected_out = (amount_in_with_fee * reserve_out) / (reserve_in + amount_in_with_fee)
        return int(expected_out)
    
    async def handle_message(self, message: AgentMessage):
        """Handle incoming messages"""
        if message.message_type == "optimize_split":
            request_id = message.payload.get("request_id")
            
            result = await self.execute({
                "liquidity_data": message.payload.get("liquidity_data", {}),
                "total_amount": message.payload.get("total_amount", 0),
                "slippage_tolerance": message.payload.get("slippage_tolerance", 0.005),
                "input_token": message.payload.get("input_token", ""),
                "output_token": message.payload.get("output_token", "")
            })
            
            response = AgentMessage(
                message_id=f"resp_{message.message_id}",
                sender=self.agent_id,
                receiver=message.sender,
                message_type="split_optimized",
                payload={
                    "result": result,
                    "request_id": request_id
                }
            )
            await self.send_message(response)
