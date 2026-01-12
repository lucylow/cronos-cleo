"""
Risk Validator Agent - Pre-execution risk checks and validation
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from decimal import Decimal

from .base_agent import BaseAgent
from .message_bus import AgentMessage
from .models import OptimizedRoute, RouteSplit

logger = logging.getLogger(__name__)


class RiskValidatorAgent(BaseAgent):
    """Agent responsible for pre-execution risk validation"""
    
    def __init__(self):
        super().__init__("risk_validator", "Risk Validator")
        self.risk_thresholds = {
            "max_position_size_bps": 1500,  # 15% of pool depth
            "volatility_threshold": 5.0,  # 5% 1h volatility
            "max_slippage_bps": 200,  # 2% max slippage
            "min_liquidity_usd": 1000,  # Minimum pool liquidity
            "max_pool_impact": 10  # 10% max impact on pool
        }
        self._pending_validations: Dict[str, Dict] = {}
    
    async def handle_message(self, message: AgentMessage):
        """Handle incoming messages"""
        if message.message_type == "validate_route":
            route_data = message.payload.get("route")
            request_id = message.payload.get("request_id")
            
            # Convert route data to OptimizedRoute if needed
            route = OptimizedRoute(**route_data) if isinstance(route_data, dict) else route_data
            
            # Perform risk validation
            validation_result = await self.validate_route(route)
            
            response = AgentMessage(
                message_id=f"resp_{message.message_id}",
                sender=self.agent_id,
                receiver=message.sender,
                message_type="route_validation",
                payload={
                    "approved": validation_result["approved"],
                    "confidence": validation_result["confidence"],
                    "risk_score": validation_result["risk_score"],
                    "warnings": validation_result["warnings"],
                    "gas_estimate": validation_result["gas_estimate"],
                    "request_id": request_id
                }
            )
            await self.send_message(response)
    
    async def validate_route(self, route: OptimizedRoute) -> Dict[str, Any]:
        """
        Validate route against risk parameters
        
        Returns:
            {
                "approved": bool,
                "confidence": float (0-1),
                "risk_score": float (0-1, higher = riskier),
                "warnings": List[str],
                "gas_estimate": int
            }
        """
        warnings = []
        risk_factors = []
        approved = True
        
        # 1. Position Size Check
        for split in route.splits:
            # Check if amount exceeds max position size
            # This would require pool depth data - for now, use heuristic
            pool_impact = self._estimate_pool_impact(split)
            if pool_impact > self.risk_thresholds["max_pool_impact"]:
                warnings.append(f"Pool impact {pool_impact:.2f}% exceeds threshold for {split.dex_name}")
                risk_factors.append(0.3)
                if pool_impact > self.risk_thresholds["max_pool_impact"] * 1.5:
                    approved = False
        
        # 2. Slippage Check
        if route.predicted_slippage > Decimal(self.risk_thresholds["max_slippage_bps"] / 10000):
            warnings.append(f"Predicted slippage {route.predicted_slippage*100:.2f}% exceeds threshold")
            risk_factors.append(0.4)
            if route.predicted_slippage > Decimal(self.risk_thresholds["max_slippage_bps"] * 1.5 / 10000):
                approved = False
        
        # 3. Volatility Check (would query oracle in production)
        volatility = await self._get_volatility(route.token_in.symbol, route.token_out.symbol)
        if volatility > self.risk_thresholds["volatility_threshold"]:
            warnings.append(f"High volatility detected: {volatility:.2f}%")
            risk_factors.append(0.2)
            if volatility > self.risk_thresholds["volatility_threshold"] * 1.5:
                approved = False
        
        # 4. Liquidity Stress Test
        stress_test_result = await self._liquidity_stress_test(route)
        if not stress_test_result["pass"]:
            warnings.append(f"Liquidity stress test failed: {stress_test_result['reason']}")
            risk_factors.append(0.5)
            approved = False
        
        # 5. Gas Estimation
        gas_estimate = self._estimate_gas(route)
        if gas_estimate > 500000:  # High gas threshold
            warnings.append(f"High gas estimate: {gas_estimate}")
            risk_factors.append(0.1)
        
        # Calculate risk score (0-1, higher = riskier)
        risk_score = sum(risk_factors) / len(risk_factors) if risk_factors else 0.0
        risk_score = min(risk_score, 1.0)
        
        # Calculate confidence (inverse of risk score, with base confidence)
        confidence = max(0.5, 1.0 - risk_score * 0.5)
        
        return {
            "approved": approved,
            "confidence": confidence,
            "risk_score": risk_score,
            "warnings": warnings,
            "gas_estimate": gas_estimate,
            "volatility": volatility
        }
    
    def _estimate_pool_impact(self, split: RouteSplit) -> float:
        """Estimate impact on pool (percentage)"""
        # Simplified: assume impact scales with amount
        # In production, would query actual pool reserves
        if split.amount_in <= 0:
            return 0.0
        
        # Heuristic: impact = (amount / estimated_liquidity) * 100
        # For demo, assume liquidity is 10x the amount for small trades
        estimated_liquidity = float(split.amount_in) * 10
        if estimated_liquidity <= 0:
            return 100.0  # No liquidity = 100% impact
        
        impact = (float(split.amount_in) / estimated_liquidity) * 100
        return min(impact, 100.0)
    
    async def _get_volatility(self, token_in: str, token_out: str) -> float:
        """Get volatility for token pair (would query oracle in production)"""
        # Placeholder: return mock volatility
        # In production, would query price oracle for 1h volatility
        return 2.5  # 2.5% default
    
    async def _liquidity_stress_test(self, route: OptimizedRoute) -> Dict[str, Any]:
        """
        Simulate liquidity stress test (+25% concurrent demand)
        
        Returns:
            {"pass": bool, "reason": str}
        """
        # Simulate: if predicted slippage increases by >50% with +25% demand, fail
        stress_slippage = route.predicted_slippage * Decimal('1.5')
        
        if stress_slippage > Decimal(self.risk_thresholds["max_slippage_bps"] / 10000):
            return {
                "pass": False,
                "reason": f"Stress test slippage {stress_slippage*100:.2f}% exceeds threshold"
            }
        
        return {"pass": True, "reason": "Passed"}
    
    def _estimate_gas(self, route: OptimizedRoute) -> int:
        """Estimate gas cost for execution"""
        # Base gas: 120k
        base_gas = 120000
        
        # Per route: 12k
        route_gas = len(route.splits) * 12000
        
        # x402 overhead: 50k
        x402_overhead = 50000
        
        total = base_gas + route_gas + x402_overhead
        return total
    
    async def check_market_regime(self) -> Dict[str, Any]:
        """Check current market regime"""
        # Would query volatility, liquidity, etc.
        return {
            "volatility_ok": True,
            "liquidity_ok": True,
            "emergency_pause": False
        }

