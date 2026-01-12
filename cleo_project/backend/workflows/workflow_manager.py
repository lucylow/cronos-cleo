"""
C.L.E.O. AI Agent Workflow: Complete Implementation

Complete 8-step workflow:
1. Intent Processing → 2. Liquidity Analysis → 3. Slippage Prediction → 
4. Route Optimization → 5. Risk Assessment → 6. x402 Execution → 
7. Result Analysis → 8. Learning Loop
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from decimal import Decimal, ROUND_DOWN
import numpy as np
from pydantic import BaseModel, Field, validator

try:
    import redis.asyncio as aioredis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False
    aioredis = None

from web3 import Web3, AsyncHTTPProvider
from web3.contract import AsyncContract

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cleo_workflow.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# Data Models
# ============================================================================

class WorkflowState(Enum):
    """Workflow state enumeration"""
    INITIATED = "initiated"
    ANALYZING_LIQUIDITY = "analyzing_liquidity"
    PREDICTING_SLIPPAGE = "predicting_slippage"
    OPTIMIZING_ROUTE = "optimizing_route"
    ASSESSING_RISK = "assessing_risk"
    EXECUTING = "executing"
    MONITORING = "monitoring"
    COMPLETED = "completed"
    FAILED = "failed"


class TradeIntent(BaseModel):
    """Trade intent from user or external system"""
    intent_id: str = Field(default_factory=lambda: f"intent_{int(datetime.now().timestamp() * 1000)}")
    user_address: str
    token_in: str
    token_out: str
    amount_in: Decimal
    max_slippage_percent: Decimal = Decimal("0.5")  # 0.5% default
    max_gas_cro: Decimal = Decimal("0.1")  # 0.1 CRO default
    deadline_seconds: int = 300  # 5 minutes default
    strategy: str = "ai_optimized"  # ai_optimized, balanced, conservative
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    
    @validator('amount_in')
    def validate_amount_positive(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        return v
    
    @validator('max_slippage_percent')
    def validate_slippage(cls, v):
        if not (Decimal('0.01') <= v <= Decimal('10')):  # 0.01% to 10%
            raise ValueError('Slippage must be between 0.01% and 10%')
        return v


class LiquiditySnapshot(BaseModel):
    """Snapshot of liquidity across DEXs"""
    snapshot_id: str
    timestamp: datetime
    token_pair: Tuple[str, str]  # (token_in, token_out)
    pools: List[Dict[str, Any]] = Field(default_factory=list)
    total_liquidity_usd: Decimal = Decimal('0')
    best_price: Decimal = Decimal('0')
    worst_price: Decimal = Decimal('0')
    price_disparity_percent: Decimal = Decimal('0')
    
    class Config:
        arbitrary_types_allowed = True


class SlippagePrediction(BaseModel):
    """Slippage prediction from ML model"""
    prediction_id: str
    timestamp: datetime
    amount_in: Decimal
    liquidity_usd: Decimal
    predicted_slippage_percent: Decimal
    confidence_score: float  # 0.0 to 1.0
    features: Dict[str, float] = Field(default_factory=dict)
    model_version: str = "1.0.0"


class OptimizedRoute(BaseModel):
    """Optimized multi-DEX route"""
    route_id: str
    intent_id: str
    created_at: datetime
    token_in: str
    token_out: str
    total_amount_in: Decimal
    total_expected_out: Decimal
    total_min_out: Decimal  # After slippage tolerance
    splits: List[Dict[str, Any]] = Field(default_factory=list)
    predicted_slippage_percent: Decimal
    predicted_gas_cro: Decimal
    optimization_score: float  # 0.0 to 1.0
    strategy_used: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RiskAssessment(BaseModel):
    """Risk assessment for a route"""
    assessment_id: str
    route_id: str
    timestamp: datetime
    overall_risk_score: float  # 0.0 to 1.0
    slippage_risk: float
    liquidity_risk: float
    execution_risk: float
    gas_risk: float
    recommendations: List[str] = Field(default_factory=list)
    is_approved: bool = False
    approval_reason: Optional[str] = None


class ExecutionPlan(BaseModel):
    """Complete execution plan for x402"""
    plan_id: str
    route: OptimizedRoute
    risk_assessment: RiskAssessment
    x402_operations: List[Dict[str, Any]] = Field(default_factory=list)
    global_condition: str
    deadline_timestamp: int
    gas_limit: int
    max_priority_fee: int
    max_fee: int
    estimated_cost_cro: Decimal


class ExecutionResult(BaseModel):
    """Execution result from x402"""
    result_id: str
    plan_id: str
    intent_id: str
    timestamp: datetime
    success: bool
    tx_hash: Optional[str] = None
    actual_amount_out: Optional[Decimal] = None
    actual_slippage_percent: Optional[Decimal] = None
    gas_used: Optional[Decimal] = None
    gas_cost_cro: Optional[Decimal] = None
    block_number: Optional[int] = None
    execution_time_ms: Optional[int] = None
    errors: List[str] = Field(default_factory=list)
    performance_metrics: Dict[str, Any] = Field(default_factory=dict)


class WorkflowStep(BaseModel):
    """Individual workflow step"""
    step_id: str
    name: str
    state: WorkflowState
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[int] = None
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkflowExecution(BaseModel):
    """Complete workflow execution record"""
    execution_id: str
    intent: TradeIntent
    steps: List[WorkflowStep] = Field(default_factory=list)
    current_state: WorkflowState = WorkflowState.INITIATED
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    result: Optional[ExecutionResult] = None
    performance_score: Optional[float] = None


# ============================================================================
# Workflow Manager
# ============================================================================

class WorkflowManager:
    """Manages the complete AI agent workflow"""
    
    def __init__(self, config: Dict[str, Any], agents: Dict[str, Any] = None):
        self.config = config
        self.redis = None
        self.w3 = None
        self.active_executions: Dict[str, WorkflowExecution] = {}
        self.execution_history: List[WorkflowExecution] = []
        self.agents = agents or {}
        
        # Statistics
        self.stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "total_volume_cro": Decimal('0'),
            "total_savings_usd": Decimal('0'),
            "avg_execution_time_ms": 0
        }
    
    async def initialize(self):
        """Initialize the workflow manager"""
        logger.info("Initializing C.L.E.O. Workflow Manager...")
        
        # Initialize Redis if available
        if HAS_REDIS and self.config.get('redis_url'):
            try:
                self.redis = await aioredis.from_url(
                    self.config['redis_url'],
                    decode_responses=True
                )
                logger.info("Redis connected")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}")
        
        # Initialize Web3
        cronos_rpc = self.config.get('cronos_rpc', 'https://evm-t3.cronos.org')
        self.w3 = Web3(AsyncHTTPProvider(cronos_rpc))
        
        logger.info("Workflow Manager initialized successfully")
    
    async def execute_trade(self, intent: TradeIntent) -> WorkflowExecution:
        """Execute complete trade workflow"""
        execution_id = f"exec_{intent.intent_id}"
        
        # Create workflow execution
        execution = WorkflowExecution(
            execution_id=execution_id,
            intent=intent
        )
        
        self.active_executions[execution_id] = execution
        self.stats["total_executions"] += 1
        
        try:
            logger.info(f"Starting workflow execution {execution_id}")
            
            # Step 1: Process Intent
            await self._execute_step(
                execution,
                "process_intent",
                WorkflowState.INITIATED,
                self._process_intent_step,
                {"intent": intent}
            )
            
            # Step 2: Analyze Liquidity
            liquidity_snapshot = await self._execute_step(
                execution,
                "analyze_liquidity",
                WorkflowState.ANALYZING_LIQUIDITY,
                self._analyze_liquidity_step,
                {"intent": intent}
            )
            
            # Step 3: Predict Slippage
            slippage_prediction = await self._execute_step(
                execution,
                "predict_slippage",
                WorkflowState.PREDICTING_SLIPPAGE,
                self._predict_slippage_step,
                {
                    "intent": intent,
                    "liquidity_snapshot": liquidity_snapshot
                }
            )
            
            # Step 4: Optimize Route
            optimized_route = await self._execute_step(
                execution,
                "optimize_route",
                WorkflowState.OPTIMIZING_ROUTE,
                self._optimize_route_step,
                {
                    "intent": intent,
                    "liquidity_snapshot": liquidity_snapshot,
                    "slippage_prediction": slippage_prediction
                }
            )
            
            # Step 5: Assess Risk
            risk_assessment = await self._execute_step(
                execution,
                "assess_risk",
                WorkflowState.ASSESSING_RISK,
                self._assess_risk_step,
                {
                    "intent": intent,
                    "optimized_route": optimized_route
                }
            )
            
            # If risk assessment fails, stop workflow
            if not risk_assessment.is_approved:
                raise Exception(f"Risk assessment failed: {risk_assessment.recommendations}")
            
            # Step 6: Create Execution Plan
            execution_plan = await self._execute_step(
                execution,
                "create_execution_plan",
                WorkflowState.OPTIMIZING_ROUTE,
                self._create_execution_plan_step,
                {
                    "intent": intent,
                    "optimized_route": optimized_route,
                    "risk_assessment": risk_assessment
                }
            )
            
            # Step 7: Execute via x402
            execution_result = await self._execute_step(
                execution,
                "execute_trade",
                WorkflowState.EXECUTING,
                self._execute_trade_step,
                {"execution_plan": execution_plan}
            )
            
            # Step 8: Analyze Performance
            await self._execute_step(
                execution,
                "analyze_performance",
                WorkflowState.MONITORING,
                self._analyze_performance_step,
                {
                    "intent": intent,
                    "execution_result": execution_result,
                    "optimized_route": optimized_route
                }
            )
            
            # Update execution
            execution.result = execution_result
            execution.current_state = WorkflowState.COMPLETED
            execution.completed_at = datetime.now()
            
            # Calculate performance score
            execution.performance_score = await self._calculate_performance_score(
                execution_result, optimized_route
            )
            
            # Update statistics
            if execution_result.success:
                self.stats["successful_executions"] += 1
                self.stats["total_volume_cro"] += intent.amount_in
                
                # Calculate savings (simplified)
                if execution_result.actual_slippage_percent:
                    baseline_slippage = Decimal('0.02')  # Assume 2% baseline
                    savings = intent.amount_in * (baseline_slippage - execution_result.actual_slippage_percent / 100)
                    self.stats["total_savings_usd"] += savings
            
            # Store in history
            self.execution_history.append(execution)
            
            # Clean up active executions (keep last 100)
            if len(self.active_executions) > 100:
                oldest_id = min(self.active_executions.keys(), 
                              key=lambda k: self.active_executions[k].created_at)
                del self.active_executions[oldest_id]
            
            logger.info(f"Workflow execution {execution_id} completed successfully")
            
            return execution
            
        except Exception as e:
            logger.error(f"Workflow execution {execution_id} failed: {e}")
            
            # Update execution state
            execution.current_state = WorkflowState.FAILED
            execution.completed_at = datetime.now()
            
            # Add error to last step
            if execution.steps:
                execution.steps[-1].error = str(e)
            
            self.stats["failed_executions"] += 1
            
            # Re-raise for caller handling
            raise
    
    async def _execute_step(self, execution: WorkflowExecution, step_name: str,
                          target_state: WorkflowState, step_func: Callable,
                          step_input: Dict[str, Any]) -> Any:
        """Execute a workflow step with proper tracking"""
        step_id = f"{execution.execution_id}_{step_name}"
        
        # Create step record
        step = WorkflowStep(
            step_id=step_id,
            name=step_name,
            state=target_state,
            start_time=datetime.now(),
            input_data=step_input
        )
        
        execution.steps.append(step)
        execution.current_state = target_state
        
        try:
            logger.info(f"Executing step: {step_name}")
            
            # Execute the step
            result = await step_func(**step_input)
            
            # Update step record
            step.end_time = datetime.now()
            step.duration_ms = int((step.end_time - step.start_time).total_seconds() * 1000)
            step.output_data = {"result": result.dict() if hasattr(result, 'dict') else result}
            
            # Store step in Redis for monitoring
            if self.redis:
                try:
                    await self.redis.setex(
                        f"workflow:{execution.execution_id}:step:{step_name}",
                        3600,  # 1 hour TTL
                        json.dumps(step.dict(), default=str)
                    )
                except Exception as e:
                    logger.warning(f"Failed to store step in Redis: {e}")
            
            logger.info(f"Step {step_name} completed in {step.duration_ms}ms")
            
            return result
            
        except Exception as e:
            logger.error(f"Step {step_name} failed: {e}")
            
            step.end_time = datetime.now()
            step.duration_ms = int((step.end_time - step.start_time).total_seconds() * 1000)
            step.error = str(e)
            step.state = WorkflowState.FAILED
            
            raise
    
    # ============================================================================
    # Workflow Steps Implementation
    # ============================================================================
    
    async def _process_intent_step(self, intent: TradeIntent) -> Dict[str, Any]:
        """Step 1: Process trade intent"""
        logger.info(f"Processing intent: {intent.intent_id}")
        
        # Validate intent
        if intent.amount_in < Decimal('10'):  # Minimum 10 CRO
            raise ValueError("Amount too small for optimization")
        
        # Check if tokens are supported
        supported_tokens = await self._get_supported_tokens()
        if intent.token_in not in supported_tokens or intent.token_out not in supported_tokens:
            raise ValueError(f"Unsupported token pair: {intent.token_in}/{intent.token_out}")
        
        # Enrich intent with metadata
        intent.metadata.update({
            "processed_at": datetime.now().isoformat(),
            "workflow_version": "1.0.0",
            "estimated_completion_time": (datetime.now() + timedelta(seconds=30)).isoformat()
        })
        
        # Store intent in Redis
        if self.redis:
            try:
                await self.redis.setex(
                    f"intent:{intent.intent_id}",
                    3600,  # 1 hour TTL
                    intent.json()
                )
            except Exception as e:
                logger.warning(f"Failed to store intent in Redis: {e}")
        
        return {
            "intent": intent.dict(),
            "validation_passed": True,
            "next_step": "analyze_liquidity"
        }
    
    async def _analyze_liquidity_step(self, intent: TradeIntent) -> LiquiditySnapshot:
        """Step 2: Analyze liquidity across DEXs"""
        logger.info(f"Analyzing liquidity for {intent.token_in}/{intent.token_out}")
        
        # Use existing liquidity analyzer agent if available
        if 'liquidity_analyzer' in self.agents:
            analyzer = self.agents['liquidity_analyzer']
            # Get pools from analyzer
            pools_data = await analyzer.get_pools_for_pair(intent.token_in, intent.token_out)
        else:
            # Fallback: use liquidity monitor
            from ai.liquidity_monitor import LiquidityMonitor
            monitor = LiquidityMonitor(self.config.get('cronos_rpc', 'https://evm-t3.cronos.org'))
            pools_data = await monitor.get_all_pools_for_pair(intent.token_in, intent.token_out)
        
        # Convert to snapshot format
        pools = []
        total_liquidity_usd = Decimal('0')
        
        for pool in pools_data:
            pools.append({
                "dex": pool.get("dex", "Unknown"),
                "id": pool.get("id", pool.get("address", "")),
                "reserve0": pool.get("reserve0", pool.get("reserveIn", 0)),
                "reserve1": pool.get("reserve1", pool.get("reserveOut", 0)),
                "reserveUSD": pool.get("reserveUSD", 0),
                "token0": {"id": intent.token_in, "symbol": "TOKEN_IN"},
                "token1": {"id": intent.token_out, "symbol": "TOKEN_OUT"}
            })
            total_liquidity_usd += Decimal(str(pool.get("reserveUSD", 0)))
        
        # Calculate best and worst prices
        prices = []
        for pool in pools:
            reserve0 = Decimal(str(pool['reserve0']))
            reserve1 = Decimal(str(pool['reserve1']))
            if reserve0 > 0:
                if pool['token0']['id'] == intent.token_in:
                    price = reserve1 / reserve0
                else:
                    price = reserve0 / reserve1
                prices.append(price)
        
        best_price = max(prices) if prices else Decimal('0')
        worst_price = min(prices) if prices else Decimal('0')
        
        # Calculate price disparity
        if best_price > 0:
            price_disparity = ((best_price - worst_price) / best_price) * 100
        else:
            price_disparity = Decimal('0')
        
        snapshot = LiquiditySnapshot(
            snapshot_id=f"snapshot_{int(datetime.now().timestamp())}",
            timestamp=datetime.now(),
            token_pair=(intent.token_in, intent.token_out),
            pools=pools,
            total_liquidity_usd=total_liquidity_usd,
            best_price=best_price,
            worst_price=worst_price,
            price_disparity_percent=price_disparity
        )
        
        # Check if liquidity is sufficient
        min_liquidity_usd = Decimal('10000')  # Minimum $10k liquidity
        if snapshot.total_liquidity_usd < min_liquidity_usd:
            raise ValueError(f"Insufficient liquidity: ${snapshot.total_liquidity_usd} < ${min_liquidity_usd}")
        
        logger.info(f"Found {len(pools)} pools with total liquidity: ${snapshot.total_liquidity_usd}")
        
        return snapshot
    
    async def _predict_slippage_step(self, intent: TradeIntent,
                                   liquidity_snapshot: LiquiditySnapshot) -> SlippagePrediction:
        """Step 3: Predict slippage using ML"""
        logger.info(f"Predicting slippage for {intent.amount_in} {intent.token_in}")
        
        # Use existing slippage predictor agent if available
        if 'slippage_predictor' in self.agents:
            predictor = self.agents['slippage_predictor']
            # Get prediction from agent
            prediction_data = await predictor.predict_slippage(
                amount_in=float(intent.amount_in),
                liquidity_usd=float(liquidity_snapshot.total_liquidity_usd),
                token_pair=(intent.token_in, intent.token_out)
            )
            
            predicted_slippage = Decimal(str(prediction_data.get('predicted_slippage', 0.001)))
            confidence = prediction_data.get('confidence', 0.7)
        else:
            # Fallback: simple heuristic
            amount_ratio = float(intent.amount_in) / float(liquidity_snapshot.total_liquidity_usd) if liquidity_snapshot.total_liquidity_usd > 0 else 1.0
            predicted_slippage = Decimal(str(0.001 * (amount_ratio ** 1.5) * 100))  # Convert to percent
            confidence = 0.7
        
        prediction = SlippagePrediction(
            prediction_id=f"pred_{int(datetime.now().timestamp())}",
            timestamp=datetime.now(),
            amount_in=intent.amount_in,
            liquidity_usd=liquidity_snapshot.total_liquidity_usd,
            predicted_slippage_percent=predicted_slippage,
            confidence_score=confidence,
            features={
                "amount_ratio": float(intent.amount_in) / float(liquidity_snapshot.total_liquidity_usd) if liquidity_snapshot.total_liquidity_usd > 0 else 1.0,
                "liquidity_usd": float(liquidity_snapshot.total_liquidity_usd)
            },
            model_version="1.0.0"
        )
        
        # Check if predicted slippage exceeds user's limit
        if prediction.predicted_slippage_percent > intent.max_slippage_percent:
            logger.warning(f"Predicted slippage {prediction.predicted_slippage_percent}% exceeds limit {intent.max_slippage_percent}%")
        
        return prediction
    
    async def _optimize_route_step(self, intent: TradeIntent,
                                 liquidity_snapshot: LiquiditySnapshot,
                                 slippage_prediction: SlippagePrediction) -> OptimizedRoute:
        """Step 4: Optimize multi-DEX route"""
        logger.info(f"Optimizing route for {intent.amount_in} {intent.token_in}")
        
        # Use existing route optimizer agent if available
        if 'route_optimizer' in self.agents:
            optimizer = self.agents['route_optimizer']
            # Get optimized route
            route_data = await optimizer.optimize_route(
                token_in=intent.token_in,
                token_out=intent.token_out,
                amount_in=float(intent.amount_in),
                max_slippage=float(intent.max_slippage_percent / 100),
                strategy=intent.strategy
            )
            
            splits = route_data.get('splits', [])
            total_expected_out = Decimal(str(route_data.get('total_expected_out', 0)))
        else:
            # Fallback: simple split across top pools
            splits = []
            top_pools = sorted(
                liquidity_snapshot.pools,
                key=lambda p: Decimal(str(p.get('reserveUSD', 0))),
                reverse=True
            )[:3]
            
            if not top_pools:
                raise ValueError("No pools available for optimization")
            
            split_amount = intent.amount_in / len(top_pools)
            total_expected_out = Decimal('0')
            
            for pool in top_pools:
                reserve0 = Decimal(str(pool['reserve0']))
                reserve1 = Decimal(str(pool['reserve1']))
                
                if pool['token0']['id'] == intent.token_in:
                    expected_out = (split_amount * reserve1) / (reserve0 + split_amount)
                else:
                    expected_out = (split_amount * reserve0) / (reserve1 + split_amount)
                
                splits.append({
                    "dex": pool.get('dex', 'Unknown'),
                    "pool_address": pool['id'],
                    "token_in": intent.token_in,
                    "token_out": intent.token_out,
                    "amount_in": float(split_amount),
                    "expected_amount_out": float(expected_out),
                    "min_amount_out": float(expected_out * (1 - intent.max_slippage_percent / 100)),
                    "path": [intent.token_in, intent.token_out],
                    "pool_share_percent": 100 / len(top_pools)
                })
                
                total_expected_out += expected_out
        
        total_min_out = total_expected_out * (1 - intent.max_slippage_percent / 100)
        
        # Estimate gas
        predicted_gas = Decimal('0.05')  # Simplified
        
        route = OptimizedRoute(
            route_id=f"route_{intent.intent_id}",
            intent_id=intent.intent_id,
            created_at=datetime.now(),
            token_in=intent.token_in,
            token_out=intent.token_out,
            total_amount_in=intent.amount_in,
            total_expected_out=total_expected_out,
            total_min_out=total_min_out,
            splits=splits,
            predicted_slippage_percent=slippage_prediction.predicted_slippage_percent,
            predicted_gas_cro=predicted_gas,
            optimization_score=0.8,  # Simplified
            strategy_used=intent.strategy,
            metadata={
                "num_splits": len(splits),
                "num_dexes": len(set(split.get('dex', 'Unknown') for split in splits))
            }
        )
        
        logger.info(f"Route optimized with {len(splits)} splits, expected output: {total_expected_out}")
        
        return route
    
    async def _assess_risk_step(self, intent: TradeIntent,
                              optimized_route: OptimizedRoute) -> RiskAssessment:
        """Step 5: Assess risks of the optimized route"""
        logger.info(f"Assessing risks for route {optimized_route.route_id}")
        
        # Use existing risk manager if available
        if 'risk_manager' in self.agents:
            risk_manager = self.agents['risk_manager']
            risk_data = await risk_manager.assess_risk(
                route=optimized_route.dict(),
                intent=intent.dict()
            )
            
            overall_risk = risk_data.get('overall_risk', 0.5)
            is_approved = risk_data.get('approved', overall_risk < 0.7)
        else:
            # Fallback: simple risk assessment
            slippage_risk = min(float(optimized_route.predicted_slippage_percent) / 5.0, 1.0)
            liquidity_risk = 0.3  # Simplified
            execution_risk = 0.2  # Simplified
            gas_risk = min(float(optimized_route.predicted_gas_cro) / 0.1, 1.0)
            
            overall_risk = (slippage_risk * 0.4 + liquidity_risk * 0.3 + execution_risk * 0.2 + gas_risk * 0.1)
            is_approved = overall_risk < 0.7
        
        assessment = RiskAssessment(
            assessment_id=f"risk_{int(datetime.now().timestamp())}",
            route_id=optimized_route.route_id,
            timestamp=datetime.now(),
            overall_risk_score=overall_risk,
            slippage_risk=slippage_risk if 'risk_manager' not in self.agents else risk_data.get('slippage_risk', 0.5),
            liquidity_risk=liquidity_risk if 'risk_manager' not in self.agents else risk_data.get('liquidity_risk', 0.3),
            execution_risk=execution_risk if 'risk_manager' not in self.agents else risk_data.get('execution_risk', 0.2),
            gas_risk=gas_risk if 'risk_manager' not in self.agents else risk_data.get('gas_risk', 0.2),
            recommendations=[] if is_approved else ["Risk score too high"],
            is_approved=is_approved,
            approval_reason="Risk assessment passed" if is_approved else "Risk score exceeds threshold"
        )
        
        risk_level = "HIGH" if assessment.overall_risk_score > 0.7 else \
                    "MEDIUM" if assessment.overall_risk_score > 0.3 else "LOW"
        
        logger.info(f"Risk assessment: {risk_level} (score: {assessment.overall_risk_score})")
        logger.info(f"Approved: {assessment.is_approved}")
        
        return assessment
    
    async def _create_execution_plan_step(self, intent: TradeIntent,
                                        optimized_route: OptimizedRoute,
                                        risk_assessment: RiskAssessment) -> ExecutionPlan:
        """Step 6: Create x402 execution plan"""
        logger.info(f"Creating execution plan for route {optimized_route.route_id}")
        
        # Build x402 operations from splits
        x402_operations = []
        for split in optimized_route.splits:
            x402_operations.append({
                "type": "swap",
                "dex": split.get('dex'),
                "pool": split.get('pool_address'),
                "token_in": split.get('token_in'),
                "token_out": split.get('token_out'),
                "amount_in": split.get('amount_in'),
                "min_amount_out": split.get('min_amount_out'),
                "path": split.get('path', [])
            })
        
        # Calculate deadline
        deadline_timestamp = int((datetime.now() + timedelta(seconds=intent.deadline_seconds)).timestamp())
        
        plan = ExecutionPlan(
            plan_id=f"plan_{intent.intent_id}",
            route=optimized_route,
            risk_assessment=risk_assessment,
            x402_operations=x402_operations,
            global_condition=f"total_out >= {optimized_route.total_min_out}",
            deadline_timestamp=deadline_timestamp,
            gas_limit=500000,  # Simplified
            max_priority_fee=2000000000,  # 2 Gwei
            max_fee=50000000000,  # 50 Gwei
            estimated_cost_cro=optimized_route.predicted_gas_cro
        )
        
        logger.info(f"Execution plan created with {len(x402_operations)} operations")
        logger.info(f"Estimated gas cost: {plan.estimated_cost_cro} CRO")
        
        return plan
    
    async def _execute_trade_step(self, execution_plan: ExecutionPlan) -> ExecutionResult:
        """Step 7: Execute trade via x402"""
        logger.info(f"Executing trade with plan {execution_plan.plan_id}")
        
        # Use existing execution agent or x402 executor
        if 'execution_agent' in self.agents:
            executor = self.agents['execution_agent']
            result_data = await executor.execute_trade(execution_plan.dict())
            
            success = result_data.get('success', False)
            tx_hash = result_data.get('tx_hash')
            actual_amount_out = Decimal(str(result_data.get('actual_amount_out', 0))) if result_data.get('actual_amount_out') else None
        else:
            # Fallback: simulate execution (for testing)
            logger.warning("No execution agent available, simulating execution")
            success = True
            tx_hash = f"0x{'0' * 64}"  # Placeholder
            actual_amount_out = execution_plan.route.total_expected_out * Decimal('0.99')  # Simulate 1% slippage
        
        # Calculate actual slippage
        if actual_amount_out and execution_plan.route.total_expected_out > 0:
            actual_slippage = ((execution_plan.route.total_expected_out - actual_amount_out) / execution_plan.route.total_expected_out) * 100
        else:
            actual_slippage = None
        
        result = ExecutionResult(
            result_id=f"result_{execution_plan.plan_id}",
            plan_id=execution_plan.plan_id,
            intent_id=execution_plan.route.intent_id,
            timestamp=datetime.now(),
            success=success,
            tx_hash=tx_hash,
            actual_amount_out=actual_amount_out,
            actual_slippage_percent=actual_slippage,
            gas_used=Decimal(str(execution_plan.estimated_cost_cro)),
            gas_cost_cro=execution_plan.estimated_cost_cro,
            block_number=None,
            execution_time_ms=5000,  # Simplified
            errors=[] if success else ["Execution failed"],
            performance_metrics={}
        )
        
        if result.success:
            logger.info(f"Trade executed successfully: {result.tx_hash}")
            logger.info(f"Actual slippage: {result.actual_slippage_percent}%")
        else:
            logger.error(f"Trade execution failed: {result.errors}")
        
        return result
    
    async def _analyze_performance_step(self, intent: TradeIntent,
                                      execution_result: ExecutionResult,
                                      optimized_route: OptimizedRoute) -> Dict[str, Any]:
        """Step 8: Analyze performance and update models"""
        logger.info(f"Analyzing performance for execution {execution_result.result_id}")
        
        # Use existing performance monitor if available
        if 'performance_monitor' in self.agents:
            monitor = self.agents['performance_monitor']
            analysis = await monitor.analyze_execution(
                intent=intent.dict(),
                result=execution_result.dict(),
                route=optimized_route.dict()
            )
        else:
            # Fallback: simple analysis
            analysis = {
                "slippage_accuracy": 0.9 if execution_result.actual_slippage_percent else 0.0,
                "execution_success": execution_result.success,
                "gas_efficiency": 0.8,
                "route_quality": optimized_route.optimization_score
            }
        
        # Update ML models with new data
        if execution_result.success and self.redis:
            try:
                training_data = {
                    "timestamp": datetime.now().isoformat(),
                    "intent": intent.dict(),
                    "result": execution_result.dict(),
                    "route": optimized_route.dict(),
                    "actual_slippage": float(execution_result.actual_slippage_percent) if execution_result.actual_slippage_percent else None,
                    "predicted_slippage": float(optimized_route.predicted_slippage_percent),
                    "error": float(execution_result.actual_slippage_percent - optimized_route.predicted_slippage_percent) if execution_result.actual_slippage_percent else None
                }
                
                await self.redis.rpush(
                    "ml_training_data",
                    json.dumps(training_data, default=str)
                )
                
                # Keep only last 1000 samples
                await self.redis.ltrim("ml_training_data", 0, 999)
            except Exception as e:
                logger.warning(f"Failed to update ML training data: {e}")
        
        logger.info(f"Performance analysis completed: {analysis}")
        
        return analysis
    
    async def _calculate_performance_score(self, result: ExecutionResult,
                                         route: OptimizedRoute) -> float:
        """Calculate performance score for execution"""
        if not result.success:
            return 0.0
        
        # Score components (each 0-1)
        slippage_score = 1.0 - min(float(result.actual_slippage_percent or 0) / 5.0, 1.0)
        gas_efficiency = 1.0 - min(float(result.gas_cost_cro or 0) / 0.05, 1.0)
        execution_speed = 1.0 - min((result.execution_time_ms or 10000) / 10000, 1.0)
        
        if result.actual_amount_out and route.total_expected_out > 0:
            accuracy_score = float(result.actual_amount_out / route.total_expected_out)
        else:
            accuracy_score = 0.0
        
        # Weighted average
        weights = {
            'slippage': 0.4,
            'gas': 0.3,
            'speed': 0.2,
            'accuracy': 0.1
        }
        
        score = (
            slippage_score * weights['slippage'] +
            gas_efficiency * weights['gas'] +
            execution_speed * weights['speed'] +
            accuracy_score * weights['accuracy']
        )
        
        return round(score, 2)
    
    async def _get_supported_tokens(self) -> List[str]:
        """Get list of supported tokens"""
        # In production, this would fetch from a config or API
        return [
            "0x5C7F8A570d578ED84E63fdFA7b1eE72dEae1AE23",  # WCRO
            "0xc21223249CA28397B4B6541dfFaEcC539BfF0c59",  # USDC
            "0x66e428c3f67a68878562e79A0234c1F83c208770",  # USDT
            "0xe243CCab9E66E6cF1215376980811ddf1eb7F689"   # ETH
        ]
    
    async def get_workflow_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a workflow execution"""
        if execution_id in self.active_executions:
            execution = self.active_executions[execution_id]
        else:
            # Try to find in history
            for exec in self.execution_history:
                if exec.execution_id == execution_id:
                    execution = exec
                    break
            else:
                return None
        
        # Calculate progress
        total_steps = len(execution.steps)
        completed_steps = sum(1 for step in execution.steps if step.end_time)
        
        return {
            "execution_id": execution_id,
            "current_state": execution.current_state.value,
            "progress": f"{completed_steps}/{total_steps}",
            "current_step": execution.steps[-1].name if execution.steps else None,
            "created_at": execution.created_at.isoformat(),
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "intent": execution.intent.dict(),
            "steps": [step.dict() for step in execution.steps],
            "result": execution.result.dict() if execution.result else None,
            "performance_score": execution.performance_score
        }
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get workflow statistics"""
        return {
            **self.stats,
            "total_volume_cro": str(self.stats["total_volume_cro"]),
            "total_savings_usd": str(self.stats["total_savings_usd"]),
            "active_executions": len(self.active_executions),
            "historical_executions": len(self.execution_history),
            "success_rate": (
                self.stats["successful_executions"] / self.stats["total_executions"]
                if self.stats["total_executions"] > 0 else 0
            ),
            "avg_volume_per_trade": (
                str(self.stats["total_volume_cro"] / self.stats["successful_executions"])
                if self.stats["successful_executions"] > 0 else "0"
            )
        }
