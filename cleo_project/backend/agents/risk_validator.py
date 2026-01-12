"""
Risk Validator Agent - Validates swap execution risks
Implements the risk validation phase of the orchestration workflow
"""
import logging
from typing import Dict, List, Any, Optional
from decimal import Decimal

from .base_agent import BaseAgent
from .message_bus import AgentMessage

logger = logging.getLogger(__name__)


class RiskValidatorAgent(BaseAgent):
    """Agent responsible for validating swap execution risks"""
    
    def __init__(self, redis_client=None):
        super().__init__("risk_validator", "Risk Validator")
        self.redis = redis_client
        self.max_pool_impact = 0.15  # 15% max per pool
        self.volatility_threshold = 3.0  # 3% 1h vol
        self.max_gas_cro = 0.05  # 0.05 CRO max gas
    
    async def execute(self, request: Dict) -> Dict:
        """
        Execute risk validation for a split plan
        
        Args:
            request: Dict with 'split_plan', 'user_address'
            
        Returns:
            Dict with 'approved', 'risk_score', and optional 'rejection_reason'
        """
        split_plan = request.get("split_plan", {})
        routes = split_plan.get("routes", [])
        user_address = request.get("user_address", "")
        
        if not routes:
            return {
                "approved": False,
                "rejection_reason": "No routes provided"
            }
        
        # Check 1: Pool impact limits
        for route in routes:
            dex_id = route.get("dex_id", "")
            amount_in = route.get("amount_in", 0)
            
            pool_depth = await self._get_pool_depth(dex_id, route.get("router", ""))
            if pool_depth > 0:
                impact = amount_in / pool_depth
                if impact > self.max_pool_impact:
                    return {
                        "approved": False,
                        "rejection_reason": f"Pool impact exceeded: {dex_id} {impact:.1%}"
                    }
        
        # Check 2: Volatility filter
        volatility = await self._get_market_volatility()
        if volatility > self.volatility_threshold:
            return {
                "approved": False,
                "rejection_reason": f"High volatility: {volatility:.1f}%"
            }
        
        # Check 3: Gas estimation
        gas_estimate = await self._estimate_gas(routes)
        if gas_estimate > self.max_gas_cro:
            return {
                "approved": False,
                "rejection_reason": f"Gas too high: {gas_estimate} CRO"
            }
        
        # All checks passed
        risk_score = self._calculate_risk_score(routes, volatility, gas_estimate)
        
        return {
            "approved": True,
            "risk_score": risk_score,
            "gas_estimate": gas_estimate,
            "volatility": volatility
        }
    
    async def _get_pool_depth(self, dex_id: str, router: str) -> float:
        """Get pool depth from cache or default"""
        if self.redis:
            try:
                cached = await self.redis.get(f"pool_depth:{dex_id}")
                if cached:
                    return float(cached)
            except Exception as e:
                logger.debug(f"Redis error getting pool depth: {e}")
        
        # Default pool depth (1M CRO equivalent)
        return 1000000.0
    
    async def _get_market_volatility(self) -> float:
        """Get market volatility (mock implementation - would use Crypto.com MCP)"""
        # In production, this would call Crypto.com MCP for real volatility data
        # For now, return a mock value
        return 1.8  # 1.8% volatility
    
    async def _estimate_gas(self, routes: List[Dict]) -> float:
        """Estimate gas cost in CRO"""
        # Base gas + per route gas
        base_gas = 21000
        per_route_gas = 75000
        total_gas = base_gas + (per_route_gas * len(routes))
        
        # Convert to CRO (assuming 0.12 CRO per 1B gas units)
        gas_in_cro = (total_gas / 1e9) * 0.12
        return gas_in_cro
    
    def _calculate_risk_score(self, routes: List[Dict], volatility: float, 
                            gas_estimate: float) -> float:
        """Calculate overall risk score (0-1, lower is better)"""
        # Simple risk scoring
        route_count_risk = min(len(routes) / 10.0, 0.3)  # Max 0.3 for route count
        volatility_risk = min(volatility / 10.0, 0.4)  # Max 0.4 for volatility
        gas_risk = min(gas_estimate / 0.1, 0.3)  # Max 0.3 for gas
        
        total_risk = route_count_risk + volatility_risk + gas_risk
        return min(total_risk, 1.0)
    
    async def handle_message(self, message: AgentMessage):
        """Handle incoming messages"""
        if message.message_type == "validate_risk":
            request_id = message.payload.get("request_id")
            
            result = await self.execute({
                "split_plan": message.payload.get("split_plan", {}),
                "user_address": message.payload.get("user_address", "")
            })
            
            response = AgentMessage(
                message_id=f"resp_{message.message_id}",
                sender=self.agent_id,
                receiver=message.sender,
                message_type="risk_validated",
                payload={
                    "result": result,
                    "request_id": request_id
                }
            )
            await self.send_message(response)
