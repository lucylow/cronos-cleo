"""
Agent Orchestrator - Main routing engine for C.L.E.O.
Coordinates all agents in the orchestration workflow
"""
import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

from .liquidity_scout import LiquidityScoutAgent
from .split_optimizer_lp import SplitOptimizerAgent
from .risk_validator import RiskValidatorAgent
from .execution_agent import ExecutionAgent

logger = logging.getLogger(__name__)


class AgentType(str, Enum):
    """Agent type enumeration"""
    LIQUIDITY_SCOUT = "liquidity_scout"
    SPLIT_OPTIMIZER = "split_optimizer"
    RISK_VALIDATOR = "risk_validator"
    X402_EXECUTOR = "x402_executor"


@dataclass
class SwapRequest:
    """Swap request data structure"""
    input_token: str
    output_token: str
    amount_in: int
    slippage_tolerance: float
    user_address: str
    deadline: int = 0


class SwapRequestModel(BaseModel):
    """Pydantic model for swap request"""
    input_token: str
    output_token: str
    amount_in: int
    slippage_tolerance: float = 0.005
    user_address: str
    deadline: int = 0


class AgentOrchestrator:
    """Main orchestrator that coordinates all agents"""
    
    def __init__(self, redis_client=None, x402_executor=None):
        self.redis = redis_client
        self.x402_executor = x402_executor
        
        # Initialize agents
        self.agents = {
            AgentType.LIQUIDITY_SCOUT: LiquidityScoutAgent(),
            AgentType.SPLIT_OPTIMIZER: SplitOptimizerAgent(),
            AgentType.RISK_VALIDATOR: RiskValidatorAgent(redis_client=redis_client),
            AgentType.X402_EXECUTOR: ExecutionAgent(x402_executor=x402_executor)
        }
        
        # Start all agents
        asyncio.create_task(self._start_agents())
    
    async def _start_agents(self):
        """Start all agents"""
        for agent in self.agents.values():
            if hasattr(agent, 'start'):
                await agent.start()
    
    async def orchestrate_swap(self, swap_request: SwapRequest) -> Dict:
        """
        Main orchestration workflow
        
        Args:
            swap_request: SwapRequest with swap parameters
            
        Returns:
            Dict with execution result
        """
        workflow_id = f"wf_{datetime.now().timestamp()}"
        logger.info(f"[{workflow_id}] Starting orchestration workflow")
        
        try:
            # Phase 1: Liquidity Discovery
            logger.info(f"[{workflow_id}] Phase 1: Liquidity Scout...")
            liquidity_data = await self.agents[AgentType.LIQUIDITY_SCOUT].execute({
                "input_token": swap_request.input_token,
                "output_token": swap_request.output_token,
                "amount_in": swap_request.amount_in
            })
            
            # Cache liquidity data
            if self.redis:
                try:
                    await self.redis.setex(
                        f"{workflow_id}:liquidity",
                        30,
                        json.dumps(liquidity_data)
                    )
                except Exception as e:
                    logger.warning(f"Redis cache error: {e}")
            
            # Phase 2: Split Optimization
            logger.info(f"[{workflow_id}] Phase 2: Split Optimization...")
            split_plan = await self.agents[AgentType.SPLIT_OPTIMIZER].execute({
                "liquidity_data": liquidity_data,
                "total_amount": swap_request.amount_in,
                "slippage_tolerance": swap_request.slippage_tolerance,
                "input_token": swap_request.input_token,
                "output_token": swap_request.output_token
            })
            
            # Cache split plan
            if self.redis:
                try:
                    await self.redis.setex(
                        f"{workflow_id}:split",
                        30,
                        json.dumps(split_plan)
                    )
                except Exception as e:
                    logger.warning(f"Redis cache error: {e}")
            
            # Phase 3: Risk Validation
            logger.info(f"[{workflow_id}] Phase 3: Risk Validation...")
            risk_report = await self.agents[AgentType.RISK_VALIDATOR].execute({
                "split_plan": split_plan,
                "user_address": swap_request.user_address
            })
            
            if not risk_report.get("approved", False):
                return {
                    "status": "rejected",
                    "workflow_id": workflow_id,
                    "reason": risk_report.get("rejection_reason", "Risk validation failed")
                }
            
            # Phase 4: x402 Execution
            logger.info(f"[{workflow_id}] Phase 4: x402 Execution...")
            optimized_route = self._convert_split_plan_to_route(split_plan, swap_request)
            execution_result = await self.agents[AgentType.X402_EXECUTOR].execute_route(
                optimized_route
            )
            
            return {
                "status": "completed",
                "workflow_id": workflow_id,
                "predicted_slippage": split_plan.get("predicted_slippage", 0.0),
                "tx_hash": execution_result.tx_hash if execution_result.success else None,
                "actual_output": float(execution_result.actual_amount_out) if execution_result.actual_amount_out else None,
                "risk_score": risk_report.get("risk_score", 1.0),
                "gas_estimate": risk_report.get("gas_estimate", 0.0)
            }
        
        except Exception as e:
            logger.error(f"[{workflow_id}] Orchestration error: {e}")
            return {
                "status": "error",
                "workflow_id": workflow_id,
                "error": str(e)
            }
    
    def _convert_split_plan_to_route(self, split_plan: Dict, swap_request: SwapRequest):
        """Convert split plan to OptimizedRoute format"""
        from .models import OptimizedRoute, RouteSplit, Token
        
        routes = split_plan.get("routes", [])
        splits = []
        
        for route in routes:
            splits.append(RouteSplit(
                dex_name=route.get("dex_id", ""),
                pool_address=route.get("pool_address", ""),
                token_in=Token(
                    address=swap_request.input_token,
                    symbol="",
                    decimals=18,
                    name=""
                ),
                token_out=Token(
                    address=swap_request.output_token,
                    symbol="",
                    decimals=18,
                    name=""
                ),
                amount_in=route.get("amount_in", 0),
                expected_amount_out=route.get("min_amount_out", 0),
                min_amount_out=route.get("min_amount_out", 0),
                path=route.get("path", [])
            ))
        
        return OptimizedRoute(
            route_id=f"route_{datetime.now().timestamp()}",
            token_in=Token(
                address=swap_request.input_token,
                symbol="",
                decimals=18,
                name=""
            ),
            token_out=Token(
                address=swap_request.output_token,
                symbol="",
                decimals=18,
                name=""
            ),
            total_amount_in=swap_request.amount_in,
            total_expected_out=split_plan.get("predicted_total_out", 0),
            total_min_out=sum(r.get("min_amount_out", 0) for r in routes),
            splits=splits,
            predicted_slippage=split_plan.get("predicted_slippage", 0.0),
            expected_gas=0.05,
            confidence_score=split_plan.get("confidence", 0.0),
            risk_score=0.1
        )


# Note: The FastAPI endpoints are integrated into main.py
# This module provides the AgentOrchestrator class for use in the main application
