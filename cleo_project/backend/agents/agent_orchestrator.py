"""
Agent Orchestrator - Main routing engine for C.L.E.O.
Coordinates all agents in the orchestration workflow with AI model integration
"""
import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import numpy as np

from .liquidity_scout import LiquidityScoutAgent
from .split_optimizer_lp import SplitOptimizerAgent
from .risk_validator import RiskValidatorAgent
from .execution_agent import ExecutionAgent

logger = logging.getLogger(__name__)

# Import BaseModel for Pydantic models
try:
    from pydantic import BaseModel
except ImportError:
    # Fallback if pydantic not available
    class BaseModel:
        pass

# Try to import AI model orchestrator
try:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from ai.model_orchestrator import AIModelOrchestrator
    HAS_AI_MODELS = True
except ImportError:
    logger.warning("AI model orchestrator not available - running without ML predictions")
    HAS_AI_MODELS = False
    AIModelOrchestrator = None


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
    """Main orchestrator that coordinates all agents with AI model integration"""
    
    def __init__(self, redis_client=None, x402_executor=None):
        self.redis = redis_client
        self.x402_executor = x402_executor
        
        # Initialize AI model orchestrator if available
        self.ai_orchestrator = None
        self.ai_models_available = False
        if HAS_AI_MODELS and AIModelOrchestrator:
            try:
                self.ai_orchestrator = AIModelOrchestrator()
                logger.info("AI model orchestrator initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize AI model orchestrator: {e}")
        
        # Initialize agents
        self.agents = {
            AgentType.LIQUIDITY_SCOUT: LiquidityScoutAgent(),
            AgentType.SPLIT_OPTIMIZER: SplitOptimizerAgent(),
            AgentType.RISK_VALIDATOR: RiskValidatorAgent(redis_client=redis_client),
            AgentType.X402_EXECUTOR: ExecutionAgent(x402_executor=x402_executor)
        }
        
        # Performance metrics
        self.metrics = {
            "total_workflows": 0,
            "successful_workflows": 0,
            "failed_workflows": 0,
            "ai_predictions_used": 0,
            "avg_response_time_ms": 0,
            "total_response_time_ms": 0
        }
        
        # AI prediction cache
        self.ai_cache = {}
        self.cache_ttl = 300  # 5 minutes
        
        # Start all agents
        asyncio.create_task(self._start_agents())
        
        # Initialize AI models asynchronously
        if self.ai_orchestrator:
            asyncio.create_task(self._initialize_ai_models())
    
    async def _start_agents(self):
        """Start all agents"""
        for agent in self.agents.values():
            if hasattr(agent, 'start'):
                await agent.start()
    
    async def _initialize_ai_models(self):
        """Initialize AI models asynchronously"""
        if self.ai_orchestrator:
            try:
                await self.ai_orchestrator.initialize()
                self.ai_models_available = True
                logger.info("AI models initialized and ready")
            except Exception as e:
                logger.warning(f"Failed to initialize AI models: {e}")
                self.ai_models_available = False
    
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
            
            # Phase 1.5: AI Model Predictions (if available)
            ai_predictions = None
            if self.ai_models_available and self.ai_orchestrator:
                try:
                    ai_predictions = await self._get_ai_predictions(
                        swap_request, liquidity_data, workflow_id
                    )
                    if ai_predictions:
                        self.metrics["ai_predictions_used"] += 1
                        logger.info(f"[{workflow_id}] AI predictions: {ai_predictions.get('confidence_score', 0):.2%} confidence")
                except Exception as e:
                    logger.warning(f"[{workflow_id}] AI prediction failed: {e}, continuing without ML")
            
            # Phase 2: Split Optimization (enhanced with AI predictions)
            logger.info(f"[{workflow_id}] Phase 2: Split Optimization...")
            optimizer_input = {
                "liquidity_data": liquidity_data,
                "total_amount": swap_request.amount_in,
                "slippage_tolerance": swap_request.slippage_tolerance,
                "input_token": swap_request.input_token,
                "output_token": swap_request.output_token
            }
            
            # Enhance optimizer input with AI predictions
            if ai_predictions:
                optimizer_input["ai_predictions"] = {
                    "predicted_slippage": ai_predictions.get("predictions", {}).get("slippage", {}).get("predicted_slippage_percent", None),
                    "risk_score": ai_predictions.get("predictions", {}).get("risk", {}).get("risk_score", None),
                    "success_probability": ai_predictions.get("predictions", {}).get("success", {}).get("success_probability", None),
                    "recommendation": ai_predictions.get("recommendation", {})
                }
            
            split_plan = await self.agents[AgentType.SPLIT_OPTIMIZER].execute(optimizer_input)
            
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
            
            # Phase 3: Risk Validation (enhanced with AI predictions)
            logger.info(f"[{workflow_id}] Phase 3: Risk Validation...")
            risk_input = {
                "split_plan": split_plan,
                "user_address": swap_request.user_address
            }
            
            # Add AI risk assessment if available
            if ai_predictions and "risk" in ai_predictions.get("predictions", {}):
                risk_input["ai_risk_assessment"] = ai_predictions["predictions"]["risk"]
            
            risk_report = await self.agents[AgentType.RISK_VALIDATOR].execute(risk_input)
            
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
            
            result = {
                "status": "completed",
                "workflow_id": workflow_id,
                "predicted_slippage": split_plan.get("predicted_slippage", 0.0),
                "tx_hash": execution_result.tx_hash if execution_result.success else None,
                "actual_output": float(execution_result.actual_amount_out) if execution_result.actual_amount_out else None,
                "risk_score": risk_report.get("risk_score", 1.0),
                "gas_estimate": risk_report.get("gas_estimate", 0.0),
                "confidence_score": split_plan.get("confidence", 0.0)
            }
            
            # Add AI predictions to result if available
            if ai_predictions:
                result["ai_insights"] = {
                    "confidence": ai_predictions.get("confidence_score", 0.0),
                    "recommendation": ai_predictions.get("recommendation", {}).get("action", "PROCEED"),
                    "models_used": ai_predictions.get("models_used", [])
                }
            
            # Update metrics
            self.metrics["total_workflows"] += 1
            self.metrics["successful_workflows"] += 1
            
            return result
        
        except Exception as e:
            logger.error(f"[{workflow_id}] Orchestration error: {e}")
            self.metrics["total_workflows"] += 1
            self.metrics["failed_workflows"] += 1
            return {
                "status": "error",
                "workflow_id": workflow_id,
                "error": str(e)
            }
    
    async def _get_ai_predictions(self, swap_request: SwapRequest, 
                                   liquidity_data: Dict, workflow_id: str) -> Optional[Dict]:
        """Get AI model predictions for the swap request"""
        if not self.ai_orchestrator or not self.ai_models_available:
            return None
        
        # Create cache key
        cache_key = f"{swap_request.input_token}:{swap_request.output_token}:{swap_request.amount_in}"
        cache_entry = self.ai_cache.get(cache_key)
        
        # Check cache
        if cache_entry and (datetime.now() - cache_entry["timestamp"]).seconds < self.cache_ttl:
            logger.debug(f"[{workflow_id}] Using cached AI predictions")
            return cache_entry["predictions"]
        
        try:
            # Prepare trade data for AI analysis
            pools = liquidity_data.get("pools", [])
            total_liquidity_usd = sum(p.get("liquidity_usd", 0) for p in pools)
            amount_usd = swap_request.amount_in * 0.08  # Rough estimate for CRO/USD
            
            # Create historical data from pools (simplified)
            historical_data = pd.DataFrame({
                'price': [p.get("price", 0.08) for p in pools[:100]],
                'liquidity': [p.get("liquidity_usd", 0) for p in pools[:100]],
                'volume': [p.get("volume_24h", 0) for p in pools[:100]]
            })
            
            trade_data = {
                'trade_id': workflow_id,
                'amount_in_usd': float(amount_usd),
                'token_pair': f"{swap_request.input_token[:8]}/{swap_request.output_token[:8]}",
                'max_slippage_percent': swap_request.slippage_tolerance * 100,
                'historical_data': historical_data,
                'historical_gas_prices': np.random.normal(10, 2, 50).tolist(),  # Would use real data
                'network_conditions': {'congestion': 0.3, 'pending_txs': 1500},
                'available_liquidity_usd': total_liquidity_usd,
                'volatility': 0.15,
                'current_gas_price': 12.5,
                'average_gas_price': 10.0,
                'available_dexes': len(pools)
            }
            
            # Run AI analysis
            predictions = await self.ai_orchestrator.analyze_trade(trade_data)
            
            # Cache the predictions
            self.ai_cache[cache_key] = {
                "predictions": predictions,
                "timestamp": datetime.now()
            }
            
            # Clean old cache entries (keep last 100)
            if len(self.ai_cache) > 100:
                oldest_key = min(self.ai_cache.keys(), 
                               key=lambda k: self.ai_cache[k]["timestamp"])
                del self.ai_cache[oldest_key]
            
            return predictions
            
        except Exception as e:
            logger.error(f"[{workflow_id}] AI prediction error: {e}")
            return None
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        success_rate = 0.0
        if self.metrics["total_workflows"] > 0:
            success_rate = (self.metrics["successful_workflows"] / 
                          self.metrics["total_workflows"]) * 100
        
        avg_response_time = 0.0
        if self.metrics["total_workflows"] > 0:
            avg_response_time = self.metrics["total_response_time_ms"] / self.metrics["total_workflows"]
        
        return {
            **self.metrics,
            "success_rate": success_rate,
            "avg_response_time_ms": avg_response_time,
            "ai_models_available": self.ai_models_available,
            "ai_cache_size": len(self.ai_cache)
        }
    
    def get_ai_model_status(self) -> Dict[str, Any]:
        """Get AI model status"""
        if not self.ai_orchestrator:
            return {
                "available": False,
                "initialized": False,
                "models": {}
            }
        
        models_status = {}
        for name, model in self.ai_orchestrator.models.items():
            models_status[name] = {
                "is_trained": model.is_trained,
                "version": model.version,
                "model_name": model.model_name
            }
        
        return {
            "available": True,
            "initialized": self.ai_models_available,
            "models": models_status
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
