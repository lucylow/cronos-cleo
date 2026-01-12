"""
Risk Manager Agent - Monitors execution risks
"""
import logging
from datetime import datetime
from typing import Dict, Any
from decimal import Decimal

from .base_agent import BaseAgent
from .message_bus import AgentMessage

logger = logging.getLogger(__name__)


class RiskManagerAgent(BaseAgent):
    """Agent responsible for monitoring execution risks"""
    
    def __init__(self):
        super().__init__("risk_manager", "Risk Manager")
        self.risk_thresholds = {
            "max_slippage": Decimal('0.1'),  # 10%
            "max_gas_price": Decimal('100'),  # 100 gwei
            "min_liquidity_ratio": Decimal('0.1')  # 10% of trade size
        }
        self.risk_alerts = []
    
    async def handle_message(self, message: AgentMessage):
        """Handle incoming messages"""
        if message.message_type == "assess_risk":
            # Assess risk for a proposed route
            route_data = message.payload.get("route")
            risk_score = await self._assess_route_risk(route_data)
            
            response = AgentMessage(
                message_id=f"resp_{message.message_id}",
                sender=self.agent_id,
                receiver=message.sender,
                message_type="risk_assessment",
                payload={
                    "risk_score": risk_score,
                    "recommendation": "proceed" if risk_score < 0.5 else "review",
                    "request_id": message.payload.get("request_id")
                }
            )
            await self.send_message(response)
        
        elif message.message_type == "liquidity_update":
            # Monitor liquidity changes
            await self._check_liquidity_risks(message.payload)
    
    async def _assess_route_risk(self, route_data: Dict[str, Any]) -> float:
        """Assess risk score for a route (0.0 = low risk, 1.0 = high risk)"""
        risk_factors = []
        
        # Check slippage
        predicted_slippage = Decimal(str(route_data.get("predicted_slippage", 0)))
        if predicted_slippage > self.risk_thresholds["max_slippage"]:
            risk_factors.append(0.5)
        
        # Check liquidity
        total_amount = Decimal(str(route_data.get("total_amount_in", 0)))
        # This would check against actual liquidity - simplified for demo
        if total_amount > Decimal('1000000'):  # Large trade
            risk_factors.append(0.3)
        
        # Calculate overall risk score
        risk_score = sum(risk_factors) / len(risk_factors) if risk_factors else 0.0
        return min(risk_score, 1.0)
    
    async def _check_liquidity_risks(self, payload: Dict[str, Any]):
        """Check for liquidity-related risks"""
        total_liquidity = payload.get("total_liquidity_usd", 0)
        if total_liquidity < 10000:  # Low total liquidity
            await self.broadcast_event(
                "risk_alert",
                {
                    "type": "low_liquidity",
                    "severity": "medium",
                    "message": "Total liquidity below threshold"
                }
            )

