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
        Execute split optimization using linear programming enhanced with AI predictions
        
        Args:
            request: Dict with 'liquidity_data', 'total_amount', 'slippage_tolerance', optional 'ai_predictions'
            
        Returns:
            Dict with optimized routes, predicted slippage, and confidence
        """
        liquidity_data = request.get("liquidity_data", {})
        pools = liquidity_data.get("pools", [])
        total_amount = request.get("total_amount", 0)
        slippage_tolerance = request.get("slippage_tolerance", 0.005)
        input_token = request.get("input_token", "")
        output_token = request.get("output_token", "")
        ai_predictions = request.get("ai_predictions", {})
        
        if not pools or total_amount <= 0:
            return {
                "routes": [],
                "predicted_slippage": 0.0,
                "predicted_total_out": 0,
                "optimization_method": "linear_programming",
                "confidence": 0.0
            }
        
        # Extract AI predictions if available
        ai_predicted_slippage = None
        ai_success_prob = None
        ai_confidence = 0.0
        
        if ai_predictions:
            ai_predicted_slippage = ai_predictions.get("predicted_slippage")
            ai_success_prob = ai_predictions.get("success_probability")
            recommendation = ai_predictions.get("recommendation", {})
            ai_confidence = 0.85  # AI-enhanced confidence
        
        # Linear programming setup: minimize total slippage
        n_dexes = len(pools)
        
        # Objective function: minimize weighted slippage
        # Enhanced with AI predictions if available
        cost_factors = []
        for i, p in enumerate(pools):
            base_cost = p.get("impact_50k", 1.0)
            
            # Adjust cost based on AI predictions if available
            if ai_predicted_slippage is not None and ai_success_prob is not None:
                # Penalize pools that would contribute to higher predicted slippage
                pool_impact = p.get("impact_50k", 0.0)
                if pool_impact > ai_predicted_slippage:
                    base_cost *= 1.2  # Penalize high-impact pools
            
            # Adjust based on success probability
            if ai_success_prob is not None and ai_success_prob < 0.7:
                # If success probability is low, prefer safer pools
                base_cost *= (1 + (0.7 - ai_success_prob))
            
            cost_factors.append(base_cost)
        
        c = np.array(cost_factors)
        
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
        if ai_predicted_slippage is not None:
            # Use AI prediction if available, weighted with calculated slippage
            calculated_slippage = 0.0
            if total_amount > 0 and predicted_total_out > 0:
                ideal_output = (total_amount * pools[0].get("reserve_out", 1)) / max(pools[0].get("reserve_in", 1), 1)
                calculated_slippage = abs((ideal_output - predicted_total_out) / ideal_output) * 100
            
            # Weighted average: 70% AI prediction, 30% calculated
            predicted_slippage = (ai_predicted_slippage * 0.7) + (calculated_slippage * 0.3)
        elif total_amount > 0 and predicted_total_out > 0:
            # Fallback to calculated slippage
            ideal_output = (total_amount * pools[0].get("reserve_out", 1)) / max(pools[0].get("reserve_in", 1), 1)
            predicted_slippage = abs((ideal_output - predicted_total_out) / ideal_output) * 100
        else:
            predicted_slippage = 0.0
        
        # Calculate confidence score
        if ai_predictions:
            confidence = max(ai_confidence, 0.85)  # Enhanced confidence with AI
        else:
            confidence = 0.75  # Base confidence without AI
        
        # Adjust confidence based on number of routes and success probability
        if ai_success_prob is not None:
            confidence = (confidence + ai_success_prob) / 2
        
        result = {
            "routes": routes,
            "predicted_slippage": predicted_slippage,
            "predicted_total_out": predicted_total_out,
            "optimization_method": "ai_enhanced_linear_programming" if ai_predictions else "linear_programming",
            "confidence": min(confidence, 0.98)  # Cap at 98%
        }
        
        # Add AI insights if available
        if ai_predictions:
            result["ai_enhanced"] = True
            result["ai_predicted_slippage"] = ai_predicted_slippage
            result["ai_success_probability"] = ai_success_prob
        
        return result
    
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
