"""
FastAPI backend server for C.L.E.O. - Cronos Liquidity Execution Orchestrator
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import os
import asyncio
from datetime import datetime
from decimal import Decimal
from dotenv import load_dotenv

from ai.ai_agent import RouteOptimizerAgent
from ai.liquidity_monitor import LiquidityMonitor
from ai.data_pipeline import DataPipeline
from mcp_client import MCPClient
from x402_executor import X402Executor
from web3 import Web3

# Multi-leg transaction imports
try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from multi_leg.models import Base, MultiLegTransaction, TransactionLeg, Batch
    from multi_leg.coordinator import MultiLegCoordinator, CompensationStrategy
    from multi_leg.batching import BatchingService, BatchingStrategy
    from multi_leg.reconciliation import ReconciliationService
    HAS_MULTI_LEG = True
except ImportError as e:
    print(f"Warning: Multi-leg module not available: {e}")
    HAS_MULTI_LEG = False
    MultiLegCoordinator = None
    BatchingService = None

# Multi-agent system imports
try:
    from agents.orchestrator import OrchestratorAgent
    from agents.message_bus import message_bus
    HAS_MULTI_AGENT = True
except ImportError:
    HAS_MULTI_AGENT = False
    OrchestratorAgent = None
    message_bus = None

# Load environment variables
load_dotenv()

app = FastAPI(title="C.L.E.O. Backend API", version="1.0.0")

# CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://localhost:5173",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:5173",
        "http://localhost:3000",  # Common React dev port
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
liquidity_monitor = None
ai_agent = None
data_pipeline = None
mcp_client = None
x402_executor = None
pipeline_executor = None

# Multi-agent system orchestrator
orchestrator = None

# Multi-leg transaction services
multi_leg_coordinator = None
batching_service = None
reconciliation_service = None
db_session = None

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global liquidity_monitor, ai_agent, data_pipeline, mcp_client, x402_executor, orchestrator, pipeline_executor
    
    cronos_rpc = os.getenv("CRONOS_RPC", "https://evm-t3.cronos.org")
    liquidity_monitor = LiquidityMonitor(cronos_rpc)
    
    # Initialize MCP client
    mcp_client = MCPClient()
    
    # Initialize AI agent with MCP client
    ai_agent = RouteOptimizerAgent(
        liquidity_monitor=liquidity_monitor,
        mcp_client=mcp_client
    )
    data_pipeline = DataPipeline()
    
    # Initialize x402 executor (optional, requires contract deployment)
    router_address = os.getenv("ROUTER_CONTRACT_ADDRESS")
    private_key = os.getenv("EXECUTOR_PRIVATE_KEY")  # Should be secure in production
    if router_address:
        try:
            x402_executor = X402Executor(
                rpc_url=cronos_rpc,
                router_contract_address=router_address,
                private_key=private_key
            )
        except Exception as e:
            print(f"Warning: Could not initialize x402 executor: {e}")
    
    # Initialize pipeline executor (optional, requires contract deployment)
    from ai.pipeline_executor import PipelineExecutor
    pipeline_contract_address = os.getenv("SETTLEMENT_PIPELINE_CONTRACT")
    if pipeline_contract_address and pipeline_contract_address != "0x0000000000000000000000000000000000000000":
        try:
            w3 = Web3(Web3.HTTPProvider(cronos_rpc))
            pipeline_abi = [
                {
                    "inputs": [{"internalType": "bytes32", "name": "pipelineId", "type": "bytes32"}],
                    "name": "executePipeline",
                    "outputs": [],
                    "stateMutability": "nonpayable",
                    "type": "function"
                }
            ]
            pipeline_executor = PipelineExecutor(w3, pipeline_contract_address, pipeline_abi)
            print("Pipeline executor initialized")
        except Exception as e:
            print(f"Warning: Could not initialize pipeline executor: {e}")
            pipeline_executor = None
    else:
        print("Pipeline executor not initialized (SETTLEMENT_PIPELINE_CONTRACT not set)")
        pipeline_executor = None
    
    # Initialize multi-agent system orchestrator (optional)
    if HAS_MULTI_AGENT:
        x402_facilitator = os.getenv("X402_FACILITATOR")
        orchestrator_private_key = os.getenv("ORCHESTRATOR_PRIVATE_KEY")
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        
        if orchestrator_private_key and x402_facilitator:
            try:
                orchestrator = OrchestratorAgent(
                    cronos_rpc=cronos_rpc,
                    private_key=orchestrator_private_key,
                    x402_facilitator=x402_facilitator,
                    redis_url=redis_url
                )
                message_bus.register_agent(orchestrator)
                await orchestrator.start()
                print("Multi-agent system orchestrator started")
            except Exception as e:
                print(f"Warning: Could not initialize multi-agent orchestrator: {e}")
                orchestrator = None
        else:
            print("Multi-agent system not initialized (missing ORCHESTRATOR_PRIVATE_KEY or X402_FACILITATOR)")
            orchestrator = None
    else:
        print("Multi-agent system not available (agents module not found)")
        orchestrator = None
    
    # Initialize multi-leg transaction services
    if HAS_MULTI_LEG:
        try:
            database_url = os.getenv('DATABASE_URL', 'sqlite:///./cleo_data.db')
            engine = create_engine(database_url, echo=False)
            Base.metadata.create_all(engine)
            Session = sessionmaker(bind=engine)
            db_session = Session()
            
            w3 = Web3(Web3.HTTPProvider(cronos_rpc))
            multi_leg_coordinator = MultiLegCoordinator(
                db_session=db_session,
                w3=w3,
                compensation_strategy=CompensationStrategy.SAGA
            )
            
            batching_service = BatchingService(
                db_session=db_session,
                w3=w3
            )
            
            reconciliation_service = ReconciliationService(
                db_session=db_session,
                w3=w3
            )
            
            print("Multi-leg transaction services initialized")
        except Exception as e:
            print(f"Warning: Could not initialize multi-leg services: {e}")
            multi_leg_coordinator = None
            batching_service = None
            reconciliation_service = None

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global mcp_client, orchestrator
    if mcp_client:
        await mcp_client.close()
    if orchestrator:
        await orchestrator.stop()

# -------------------- Request/Response Models --------------------

class OptimizeRequest(BaseModel):
    token_in: str
    token_out: str
    amount_in: float
    max_slippage: float = 0.005

class PoolInfo(BaseModel):
    dex: str
    pair: str
    reserveIn: float
    reserveOut: float
    feeBps: int
    address: Optional[str] = None

class SplitRoute(BaseModel):
    id: str
    dex: str
    amountIn: float
    estimatedOut: float
    path: List[str]
    pool_address: Optional[str] = None

class SimulationResult(BaseModel):
    totalIn: float
    totalOut: float
    slippagePct: float
    gasEstimate: int
    routeBreakdown: List[SplitRoute]

class OptimizeResponse(BaseModel):
    optimized_split: Dict
    routes: List[SplitRoute]
    predicted_improvement: float
    risk_metrics: Dict

# Pipeline Models
class RouteSplitRequest(BaseModel):
    router: str
    path: List[str]
    amountIn: int
    minAmountOut: int

class CrossDEXSettlementRequest(BaseModel):
    creator: str
    routes: List[RouteSplitRequest]
    tokenIn: str
    tokenOut: str
    totalAmountIn: int
    minTotalOut: int
    deadline: int

class InvoicePaymentRequest(BaseModel):
    creator: str
    invoiceId: int
    currency: str
    amount: int
    recipient: str
    deliveryTokenId: int
    deliveryNFT: str
    receiptNFT: str

class YieldHarvestRequest(BaseModel):
    creator: str
    farmAddress: str
    rewardToken: str
    lpToken: str
    token0: str
    token1: str
    router: str
    minRewardThreshold: int

class PipelineResponse(BaseModel):
    pipeline_id: str
    pipeline_type: str
    status: str
    created_at: int
    deadline: int
    min_total_out: int
    steps_count: int

class PipelineExecutionRequest(BaseModel):
    pipeline_id: str
    private_key: Optional[str] = None  # In production, use secure key management

class RecurringPipelineRequest(BaseModel):
    pipeline_id: str
    interval_seconds: int
    max_executions: int

# -------------------- API Endpoints --------------------

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "service": "C.L.E.O. Backend API"}

@app.get("/health")
async def health():
    """Health check with service status"""
    return {
        "status": "healthy",
        "services": {
            "liquidity_monitor": liquidity_monitor is not None,
            "ai_agent": ai_agent is not None,
            "data_pipeline": data_pipeline is not None,
            "mcp_client": mcp_client is not None,
            "x402_executor": x402_executor is not None,
        }
    }

@app.get("/api/pools/{token_in}/{token_out}")
async def get_pools(token_in: str, token_out: str):
    """Get available pools for a token pair"""
    try:
        if not liquidity_monitor:
            raise HTTPException(status_code=503, detail="Liquidity monitor not initialized")
        
        pools = await liquidity_monitor.get_all_pools_for_pair(token_in, token_out)
        
        # Convert to frontend format
        pool_list = []
        for pool in pools:
            pool_list.append({
                "dex": pool.get("dex", "Unknown"),
                "pair": f"{token_in}-{token_out}",
                "reserveIn": float(pool.get("reserve0", 0)),
                "reserveOut": float(pool.get("reserve1", 0)),
                "feeBps": pool.get("feeBps", 30),
                "address": pool.get("id"),
            })
        
        return {"pools": pool_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/optimize", response_model=OptimizeResponse)
async def optimize_routes(request: OptimizeRequest):
    """Optimize route splits using AI agent"""
    try:
        if not ai_agent:
            raise HTTPException(status_code=503, detail="AI agent not initialized")
        
        # Call AI agent optimization
        result = await ai_agent.optimize_split(
            token_in=request.token_in,
            token_out=request.token_out,
            amount_in=request.amount_in,
            max_slippage=request.max_slippage
        )
        
        # Convert to frontend format
        routes = []
        optimized_split = result.get("optimized_split", {})
        splits = optimized_split.get("splits", [])
        
        for i, split in enumerate(splits):
            routes.append({
                "id": f"r_{i}",
                "dex": split.get("dex", "Unknown"),
                "amountIn": float(split.get("amount", 0)),
                "estimatedOut": float(split.get("predicted_output", 0)),
                "path": [request.token_in, request.token_out],
                "pool_address": split.get("pool"),
            })
        
        return OptimizeResponse(
            optimized_split=optimized_split,
            routes=routes,
            predicted_improvement=result.get("predicted_improvement", 0.0),
            risk_metrics=result.get("risk_metrics", {})
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/simulate", response_model=SimulationResult)
async def simulate_execution(routes: List[SplitRoute]):
    """Simulate execution of routes with advanced AMM calculations"""
    try:
        from transaction_simulator import TransactionSimulator
        
        if not ai_agent:
            raise HTTPException(status_code=503, detail="AI agent not initialized")
        
        cronos_rpc = os.getenv("CRONOS_RPC", "https://evm-t3.cronos.org")
        simulator = TransactionSimulator(cronos_rpc)
        
        # Get pool data for simulation
        if routes:
            token_in = routes[0].path[0] if routes[0].path else "CRO"
            token_out = routes[0].path[-1] if routes[0].path else "USDC.e"
            
            pools = await liquidity_monitor.get_all_pools_for_pair(token_in, token_out) if liquidity_monitor else []
            
            # Convert routes to simulator format
            sim_routes = [
                {
                    "dexId": r.dex.lower().replace(" ", "_"),
                    "amountIn": r.amountIn,
                    "path": r.path
                }
                for r in routes
            ]
            
            # Run simulation
            sim_result = await simulator.simulate_multi_route_swap(sim_routes, pools)
            
            # Estimate gas
            gas_estimate = simulator.estimate_gas_cost(len(routes))
            
            return SimulationResult(
                totalIn=sim_result["total_in"],
                totalOut=sim_result["total_out"],
                slippagePct=sim_result["overall_slippage_pct"],
                gasEstimate=gas_estimate["total_gas"],
                routeBreakdown=routes
            )
        else:
            # Fallback to simple calculation
            total_in = sum(r.amountIn for r in routes)
            total_out = sum(r.estimatedOut for r in routes)
            slippage_pct = abs((total_out / total_in - 1) * 100) if total_in > 0 else 0.0
            gas_estimate = 120000 + len(routes) * 12000
            
            return SimulationResult(
                totalIn=total_in,
                totalOut=total_out,
                slippagePct=slippage_pct,
                gasEstimate=gas_estimate,
                routeBreakdown=routes
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/liquidity/{pair}")
async def get_liquidity_data(pair: str):
    """Get liquidity data for a trading pair"""
    try:
        if not mcp_client:
            raise HTTPException(status_code=503, detail="MCP client not initialized")
        
        liquidity_data = await mcp_client.get_liquidity_data(pair)
        market_summary = await mcp_client.get_market_summary(pair)
        volatility_data = await mcp_client.get_historical_volatility(pair)
        
        return {
            "pair": pair,
            "total_liquidity_usd": liquidity_data.get("total_liquidity_usd", 0),
            "volatility": volatility_data.get("volatility", 0.0),
            "spread_bps": liquidity_data.get("spread_bps", 0),
            "current_price": market_summary.get("current_price", 0),
            "timestamp": liquidity_data.get("timestamp")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/execute")
async def execute_swap(request: OptimizeRequest):
    """Execute optimized swap through x402 router"""
    try:
        if not x402_executor:
            raise HTTPException(
                status_code=503,
                detail="x402 executor not initialized. Contract deployment required."
            )
        
        if not ai_agent:
            raise HTTPException(status_code=503, detail="AI agent not initialized")
        
        # Step 1: Get optimization
        optimization_result = await ai_agent.optimize_split(
            token_in=request.token_in,
            token_out=request.token_out,
            amount_in=request.amount_in,
            max_slippage=request.max_slippage
        )
        
        # Step 2: Prepare routes for contract
        routes = await x402_executor.prepare_route_splits(
            optimized_split=optimization_result.get("optimized_split", {}),
            token_in_address=request.token_in,
            token_out_address=request.token_out
        )
        
        # Step 3: Calculate minimum output
        total_predicted_out = sum(
            float(split.get("predicted_output", 0))
            for split in optimization_result.get("optimized_split", {}).get("splits", [])
        )
        min_total_out = total_predicted_out * (1 - request.max_slippage)
        
        # Step 4: Execute
        execution_result = await x402_executor.execute_swap(
            routes=routes,
            total_amount_in=request.amount_in,
            token_in=request.token_in,
            token_out=request.token_out,
            min_total_out=total_predicted_out,
            max_slippage=request.max_slippage
        )
        
        return {
            "optimization": optimization_result,
            "execution": execution_result,
            "routes": routes
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/order/{order_id}")
async def get_order_status(order_id: str):
    """Get status of an executed order"""
    try:
        if not x402_executor:
            raise HTTPException(status_code=503, detail="x402 executor not initialized")
        
        order_status = await x402_executor.check_order_status(order_id)
        return order_status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== Multi-Agent System Endpoints ====================

@app.post("/api/multi-agent/execute")
async def execute_swap_multi_agent(request: OptimizeRequest):
    """Execute swap using multi-agent system"""
    try:
        if not orchestrator:
            raise HTTPException(
                status_code=503,
                detail="Multi-agent orchestrator not initialized. Set ORCHESTRATOR_PRIVATE_KEY and X402_FACILITATOR environment variables."
            )
        
        result = await orchestrator.execute_swap(
            token_in=request.token_in,
            token_out=request.token_out,
            amount_in=Decimal(str(request.amount_in)),
            max_slippage=Decimal(str(request.max_slippage)),
            strategy="ai_optimized"
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/multi-agent/status")
async def get_multi_agent_status():
    """Get multi-agent system status"""
    try:
        if not orchestrator:
            return {
                "status": "not_initialized",
                "message": "Multi-agent system not initialized"
            }
        
        # Request status from orchestrator
        from agents.message_bus import AgentMessage
        status_msg = AgentMessage(
            message_id=f"status_req_{datetime.now().timestamp()}",
            sender="api",
            receiver="orchestrator",
            message_type="system_status",
            payload={}
        )
        await orchestrator.receive_message(status_msg)
        
        # Wait for response (simplified - in production use proper async waiting)
        await asyncio.sleep(0.5)
        
        return {
            "status": "running",
            "orchestrator": orchestrator.is_running,
            "active_requests": len(orchestrator.active_requests)
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

@app.get("/api/multi-agent/request/{request_id}")
async def get_request_status(request_id: str):
    """Get status of a swap request"""
    try:
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Multi-agent orchestrator not initialized")
        
        if request_id not in orchestrator.active_requests:
            raise HTTPException(status_code=404, detail="Request not found")
        
        request_data = orchestrator.active_requests[request_id]
        return request_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== Pipeline Endpoints ====================

@app.post("/api/pipelines/cross-dex-settlement", response_model=PipelineResponse)
async def create_cross_dex_settlement(request: CrossDEXSettlementRequest):
    """Create a cross-DEX settlement pipeline"""
    try:
        if not pipeline_executor:
            raise HTTPException(status_code=503, detail="Pipeline executor not initialized")
        
        # Convert routes to dict format
        routes = [
            {
                "router": r.router,
                "path": r.path,
                "amountIn": r.amountIn,
                "minAmountOut": r.minAmountOut
            }
            for r in request.routes
        ]
        
        pipeline_id = await pipeline_executor.create_cross_dex_settlement(
            creator=request.creator,
            routes=routes,
            token_in=request.tokenIn,
            token_out=request.tokenOut,
            total_amount_in=request.totalAmountIn,
            min_total_out=request.minTotalOut,
            deadline=request.deadline
        )
        
        pipeline = pipeline_executor.get_pipeline(pipeline_id)
        
        return PipelineResponse(
            pipeline_id=pipeline_id,
            pipeline_type=pipeline.pipeline_type.value,
            status=pipeline.status.value,
            created_at=pipeline.created_at,
            deadline=pipeline.deadline,
            min_total_out=pipeline.min_total_out,
            steps_count=len(pipeline.steps)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/pipelines/invoice-payment", response_model=PipelineResponse)
async def create_invoice_payment(request: InvoicePaymentRequest):
    """Create an invoice payment pipeline"""
    try:
        if not pipeline_executor:
            raise HTTPException(status_code=503, detail="Pipeline executor not initialized")
        
        pipeline_id = await pipeline_executor.create_invoice_payment(
            creator=request.creator,
            invoice_id=request.invoiceId,
            currency=request.currency,
            amount=request.amount,
            recipient=request.recipient,
            delivery_token_id=request.deliveryTokenId,
            delivery_nft=request.deliveryNFT,
            receipt_nft=request.receiptNFT
        )
        
        pipeline = pipeline_executor.get_pipeline(pipeline_id)
        
        return PipelineResponse(
            pipeline_id=pipeline_id,
            pipeline_type=pipeline.pipeline_type.value,
            status=pipeline.status.value,
            created_at=pipeline.created_at,
            deadline=pipeline.deadline,
            min_total_out=pipeline.min_total_out,
            steps_count=len(pipeline.steps)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/pipelines/yield-harvest", response_model=PipelineResponse)
async def create_yield_harvest(request: YieldHarvestRequest):
    """Create a yield harvest + compound pipeline"""
    try:
        if not pipeline_executor:
            raise HTTPException(status_code=503, detail="Pipeline executor not initialized")
        
        pipeline_id = await pipeline_executor.create_yield_harvest(
            creator=request.creator,
            farm_address=request.farmAddress,
            reward_token=request.rewardToken,
            lp_token=request.lpToken,
            token0=request.token0,
            token1=request.token1,
            router=request.router,
            min_reward_threshold=request.minRewardThreshold
        )
        
        pipeline = pipeline_executor.get_pipeline(pipeline_id)
        
        return PipelineResponse(
            pipeline_id=pipeline_id,
            pipeline_type=pipeline.pipeline_type.value,
            status=pipeline.status.value,
            created_at=pipeline.created_at,
            deadline=pipeline.deadline,
            min_total_out=pipeline.min_total_out,
            steps_count=len(pipeline.steps)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/pipelines/{pipeline_id}/validate")
async def validate_pipeline(pipeline_id: str):
    """Validate a pipeline before execution"""
    try:
        if not pipeline_executor:
            raise HTTPException(status_code=503, detail="Pipeline executor not initialized")
        
        result = await pipeline_executor.validate_pipeline(pipeline_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/pipelines/{pipeline_id}/simulate")
async def simulate_pipeline(pipeline_id: str):
    """Simulate pipeline execution"""
    try:
        if not pipeline_executor:
            raise HTTPException(status_code=503, detail="Pipeline executor not initialized")
        
        result = await pipeline_executor.simulate_pipeline(pipeline_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/pipelines/{pipeline_id}/execute")
async def execute_pipeline(pipeline_id: str, request: PipelineExecutionRequest):
    """Execute a pipeline on-chain"""
    try:
        if not pipeline_executor:
            raise HTTPException(status_code=503, detail="Pipeline executor not initialized")
        
        if not request.private_key:
            raise HTTPException(status_code=400, detail="Private key required for execution")
        
        result = await pipeline_executor.execute_pipeline(
            pipeline_id=pipeline_id,
            private_key=request.private_key
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/pipelines/{pipeline_id}")
async def get_pipeline(pipeline_id: str):
    """Get pipeline details"""
    try:
        if not pipeline_executor:
            raise HTTPException(status_code=503, detail="Pipeline executor not initialized")
        
        pipeline = pipeline_executor.get_pipeline(pipeline_id)
        if not pipeline:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        
        return {
            "pipeline_id": pipeline.pipeline_id,
            "pipeline_type": pipeline.pipeline_type.value,
            "creator": pipeline.creator,
            "status": pipeline.status.value,
            "created_at": pipeline.created_at,
            "executed_at": pipeline.executed_at,
            "deadline": pipeline.deadline,
            "min_total_out": pipeline.min_total_out,
            "steps_count": len(pipeline.steps),
            "tx_hash": pipeline.tx_hash,
            "error": pipeline.error
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/pipelines/user/{user_address}")
async def get_user_pipelines(user_address: str):
    """Get all pipelines for a user"""
    try:
        if not pipeline_executor:
            raise HTTPException(status_code=503, detail="Pipeline executor not initialized")
        
        pipelines = pipeline_executor.get_user_pipelines(user_address)
        
        return [
            {
                "pipeline_id": p.pipeline_id,
                "pipeline_type": p.pipeline_type.value,
                "status": p.status.value,
                "created_at": p.created_at,
                "deadline": p.deadline,
                "min_total_out": p.min_total_out,
                "steps_count": len(p.steps)
            }
            for p in pipelines
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/pipelines/{pipeline_id}/schedule-recurring")
async def schedule_recurring_pipeline(
    pipeline_id: str,
    request: RecurringPipelineRequest
):
    """Schedule a pipeline for recurring execution"""
    try:
        if not pipeline_executor:
            raise HTTPException(status_code=503, detail="Pipeline executor not initialized")
        
        result = await pipeline_executor.schedule_recurring_pipeline(
            pipeline_id=pipeline_id,
            interval_seconds=request.interval_seconds,
            max_executions=request.max_executions
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== Multi-Agent System V2 Endpoints ====================

class MultiAgentSwapRequest(BaseModel):
    """Request model for multi-agent swap"""
    token_in: str
    token_out: str
    amount_in: float
    max_slippage: float = 0.05
    strategy: str = "ai_optimized"

@app.post("/api/v2/swap")
async def execute_multi_agent_swap(request: MultiAgentSwapRequest):
    """Execute swap using multi-agent system (v2 endpoint)"""
    try:
        if not orchestrator:
            raise HTTPException(
                status_code=503, 
                detail="Multi-agent system not available"
            )
        
        result = await orchestrator.execute_swap(
            token_in=request.token_in,
            token_out=request.token_out,
            amount_in=Decimal(str(request.amount_in)),
            max_slippage=Decimal(str(request.max_slippage)),
            strategy=request.strategy
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v2/system-status")
async def get_multi_agent_status_v2():
    """Get multi-agent system status (v2 endpoint)"""
    try:
        if not orchestrator:
            return {
                "available": False,
                "message": "Multi-agent system not initialized"
            }
        
        # Return basic status
        return {
            "available": True,
            "orchestrator_running": orchestrator.is_running if orchestrator else False,
            "active_requests": len(orchestrator.active_requests) if orchestrator else 0
        }
    except Exception as e:
        return {
            "available": orchestrator is not None,
                "error": str(e)
            }

# ==================== Multi-Leg Transaction Endpoints ====================

class LegDefinition(BaseModel):
    """Definition of a transaction leg"""
    type: str  # "debit", "credit", "swap", "transfer", etc.
    target_address: Optional[str] = None
    function_name: Optional[str] = None
    function_data: Optional[str] = None
    amount_in: Optional[str] = None
    amount_out: Optional[str] = None
    token_in: Optional[str] = None
    token_out: Optional[str] = None
    requires_compensation: bool = False
    metadata: Optional[Dict] = None

class CreateMultiLegTransactionRequest(BaseModel):
    """Request to create a multi-leg transaction"""
    transaction_type: str
    initiator: str
    legs: List[LegDefinition]
    idempotency_key: Optional[str] = None
    deadline: Optional[int] = None  # Unix timestamp
    metadata: Optional[Dict] = None

class ExecuteTransactionRequest(BaseModel):
    """Request to execute a transaction"""
    transaction_id: str
    atomic: bool = True

class BatchRequest(BaseModel):
    """Request to add item to batch"""
    transaction_id: Optional[str] = None
    leg_id: Optional[str] = None
    batch_type: str = "time_window"
    strategy: str = "time_window"
    time_window_seconds: Optional[int] = 60
    max_size: Optional[int] = 100
    metadata: Optional[Dict] = None

@app.post("/api/multi-leg/create")
async def create_multi_leg_transaction(request: CreateMultiLegTransactionRequest):
    """Create a new multi-leg transaction"""
    try:
        if not multi_leg_coordinator:
            raise HTTPException(status_code=503, detail="Multi-leg coordinator not initialized")
        
        # Convert legs
        legs = []
        for leg_def in request.legs:
            legs.append({
                "type": leg_def.type,
                "target_address": leg_def.target_address,
                "function_name": leg_def.function_name,
                "function_data": leg_def.function_data,
                "amount_in": leg_def.amount_in,
                "amount_out": leg_def.amount_out,
                "token_in": leg_def.token_in,
                "token_out": leg_def.token_out,
                "requires_compensation": leg_def.requires_compensation,
                "metadata": leg_def.metadata or {}
            })
        
        deadline = None
        if request.deadline:
            deadline = datetime.fromtimestamp(request.deadline)
        
        transaction = multi_leg_coordinator.create_transaction(
            transaction_type=request.transaction_type,
            initiator=request.initiator,
            legs=legs,
            idempotency_key=request.idempotency_key,
            deadline=deadline,
            metadata=request.metadata
        )
        
        return transaction.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/multi-leg/execute")
async def execute_multi_leg_transaction(request: ExecuteTransactionRequest):
    """Execute a multi-leg transaction"""
    try:
        if not multi_leg_coordinator:
            raise HTTPException(status_code=503, detail="Multi-leg coordinator not initialized")
        
        result = await multi_leg_coordinator.execute_transaction(
            transaction_id=request.transaction_id,
            atomic=request.atomic
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/multi-leg/{transaction_id}")
async def get_multi_leg_transaction(transaction_id: str):
    """Get multi-leg transaction details"""
    try:
        if not multi_leg_coordinator:
            raise HTTPException(status_code=503, detail="Multi-leg coordinator not initialized")
        
        transaction = multi_leg_coordinator.get_transaction(transaction_id)
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        legs = multi_leg_coordinator.get_transaction_legs(transaction_id)
        
        return {
            "transaction": transaction.to_dict(),
            "legs": [leg.to_dict() for leg in legs]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/batching/add")
async def add_to_batch(request: BatchRequest):
    """Add transaction or leg to batch"""
    try:
        if not batching_service:
            raise HTTPException(status_code=503, detail="Batching service not initialized")
        
        strategy = BatchingStrategy(request.strategy)
        
        batch_id = batching_service.add_to_batch(
            transaction_id=request.transaction_id,
            leg_id=None,  # Could be added from request
            batch_type=request.batch_type,
            strategy=strategy,
            time_window_seconds=request.time_window_seconds,
            max_size=request.max_size,
            metadata=request.metadata
        )
        
        return {
            "batch_id": batch_id,
            "status": "added"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/batching/{batch_id}/execute")
async def execute_batch(batch_id: str):
    """Execute a batch"""
    try:
        if not batching_service:
            raise HTTPException(status_code=503, detail="Batching service not initialized")
        
        result = await batching_service.execute_batch(batch_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/batching/{batch_id}")
async def get_batch(batch_id: str):
    """Get batch details"""
    try:
        if not batching_service:
            raise HTTPException(status_code=503, detail="Batching service not initialized")
        
        batch = batching_service.get_batch(batch_id)
        if not batch:
            raise HTTPException(status_code=404, detail="Batch not found")
        
        return batch.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/batching/pending")
async def get_pending_batches(strategy: Optional[str] = None):
    """Get pending batches"""
    try:
        if not batching_service:
            raise HTTPException(status_code=503, detail="Batching service not initialized")
        
        batching_strategy = BatchingStrategy(strategy) if strategy else None
        batches = batching_service.get_pending_batches(batching_strategy)
        
        return {
            "batches": [batch.to_dict() for batch in batches]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/reconciliation/{transaction_id}")
async def reconcile_transaction(transaction_id: str, on_chain_tx_hash: Optional[str] = None):
    """Reconcile a transaction"""
    try:
        if not reconciliation_service:
            raise HTTPException(status_code=503, detail="Reconciliation service not initialized")
        
        result = await reconciliation_service.reconcile_transaction(
            transaction_id=transaction_id,
            on_chain_tx_hash=on_chain_tx_hash
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reconciliation/records")
async def get_reconciliation_records(
    transaction_id: Optional[str] = None,
    status: Optional[str] = None
):
    """Get reconciliation records"""
    try:
        if not reconciliation_service:
            raise HTTPException(status_code=503, detail="Reconciliation service not initialized")
        
        records = reconciliation_service.get_reconciliation_records(
            transaction_id=transaction_id,
            status=status
        )
        
        return {
            "records": [record.to_dict() for record in records]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== Dashboard & Metrics Endpoints ====================

@app.get("/api/metrics/dashboard")
async def get_dashboard_metrics():
    """Get dashboard metrics and statistics"""
    try:
        # Try to get real metrics if available
        try:
            from performance_metrics import performance_tracker
            dashboard = performance_tracker.get_performance_dashboard()
            return dashboard
        except ImportError:
            # Return mock data if performance tracker not available
            return {
                "total_volume_usd": 1200000,
                "total_executions": 342,
                "avg_savings_pct": 2.4,
                "agent_status": "active",
                "success_rate": 98.5,
                "avg_gas_efficiency": 0.95,
                "recent_executions": [
                    {
                        "id": f"exec_{i}",
                        "timestamp": int(datetime.now().timestamp()) - (i * 120),
                        "token_in": "CRO",
                        "token_out": "USDC.e",
                        "amount_in": 100000 - (i * 1000),
                        "amount_out": 50000 - (i * 500),
                        "savings_pct": 2.1 + (i * 0.1),
                        "status": "success"
                    }
                    for i in range(5)
                ]
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/agent/status")
async def get_agent_status():
    """Get AI agent status and statistics"""
    try:
        if not orchestrator:
            return {
                "status": "offline",
                "available": False,
                "decisions_today": 0,
                "avg_response_time_ms": 0,
                "recent_decisions": []
            }
        
        # Get orchestrator status
        status = {
            "status": "online" if orchestrator.is_running else "offline",
            "available": orchestrator.is_running,
            "active_requests": len(orchestrator.active_requests) if orchestrator else 0,
            "decisions_today": len(orchestrator.active_requests) if orchestrator else 0,
            "avg_response_time_ms": 145,  # Would come from actual metrics
            "recent_decisions": [
                {
                    "id": f"decision_{i}",
                    "timestamp": int(datetime.now().timestamp()) - (i * 120),
                    "route": "VVS 60% / CronaSwap 40%",
                    "details": "100,000 CRO → USDC.e • 2.1% savings",
                    "status": "success"
                }
                for i in range(3)
            ]
        }
        return status
    except Exception as e:
        return {
            "status": "error",
            "available": False,
            "error": str(e)
        }

@app.get("/api/executions/recent")
async def get_recent_executions(limit: int = 10):
    """Get recent execution history"""
    try:
        # Mock data - in production would come from database
        return {
            "executions": [
                {
                    "id": f"exec_{i}",
                    "timestamp": int(datetime.now().timestamp()) - (i * 300),
                    "token_in": "CRO",
                    "token_out": "USDC.e",
                    "amount_in": 100000 - (i * 1000),
                    "amount_out": 50000 - (i * 500),
                    "savings_pct": 2.1 + (i * 0.1),
                    "status": "success",
                    "tx_hash": f"0x{'0' * 64}"
                }
                for i in range(min(limit, 10))
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

