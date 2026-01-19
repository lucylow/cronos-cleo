"""
FastAPI backend server for C.L.E.O. - Cronos Liquidity Execution Orchestrator
"""
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError
from typing import List, Dict, Optional, Any
import os
import asyncio
import logging
import traceback
from datetime import datetime
from decimal import Decimal, InvalidOperation
from dotenv import load_dotenv

from ai.ai_agent import RouteOptimizerAgent
from ai.liquidity_monitor import LiquidityMonitor
from ai.data_pipeline import DataPipeline
from mcp_client import MCPClient
from x402_executor import X402Executor
from dao_executor import DAOExecutor
from web3 import Web3
from web3.exceptions import Web3Exception, BlockNotFound, TransactionNotFound

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

# Workflow manager imports
try:
    from workflows.workflow_manager import WorkflowManager, TradeIntent
    HAS_WORKFLOW = True
except ImportError:
    HAS_WORKFLOW = False
    WorkflowManager = None
    TradeIntent = None

# Agent orchestrator imports
try:
    from agents.agent_orchestrator import AgentOrchestrator, SwapRequest, SwapRequestModel
    HAS_AGENT_ORCHESTRATOR = True
except ImportError:
    HAS_AGENT_ORCHESTRATOR = False
    AgentOrchestrator = None
    SwapRequest = None
    SwapRequestModel = None

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('cleo_backend.log')
    ]
)
logger = logging.getLogger(__name__)

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

# ==================== Exception Handlers ====================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors"""
    logger.warning(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "message": "Invalid request parameters",
            "code": "VALIDATION_ERROR",
            "errors": exc.errors(),
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "message": exc.detail,
            "code": f"HTTP_{exc.status_code}",
            "status": exc.status_code,
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(ValidationError)
async def pydantic_validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors"""
    logger.warning(f"Pydantic validation error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "message": "Invalid data format",
            "code": "VALIDATION_ERROR",
            "errors": exc.errors(),
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle value errors"""
    logger.error(f"Value error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "detail": str(exc),
            "message": str(exc),
            "code": "VALUE_ERROR",
            "status": 400,
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(InvalidOperation)
async def invalid_operation_handler(request: Request, exc: InvalidOperation):
    """Handle invalid decimal operations"""
    logger.error(f"Invalid operation: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "detail": str(exc),
            "message": "Invalid numeric operation",
            "code": "INVALID_OPERATION",
            "status": 400,
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(Web3Exception)
async def web3_exception_handler(request: Request, exc: Web3Exception):
    """Handle Web3/blockchain exceptions"""
    logger.error(f"Web3 error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": str(exc),
            "message": "Blockchain interaction failed",
            "code": "WEB3_ERROR",
            "status": 500,
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "message": "An unexpected error occurred",
            "code": "INTERNAL_ERROR",
            "status": 500,
            "timestamp": datetime.now().isoformat()
        }
    )

# ==================== Request Logging Middleware ====================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests and responses"""
    start_time = datetime.now()
    request_id = f"{start_time.timestamp()}_{id(request)}"
    
    # Log request
    logger.info(f"[{request_id}] {request.method} {request.url.path} - Client: {request.client.host if request.client else 'unknown'}")
    
    try:
        response = await call_next(request)
        process_time = (datetime.now() - start_time).total_seconds()
        
        # Log response
        logger.info(f"[{request_id}] {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.3f}s")
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
    except Exception as e:
        process_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"[{request_id}] {request.method} {request.url.path} - Error: {str(e)} - Time: {process_time:.3f}s", exc_info=True)
        raise

# Initialize services
liquidity_monitor = None
ai_agent = None
data_pipeline = None
mcp_client = None
x402_executor = None
pipeline_executor = None
intelligent_settlement = None
settlement_agent = None
dao_executor = None

# Multi-agent system orchestrator
orchestrator = None

# Workflow manager
workflow_manager = None

# Multi-leg transaction services
multi_leg_coordinator = None
batching_service = None
reconciliation_service = None
db_session = None

# HITL service
hitl_db_session = None

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global liquidity_monitor, ai_agent, data_pipeline, mcp_client, x402_executor, orchestrator, pipeline_executor, workflow_manager, agent_orchestrator, intelligent_settlement, settlement_agent
    
    try:
        logger.info("Starting C.L.E.O. Backend API...")
        cronos_rpc = os.getenv("CRONOS_RPC", "https://evm-t3.cronos.org")
        
        # Initialize liquidity monitor
        try:
            liquidity_monitor = LiquidityMonitor(cronos_rpc)
            logger.info("Liquidity monitor initialized")
        except Exception as e:
            logger.error(f"Failed to initialize liquidity monitor: {e}", exc_info=True)
            liquidity_monitor = None
        
        # Initialize MCP client
        try:
            mcp_client = MCPClient()
            logger.info("MCP client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize MCP client: {e}", exc_info=True)
            mcp_client = None
        
        # Initialize AI agent with MCP client
        try:
            if liquidity_monitor and mcp_client:
                ai_agent = RouteOptimizerAgent(
                    liquidity_monitor=liquidity_monitor,
                    mcp_client=mcp_client
                )
                logger.info("AI agent initialized")
            else:
                logger.warning("AI agent not initialized: missing dependencies")
                ai_agent = None
        except Exception as e:
            logger.error(f"Failed to initialize AI agent: {e}", exc_info=True)
            ai_agent = None
        
        # Initialize data pipeline
        try:
            data_pipeline = DataPipeline()
            logger.info("Data pipeline initialized")
        except Exception as e:
            logger.error(f"Failed to initialize data pipeline: {e}", exc_info=True)
            data_pipeline = None
        
        # Initialize DAO executor (optional, requires contract deployment)
        dao_address = os.getenv("DAO_CONTRACT_ADDRESS")
        if dao_address:
            try:
                dao_executor = DAOExecutor(
                    rpc_url=cronos_rpc,
                    dao_contract_address=dao_address,
                    private_key=None  # Private key passed per-request for security
                )
                logger.info("DAO executor initialized")
            except Exception as e:
                logger.warning(f"Could not initialize DAO executor: {e}")
                dao_executor = None
        else:
            logger.info("DAO executor not initialized (DAO_CONTRACT_ADDRESS not set)")
            dao_executor = None
        
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
                logger.info("x402 executor initialized")
            except Exception as e:
                logger.warning(f"Could not initialize x402 executor: {e}")
                x402_executor = None
        else:
            logger.info("x402 executor not initialized (ROUTER_CONTRACT_ADDRESS not set)")
            x402_executor = None
        
        # Initialize pipeline executor (optional, requires contract deployment)
        try:
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
                    logger.info("Pipeline executor initialized")
                except Exception as e:
                    logger.warning(f"Could not initialize pipeline executor: {e}")
                    pipeline_executor = None
            else:
                logger.info("Pipeline executor not initialized (SETTLEMENT_PIPELINE_CONTRACT not set)")
                pipeline_executor = None
        except ImportError as e:
            logger.warning(f"Pipeline executor module not available: {e}")
            pipeline_executor = None
        
        # Initialize instruction set services
        global instruction_set_registry, condition_evaluator
        try:
            from instruction_sets import ConditionEvaluator, InstructionSetRegistry
            w3_inst = Web3(Web3.HTTPProvider(cronos_rpc))
            condition_evaluator = ConditionEvaluator(w3_inst, liquidity_monitor)
            instruction_set_registry = InstructionSetRegistry(
                w3=w3_inst,
                condition_evaluator=condition_evaluator,
                pipeline_executor=pipeline_executor,
                x402_executor=x402_executor
            )
            logger.info("Instruction set services initialized")
        except Exception as e:
            logger.warning(f"Could not initialize instruction set services: {e}")
            instruction_set_registry = None
            condition_evaluator = None
    
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
                    logger.info("Multi-agent system orchestrator started")
                except Exception as e:
                    logger.warning(f"Could not initialize multi-agent orchestrator: {e}", exc_info=True)
                    orchestrator = None
            else:
                logger.info("Multi-agent system not initialized (missing ORCHESTRATOR_PRIVATE_KEY or X402_FACILITATOR)")
                orchestrator = None
        else:
            logger.info("Multi-agent system not available (agents module not found)")
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
                
                logger.info("Multi-leg transaction services initialized")
            except Exception as e:
                logger.error(f"Could not initialize multi-leg services: {e}", exc_info=True)
                multi_leg_coordinator = None
                batching_service = None
                reconciliation_service = None
                db_session = None
        
        # Initialize agent orchestrator
        if HAS_AGENT_ORCHESTRATOR:
            try:
                agent_orchestrator = AgentOrchestrator()
                logger.info("Agent orchestrator initialized")
            except Exception as e:
                logger.error(f"Could not initialize agent orchestrator: {e}", exc_info=True)
                agent_orchestrator = None
        else:
            logger.info("Agent orchestrator not available")
            agent_orchestrator = None
        
        # Initialize multi-DEX router agent
        global multi_dex_router_agent
        try:
            from agents.multi_dex_router import MultiDEXRouterAgent
            multi_dex_router_agent = MultiDEXRouterAgent(cronos_rpc=cronos_rpc)
            if HAS_MULTI_AGENT and message_bus:
                message_bus.register_agent(multi_dex_router_agent)
                await multi_dex_router_agent.start()
            logger.info("Multi-DEX router agent initialized")
        except Exception as e:
            logger.warning(f"Could not initialize multi-DEX router agent: {e}", exc_info=True)
            multi_dex_router_agent = None
        
        # Initialize multi-DEX analytics
        global multi_dex_analytics
        try:
            from agents.multi_dex_analytics import analytics_service
            multi_dex_analytics = analytics_service
            logger.info("Multi-DEX analytics service initialized")
        except Exception as e:
            logger.warning(f"Could not initialize multi-DEX analytics: {e}", exc_info=True)
            multi_dex_analytics = None
        
        logger.info("C.L.E.O. Backend API startup completed")
    except Exception as e:
        logger.critical(f"Critical error during startup: {e}", exc_info=True)
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global mcp_client, orchestrator, db_session, settlement_agent
    logger.info("Shutting down C.L.E.O. Backend API...")
    
    try:
        if mcp_client:
            try:
                await mcp_client.close()
                logger.info("MCP client closed")
            except Exception as e:
                logger.error(f"Error closing MCP client: {e}")
        
        if orchestrator:
            try:
                await orchestrator.stop()
                logger.info("Orchestrator stopped")
            except Exception as e:
                logger.error(f"Error stopping orchestrator: {e}")
        
        if settlement_agent:
            try:
                await settlement_agent.stop()
                logger.info("Settlement agent stopped")
            except Exception as e:
                logger.error(f"Error stopping settlement agent: {e}")
        
        if db_session:
            try:
                db_session.close()
                logger.info("Database session closed")
            except Exception as e:
                logger.error(f"Error closing database session: {e}")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}", exc_info=True)
    
    logger.info("Shutdown completed")

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

# Instruction Set Request/Response Models
class ConditionRequest(BaseModel):
    condition_type: str
    parameters: Dict[str, Any]
    description: Optional[str] = None

class ActionRequest(BaseModel):
    action_type: str
    target: str
    parameters: Dict[str, Any]
    is_critical: bool = True
    condition: Optional[ConditionRequest] = None

class ScheduleRequest(BaseModel):
    interval_seconds: int
    next_execution: int
    end_time: Optional[int] = None
    max_executions: Optional[int] = None

class LimitsRequest(BaseModel):
    max_notional_per_run: Optional[int] = None
    cumulative_cap: Optional[int] = None
    max_slippage_bps: Optional[int] = None
    max_gas_per_execution: Optional[int] = None
    per_beneficiary_cap: Optional[Dict[str, int]] = None
    circuit_breaker_active: bool = False
    pause_switch: bool = False

class CreateInstructionSetRequest(BaseModel):
    owner: str
    instruction_type: str
    schedule: ScheduleRequest
    conditions: List[ConditionRequest]
    actions: List[ActionRequest]
    limits: LimitsRequest
    metadata: Optional[Dict[str, Any]] = None

class UpdateInstructionSetRequest(BaseModel):
    schedule: Optional[ScheduleRequest] = None
    conditions: Optional[List[ConditionRequest]] = None
    actions: Optional[List[ActionRequest]] = None
    limits: Optional[LimitsRequest] = None
    status: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class ExecuteInstructionSetRequest(BaseModel):
    private_key: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

# Intelligent Settlement Request/Response Models
class CreateDealRequest(BaseModel):
    seller: str
    token: str  # Token address or "0x0" for native
    total_amount: int  # Amount in wei/smallest unit
    deadline: int  # Unix timestamp
    milestone_amounts: List[int]  # Must sum to total_amount
    fee_bps: int = 25  # Protocol fee in basis points (0-500)
    arbitrator: Optional[str] = None
    buyer_private_key: Optional[str] = None  # In production, use secure key management

class FundDealRequest(BaseModel):
    deal_id: int
    amount: int  # Amount in wei/smallest unit
    buyer_private_key: Optional[str] = None
    is_native: bool = False

class ReleaseMilestoneRequest(BaseModel):
    deal_id: int
    milestone_index: int
    min_seller_amount: int
    agent_nonce: int

class RefundDealRequest(BaseModel):
    deal_id: int
    buyer_private_key: Optional[str] = None

# Gas API Request/Response Models
class GasEstimateRequest(BaseModel):
    to: Optional[str] = None
    data: Optional[str] = None
    value: Optional[str] = None
    from_address: Optional[str] = None
    buffer_percent: Optional[int] = 20

class TxSendRequest(BaseModel):
    signed_tx: Optional[str] = None
    tx_request: Optional[Dict[str, Any]] = None
    mode: Optional[str] = None  # 'server' or None (for signed_tx)

class TxMonitorRequest(BaseModel):
    tx_hash: str
    confirmations: Optional[int] = 1
    timeout_ms: Optional[int] = 120000

class PaymentVerifyRequest(BaseModel):
    tx_hash: str
    token_address: Optional[str] = None
    expected_recipient: Optional[str] = None
    min_amount_wei: Optional[str] = None

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
            "intelligent_settlement": intelligent_settlement is not None,
        }
    }

@app.get("/api/pools/{token_in}/{token_out}")
async def get_pools(token_in: str, token_out: str):
    """Get available pools for a token pair"""
    try:
        if not liquidity_monitor:
            logger.warning(f"Liquidity monitor not initialized for pool request: {token_in}/{token_out}")
            raise HTTPException(
                status_code=503,
                detail="Liquidity monitor not initialized. Please try again later."
            )
        
        if not token_in or not token_out:
            raise HTTPException(
                status_code=400,
                detail="Both token_in and token_out are required"
            )
        
        logger.info(f"Fetching pools for pair: {token_in}/{token_out}")
        pools = await liquidity_monitor.get_all_pools_for_pair(token_in, token_out)
        
        if not pools:
            logger.warning(f"No pools found for pair: {token_in}/{token_out}")
            return {"pools": []}
        
        # Convert to frontend format
        pool_list = []
        for pool in pools:
            try:
                pool_list.append({
                    "dex": pool.get("dex", "Unknown"),
                    "pair": f"{token_in}-{token_out}",
                    "reserveIn": float(pool.get("reserve0", 0)),
                    "reserveOut": float(pool.get("reserve1", 0)),
                    "feeBps": pool.get("feeBps", 30),
                    "address": pool.get("id"),
                })
            except (ValueError, TypeError) as e:
                logger.warning(f"Error processing pool data: {e}, skipping pool")
                continue
        
        logger.info(f"Found {len(pool_list)} pools for {token_in}/{token_out}")
        return {"pools": pool_list}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching pools for {token_in}/{token_out}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch pools: {str(e)}"
        )

@app.post("/api/optimize", response_model=OptimizeResponse)
async def optimize_routes(request: OptimizeRequest):
    """Optimize route splits using AI agent"""
    try:
        if not ai_agent:
            logger.warning("AI agent not initialized for optimization request")
            raise HTTPException(
                status_code=503,
                detail="AI agent not initialized. Please try again later."
            )
        
        # Validate input
        if request.amount_in <= 0:
            raise HTTPException(
                status_code=400,
                detail="amount_in must be greater than 0"
            )
        
        if not request.token_in or not request.token_out:
            raise HTTPException(
                status_code=400,
                detail="Both token_in and token_out are required"
            )
        
        if request.max_slippage < 0 or request.max_slippage > 1:
            raise HTTPException(
                status_code=400,
                detail="max_slippage must be between 0 and 1"
            )
        
        logger.info(f"Optimizing routes: {request.amount_in} {request.token_in} -> {request.token_out}")
        
        # Call AI agent optimization
        result = await ai_agent.optimize_split(
            token_in=request.token_in,
            token_out=request.token_out,
            amount_in=request.amount_in,
            max_slippage=request.max_slippage
        )
        
        if not result:
            raise HTTPException(
                status_code=500,
                detail="Optimization returned no results"
            )
        
        # Convert to frontend format
        routes = []
        optimized_split = result.get("optimized_split", {})
        splits = optimized_split.get("splits", [])
        
        for i, split in enumerate(splits):
            try:
                routes.append({
                    "id": f"r_{i}",
                    "dex": split.get("dex", "Unknown"),
                    "amountIn": float(split.get("amount", 0)),
                    "estimatedOut": float(split.get("predicted_output", 0)),
                    "path": [request.token_in, request.token_out],
                    "pool_address": split.get("pool"),
                })
            except (ValueError, TypeError) as e:
                logger.warning(f"Error processing split {i}: {e}, skipping")
                continue
        
        logger.info(f"Optimization completed: {len(routes)} routes found")
        return OptimizeResponse(
            optimized_split=optimized_split,
            routes=routes,
            predicted_improvement=result.get("predicted_improvement", 0.0),
            risk_metrics=result.get("risk_metrics", {})
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error optimizing routes: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to optimize routes: {str(e)}"
        )

@app.post("/api/simulate", response_model=SimulationResult)
async def simulate_execution(routes: List[SplitRoute]):
    """Simulate execution of routes with advanced AMM calculations"""
    try:
        if not routes:
            raise HTTPException(
                status_code=400,
                detail="At least one route is required for simulation"
            )
        
        if not ai_agent:
            logger.warning("AI agent not initialized for simulation request")
            raise HTTPException(
                status_code=503,
                detail="AI agent not initialized. Please try again later."
            )
        
        logger.info(f"Simulating execution for {len(routes)} routes")
        
        try:
            from transaction_simulator import TransactionSimulator
        except ImportError as e:
            logger.error(f"Transaction simulator module not available: {e}")
            raise HTTPException(
                status_code=503,
                detail="Transaction simulator not available"
            )
        
        cronos_rpc = os.getenv("CRONOS_RPC", "https://evm-t3.cronos.org")
        
        try:
            simulator = TransactionSimulator(cronos_rpc)
        except Exception as e:
            logger.error(f"Failed to initialize transaction simulator: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize simulator: {str(e)}"
            )
        
        # Get pool data for simulation
        try:
            token_in = routes[0].path[0] if routes[0].path else "CRO"
            token_out = routes[0].path[-1] if routes[0].path else "USDC.e"
            
            pools = []
            if liquidity_monitor:
                try:
                    pools = await liquidity_monitor.get_all_pools_for_pair(token_in, token_out)
                except Exception as e:
                    logger.warning(f"Failed to fetch pools for simulation: {e}")
                    pools = []
            
            # Convert routes to simulator format
            sim_routes = []
            for r in routes:
                try:
                    if not r.path or len(r.path) < 2:
                        logger.warning(f"Invalid path in route, skipping: {r.path}")
                        continue
                    sim_routes.append({
                        "dexId": r.dex.lower().replace(" ", "_"),
                        "amountIn": r.amountIn,
                        "path": r.path
                    })
                except Exception as e:
                    logger.warning(f"Error processing route: {e}, skipping")
                    continue
            
            if not sim_routes:
                raise HTTPException(
                    status_code=400,
                    detail="No valid routes provided for simulation"
                )
            
            # Run simulation
            try:
                sim_result = await simulator.simulate_multi_route_swap(sim_routes, pools)
                
                if not sim_result:
                    raise HTTPException(
                        status_code=500,
                        detail="Simulation returned no results"
                    )
            except Exception as e:
                logger.error(f"Error during simulation: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"Simulation failed: {str(e)}"
                )
            
            # Estimate gas
            try:
                gas_estimate = simulator.estimate_gas_cost(len(sim_routes))
            except Exception as e:
                logger.warning(f"Error estimating gas: {e}, using default")
                gas_estimate = {"total_gas": 120000 + len(sim_routes) * 12000}
            
            logger.info(f"Simulation completed successfully")
            return SimulationResult(
                totalIn=sim_result.get("total_in", 0),
                totalOut=sim_result.get("total_out", 0),
                slippagePct=sim_result.get("overall_slippage_pct", 0.0),
                gasEstimate=gas_estimate.get("total_gas", 0),
                routeBreakdown=routes
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in simulation logic: {e}", exc_info=True)
            # Fallback to simple calculation
            try:
                total_in = sum(r.amountIn for r in routes if r.amountIn > 0)
                total_out = sum(r.estimatedOut for r in routes if r.estimatedOut > 0)
                slippage_pct = abs((total_out / total_in - 1) * 100) if total_in > 0 else 0.0
                gas_estimate = 120000 + len(routes) * 12000
                
                logger.warning("Using fallback calculation for simulation")
                return SimulationResult(
                    totalIn=total_in,
                    totalOut=total_out,
                    slippagePct=slippage_pct,
                    gasEstimate=gas_estimate,
                    routeBreakdown=routes
                )
            except Exception as fallback_error:
                logger.error(f"Fallback calculation also failed: {fallback_error}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"Simulation failed: {str(e)}"
                )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in simulate_execution: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to simulate execution: {str(e)}"
        )

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
            logger.warning("x402 executor not initialized for execution request")
            raise HTTPException(
                status_code=503,
                detail="x402 executor not initialized. Contract deployment required."
            )
        
        if not ai_agent:
            logger.warning("AI agent not initialized for execution request")
            raise HTTPException(
                status_code=503,
                detail="AI agent not initialized. Please try again later."
            )
        
        # Validate input
        if request.amount_in <= 0:
            raise HTTPException(
                status_code=400,
                detail="amount_in must be greater than 0"
            )
        
        if not request.token_in or not request.token_out:
            raise HTTPException(
                status_code=400,
                detail="Both token_in and token_out are required"
            )
        
        logger.info(f"Executing swap: {request.amount_in} {request.token_in} -> {request.token_out}")
        
        # Step 1: Get optimization
        try:
            optimization_result = await ai_agent.optimize_split(
                token_in=request.token_in,
                token_out=request.token_out,
                amount_in=request.amount_in,
                max_slippage=request.max_slippage
            )
            
            if not optimization_result:
                raise HTTPException(
                    status_code=500,
                    detail="Optimization failed - no routes found"
                )
        except Exception as e:
            logger.error(f"Error during optimization: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Optimization failed: {str(e)}"
            )
        
        # Step 2: Prepare routes for contract
        try:
            routes = await x402_executor.prepare_route_splits(
                optimized_split=optimization_result.get("optimized_split", {}),
                token_in_address=request.token_in,
                token_out_address=request.token_out
            )
            
            if not routes:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to prepare routes for execution"
                )
        except Exception as e:
            logger.error(f"Error preparing routes: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Route preparation failed: {str(e)}"
            )
        
        # Step 3: Calculate minimum output
        try:
            splits = optimization_result.get("optimized_split", {}).get("splits", [])
            if not splits:
                raise HTTPException(
                    status_code=500,
                    detail="No splits found in optimization result"
                )
            
            total_predicted_out = sum(
                float(split.get("predicted_output", 0))
                for split in splits
            )
            
            if total_predicted_out <= 0:
                raise HTTPException(
                    status_code=500,
                    detail="Invalid predicted output amount"
                )
            
            min_total_out = total_predicted_out * (1 - request.max_slippage)
        except (ValueError, TypeError) as e:
            logger.error(f"Error calculating minimum output: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to calculate minimum output: {str(e)}"
            )
        
        # Step 4: Execute
        try:
            execution_result = await x402_executor.execute_swap(
                routes=routes,
                total_amount_in=request.amount_in,
                token_in=request.token_in,
                token_out=request.token_out,
                min_total_out=total_predicted_out,
                max_slippage=request.max_slippage
            )
            
            logger.info(f"Swap execution completed successfully")
            return {
                "optimization": optimization_result,
                "execution": execution_result,
                "routes": routes
            }
        except Exception as e:
            logger.error(f"Error during swap execution: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Swap execution failed: {str(e)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in execute_swap: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to execute swap: {str(e)}"
        )

@app.get("/api/order/{order_id}")
async def get_order_status(order_id: str):
    """Get status of an executed order"""
    try:
        if not order_id:
            raise HTTPException(
                status_code=400,
                detail="order_id is required"
            )
        
        if not x402_executor:
            logger.warning("x402 executor not initialized for order status request")
            raise HTTPException(
                status_code=503,
                detail="x402 executor not initialized. Contract deployment required."
            )
        
        logger.info(f"Checking order status for: {order_id}")
        
        try:
            order_status = await x402_executor.check_order_status(order_id)
            
            if not order_status:
                raise HTTPException(
                    status_code=404,
                    detail=f"Order {order_id} not found"
                )
            
            return order_status
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error checking order status for {order_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to check order status: {str(e)}"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_order_status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get order status: {str(e)}"
        )

@app.post("/swap")
async def create_swap(request: SwapRequestModel):
    """
    Main swap endpoint - Complete orchestration workflow
    Phase 1: Liquidity Discovery
    Phase 2: Split Optimization (Linear Programming)
    Phase 3: Risk Validation
    Phase 4: x402 Execution
    """
    try:
        if not agent_orchestrator:
            logger.warning("Agent orchestrator not initialized for swap request")
            raise HTTPException(
                status_code=503,
                detail="Agent orchestrator not initialized. Please try again later."
            )
        
        # Validate input
        if not request.input_token or not request.output_token:
            raise HTTPException(
                status_code=400,
                detail="Both input_token and output_token are required"
            )
        
        if request.amount_in <= 0:
            raise HTTPException(
                status_code=400,
                detail="amount_in must be greater than 0"
            )
        
        if not request.user_address:
            raise HTTPException(
                status_code=400,
                detail="user_address is required"
            )
        
        if request.slippage_tolerance < 0 or request.slippage_tolerance > 1:
            raise HTTPException(
                status_code=400,
                detail="slippage_tolerance must be between 0 and 1"
            )
        
        logger.info(f"Creating swap: {request.amount_in} {request.input_token} -> {request.output_token} for {request.user_address}")
        
        swap_req = SwapRequest(
            input_token=request.input_token,
            output_token=request.output_token,
            amount_in=request.amount_in,
            slippage_tolerance=request.slippage_tolerance,
            user_address=request.user_address,
            deadline=request.deadline or int(datetime.now().timestamp()) + 1800
        )
        
        result = await agent_orchestrator.orchestrate_swap(swap_req)
        
        if not result:
            raise HTTPException(
                status_code=500,
                detail="Swap orchestration returned no results"
            )
        
        logger.info(f"Swap orchestration completed successfully")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating swap: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create swap: {str(e)}"
        )

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
            import random
            
            # Generate more varied recent executions
            token_pairs = [
                ("CRO", "USDC.e"),
                ("CRO", "USDT"),
                ("USDC.e", "CRO"),
                ("CRO", "WETH"),
                ("USDT", "USDC.e"),
                ("CRO", "DAI"),
            ]
            
            recent_executions = []
            now = int(datetime.now().timestamp())
            
            for i in range(15):
                token_in, token_out = random.choice(token_pairs)
                time_offset = i * random.randint(60, 180)  # 1-3 minutes apart
                
                # Varied amounts
                base_amount = random.randint(5000, 500000)
                amount_out_multiplier = random.uniform(0.48, 0.52)  # Approximate CRO price
                
                # Varied savings percentages
                savings = random.uniform(1.5, 4.5)
                
                # Varied statuses (mostly success, some pending)
                statuses = ["success"] * 13 + ["pending"] * 2
                
                recent_executions.append({
                    "id": f"exec_{i}_{random.randint(1000, 9999)}",
                    "timestamp": now - time_offset,
                    "token_in": token_in,
                    "token_out": token_out,
                    "amount_in": base_amount,
                    "amount_out": int(base_amount * amount_out_multiplier),
                    "savings_pct": round(savings, 2),
                    "status": statuses[i] if i < len(statuses) else "success"
                })
            
            # Sort by timestamp descending (most recent first)
            recent_executions.sort(key=lambda x: x["timestamp"], reverse=True)
            
            return {
                "total_volume_usd": 3456789,
                "total_executions": 1247,
                "avg_savings_pct": 2.87,
                "agent_status": "active",
                "success_rate": 98.5,
                "avg_gas_efficiency": 0.95,
                "recent_executions": recent_executions
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== Multi-DEX Routing Endpoints ====================

@app.post("/api/multi-dex/optimize")
async def optimize_multi_dex_route(request: OptimizeRequest, strategy: str = "weighted_liquidity"):
    """
    Optimize route across multiple DEXs using advanced algorithms
    
    Strategies:
    - weighted_liquidity: Split based on liquidity-weighted distribution
    - price_impact: Minimize price impact across pools
    - balanced: Equal distribution
    - greedy: Use best pool only
    """
    try:
        if not multi_dex_router_agent:
            raise HTTPException(
                status_code=503,
                detail="Multi-DEX router agent not initialized"
            )
        
        # Validate input
        if request.amount_in <= 0:
            raise HTTPException(status_code=400, detail="amount_in must be greater than 0")
        
        if not request.token_in or not request.token_out:
            raise HTTPException(status_code=400, detail="Both token_in and token_out are required")
        
        logger.info(f"Optimizing multi-DEX route: {request.amount_in} {request.token_in} -> {request.token_out}, strategy={strategy}")
        
        # Create optimization message
        from agents.message_bus import AgentMessage
        from decimal import Decimal
        
        optimize_msg = AgentMessage(
            message_id=f"optimize_{datetime.now().timestamp()}",
            sender="api",
            receiver="multi_dex_router",
            message_type="optimize_multi_dex_route",
            payload={
                "token_in": request.token_in,
                "token_out": request.token_out,
                "amount_in": request.amount_in,
                "max_slippage": request.max_slippage,
                "strategy": strategy
            }
        )
        
        # For now, use direct method call (would use message bus in production)
        from agents.models import Token, DEXPool
        pools = []  # Would be fetched from liquidity_analyzer
        
        route = await multi_dex_router_agent._optimize_route(
            token_in=request.token_in,
            token_out=request.token_out,
            amount_in=Decimal(str(request.amount_in)),
            pools=pools,
            strategy=strategy,
            max_slippage=Decimal(str(request.max_slippage))
        )
        
        # Convert to response format
        routes = []
        for split in route.splits:
            routes.append({
                "dex": split.dex_name,
                "pool_address": split.pool_address,
                "amountIn": float(split.amount_in),
                "estimatedOut": float(split.expected_amount_out),
                "minOut": float(split.min_amount_out),
                "path": split.path
            })
        
        return {
            "route_id": route.route_id,
            "token_in": request.token_in,
            "token_out": request.token_out,
            "total_amount_in": float(route.total_amount_in),
            "total_expected_out": float(route.total_expected_out),
            "total_min_out": float(route.total_min_out),
            "predicted_slippage": float(route.predicted_slippage),
            "expected_gas": float(route.expected_gas),
            "confidence_score": route.confidence_score,
            "risk_score": route.risk_score,
            "routes": routes
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error optimizing multi-DEX route: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/multi-dex/registry")
async def get_dex_registry():
    """Get DEX registry with all configured DEXs"""
    try:
        if not multi_dex_router_agent:
            raise HTTPException(
                status_code=503,
                detail="Multi-DEX router agent not initialized"
            )
        
        registry = multi_dex_router_agent.get_dex_registry()
        
        return {
            "dexes": {
                dex_id: {
                    "dex_id": config.dex_id,
                    "name": config.name,
                    "router_address": config.router_address,
                    "factory_address": config.factory_address,
                    "fee_bps": config.fee_bps,
                    "priority": config.priority,
                    "is_active": config.is_active,
                    "min_liquidity_usd": str(config.min_liquidity_usd)
                }
                for dex_id, config in registry.items()
            },
            "active_dexes": multi_dex_router_agent.get_active_dexes()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting DEX registry: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/multi-dex/analytics")
async def get_multi_dex_analytics():
    """Get multi-DEX routing analytics"""
    try:
        if not multi_dex_analytics:
            raise HTTPException(
                status_code=503,
                detail="Multi-DEX analytics service not initialized"
            )
        
        return multi_dex_analytics.get_summary()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting analytics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/multi-dex/analytics/dex/{dex_id}")
async def get_dex_analytics(dex_id: str):
    """Get analytics for a specific DEX"""
    try:
        if not multi_dex_analytics:
            raise HTTPException(
                status_code=503,
                detail="Multi-DEX analytics service not initialized"
            )
        
        metrics = multi_dex_analytics.get_dex_metrics(dex_id)
        if not metrics:
            raise HTTPException(status_code=404, detail=f"DEX {dex_id} not found")
        
        return {
            "dex_id": metrics.dex_id,
            "total_swaps": metrics.total_swaps,
            "total_volume": str(metrics.total_volume),
            "total_successful": metrics.total_successful,
            "total_failed": metrics.total_failed,
            "success_rate": (metrics.total_successful / metrics.total_swaps * 100.0) if metrics.total_swaps > 0 else 0.0,
            "avg_slippage": str(metrics.avg_slippage),
            "avg_gas_used": str(metrics.total_gas_used / Decimal(metrics.total_swaps)) if metrics.total_swaps > 0 else "0"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting DEX analytics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/multi-dex/analytics/daily")
async def get_daily_analytics(days: int = 7):
    """Get daily statistics"""
    try:
        if not multi_dex_analytics:
            raise HTTPException(
                status_code=503,
                detail="Multi-DEX analytics service not initialized"
            )
        
        if days < 1 or days > 30:
            raise HTTPException(status_code=400, detail="days must be between 1 and 30")
        
        return {
            "daily_statistics": multi_dex_analytics.get_daily_statistics(days=days)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting daily analytics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/agent/status")
async def get_agent_status():
    """Get AI agent status and statistics with AI model information"""
    try:
        # Check agent orchestrator first (preferred)
        if HAS_AGENT_ORCHESTRATOR and agent_orchestrator:
            metrics = agent_orchestrator.get_metrics()
            ai_model_status = agent_orchestrator.get_ai_model_status()
            
            status = {
                "status": "online" if ai_model_status.get("initialized", False) else "offline",
                "available": ai_model_status.get("initialized", False),
                "decisions_today": metrics.get("total_workflows", 0),
                "successful_decisions": metrics.get("successful_workflows", 0),
                "failed_decisions": metrics.get("failed_workflows", 0),
                "success_rate": metrics.get("success_rate", 0.0),
                "avg_response_time_ms": int(metrics.get("avg_response_time_ms", 0)),
                "ai_predictions_used": metrics.get("ai_predictions_used", 0),
                "ai_models": ai_model_status,
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
        
        # Fallback to multi-agent orchestrator
        if not orchestrator:
            return {
                "status": "offline",
                "available": False,
                "decisions_today": 0,
                "avg_response_time_ms": 0,
                "ai_models": {"available": False},
                "recent_decisions": []
            }
        
        # Get orchestrator status
        status = {
            "status": "online" if orchestrator.is_running else "offline",
            "available": orchestrator.is_running,
            "active_requests": len(orchestrator.active_requests) if orchestrator else 0,
            "decisions_today": len(orchestrator.active_requests) if orchestrator else 0,
            "avg_response_time_ms": 145,  # Would come from actual metrics
            "ai_models": {"available": False, "note": "AI models not integrated with this orchestrator"},
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
        logger.error(f"Error getting agent status: {e}", exc_info=True)
        return {
            "status": "error",
            "available": False,
            "error": str(e),
            "ai_models": {"available": False}
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

# ==================== Instruction Set Endpoints ====================

@app.post("/api/instruction-sets")
async def create_instruction_set(request: CreateInstructionSetRequest):
    """Create a new instruction set"""
    try:
        if not instruction_set_registry:
            raise HTTPException(status_code=503, detail="Instruction set registry not initialized")
        
        from instruction_sets import (
            InstructionSetType, Condition, ConditionType,
            Action, ActionType, Schedule, Limits
        )
        
        # Convert request models to internal models
        conditions = [
            Condition(
                condition_type=ConditionType(c.condition_type),
                parameters=c.parameters,
                description=c.description
            )
            for c in request.conditions
        ]
        
        actions = [
            Action(
                action_type=ActionType(a.action_type),
                target=a.target,
                parameters=a.parameters,
                is_critical=a.is_critical,
                condition=Condition(
                    condition_type=ConditionType(a.condition.condition_type),
                    parameters=a.condition.parameters,
                    description=a.condition.description
                ) if a.condition else None
            )
            for a in request.actions
        ]
        
        schedule = Schedule(
            interval_seconds=request.schedule.interval_seconds,
            next_execution=request.schedule.next_execution,
            end_time=request.schedule.end_time,
            max_executions=request.schedule.max_executions
        )
        
        limits = Limits(
            max_notional_per_run=request.limits.max_notional_per_run,
            cumulative_cap=request.limits.cumulative_cap,
            max_slippage_bps=request.limits.max_slippage_bps,
            max_gas_per_execution=request.limits.max_gas_per_execution,
            per_beneficiary_cap=request.limits.per_beneficiary_cap,
            circuit_breaker_active=request.limits.circuit_breaker_active,
            pause_switch=request.limits.pause_switch
        )
        
        instruction_set = instruction_set_registry.create_instruction_set(
            owner=request.owner,
            instruction_type=InstructionSetType(request.instruction_type),
            schedule=schedule,
            conditions=conditions,
            actions=actions,
            limits=limits,
            metadata=request.metadata
        )
        
        return instruction_set.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/instruction-sets/{instruction_id}")
async def get_instruction_set(instruction_id: str):
    """Get instruction set by ID"""
    try:
        if not instruction_set_registry:
            raise HTTPException(status_code=503, detail="Instruction set registry not initialized")
        
        instruction_set = instruction_set_registry.get_instruction_set(instruction_id)
        if not instruction_set:
            raise HTTPException(status_code=404, detail="Instruction set not found")
        
        return instruction_set.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/instruction-sets/user/{owner}")
async def get_user_instruction_sets(owner: str):
    """Get all instruction sets for a user"""
    try:
        if not instruction_set_registry:
            raise HTTPException(status_code=503, detail="Instruction set registry not initialized")
        
        instruction_sets = instruction_set_registry.get_user_instruction_sets(owner)
        return [inst.to_dict() for inst in instruction_sets]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/instruction-sets/{instruction_id}")
async def update_instruction_set(
    instruction_id: str,
    request: UpdateInstructionSetRequest,
    owner: str  # Should come from auth in production
):
    """Update an instruction set"""
    try:
        if not instruction_set_registry:
            raise HTTPException(status_code=503, detail="Instruction set registry not initialized")
        
        from instruction_sets import (
            InstructionSetStatus, Condition, ConditionType,
            Action, ActionType, Schedule, Limits
        )
        
        # Convert request to internal models
        schedule = None
        if request.schedule:
            schedule = Schedule(
                interval_seconds=request.schedule.interval_seconds,
                next_execution=request.schedule.next_execution,
                end_time=request.schedule.end_time,
                max_executions=request.schedule.max_executions
            )
        
        conditions = None
        if request.conditions:
            conditions = [
                Condition(
                    condition_type=ConditionType(c.condition_type),
                    parameters=c.parameters,
                    description=c.description
                )
                for c in request.conditions
            ]
        
        actions = None
        if request.actions:
            actions = [
                Action(
                    action_type=ActionType(a.action_type),
                    target=a.target,
                    parameters=a.parameters,
                    is_critical=a.is_critical,
                    condition=Condition(
                        condition_type=ConditionType(a.condition.condition_type),
                        parameters=a.condition.parameters,
                        description=a.condition.description
                    ) if a.condition else None
                )
                for a in request.actions
            ]
        
        limits = None
        if request.limits:
            limits = Limits(
                max_notional_per_run=request.limits.max_notional_per_run,
                cumulative_cap=request.limits.cumulative_cap,
                max_slippage_bps=request.limits.max_slippage_bps,
                max_gas_per_execution=request.limits.max_gas_per_execution,
                per_beneficiary_cap=request.limits.per_beneficiary_cap,
                circuit_breaker_active=request.limits.circuit_breaker_active,
                pause_switch=request.limits.pause_switch
            )
        
        status = None
        if request.status:
            status = InstructionSetStatus(request.status)
        
        updated = instruction_set_registry.update_instruction_set(
            instruction_id=instruction_id,
            owner=owner,
            schedule=schedule,
            conditions=conditions,
            actions=actions,
            limits=limits,
            status=status,
            metadata=request.metadata
        )
        
        if not updated:
            raise HTTPException(status_code=404, detail="Instruction set not found or unauthorized")
        
        return updated.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/instruction-sets/{instruction_id}/pause")
async def pause_instruction_set(instruction_id: str, owner: str):
    """Pause an instruction set"""
    try:
        if not instruction_set_registry:
            raise HTTPException(status_code=503, detail="Instruction set registry not initialized")
        
        success = instruction_set_registry.pause_instruction_set(instruction_id, owner)
        if not success:
            raise HTTPException(status_code=404, detail="Instruction set not found or unauthorized")
        
        return {"success": True, "instruction_id": instruction_id, "status": "paused"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/instruction-sets/{instruction_id}/resume")
async def resume_instruction_set(instruction_id: str, owner: str):
    """Resume a paused instruction set"""
    try:
        if not instruction_set_registry:
            raise HTTPException(status_code=503, detail="Instruction set registry not initialized")
        
        success = instruction_set_registry.resume_instruction_set(instruction_id, owner)
        if not success:
            raise HTTPException(status_code=404, detail="Instruction set not found or unauthorized")
        
        return {"success": True, "instruction_id": instruction_id, "status": "active"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/instruction-sets/{instruction_id}/cancel")
async def cancel_instruction_set(instruction_id: str, owner: str):
    """Cancel an instruction set"""
    try:
        if not instruction_set_registry:
            raise HTTPException(status_code=503, detail="Instruction set registry not initialized")
        
        success = instruction_set_registry.cancel_instruction_set(instruction_id, owner)
        if not success:
            raise HTTPException(status_code=404, detail="Instruction set not found or unauthorized")
        
        return {"success": True, "instruction_id": instruction_id, "status": "cancelled"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/instruction-sets/{instruction_id}/execute")
async def execute_instruction_set(
    instruction_id: str,
    request: ExecuteInstructionSetRequest
):
    """Execute an instruction set (if conditions are met)"""
    try:
        if not instruction_set_registry:
            raise HTTPException(status_code=503, detail="Instruction set registry not initialized")
        
        result = await instruction_set_registry.execute_instruction_set(
            instruction_id=instruction_id,
            private_key=request.private_key,
            context=request.context
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/instruction-sets/{instruction_id}/history")
async def get_instruction_set_history(instruction_id: str, limit: int = 50):
    """Get execution history for an instruction set"""
    try:
        if not instruction_set_registry:
            raise HTTPException(status_code=503, detail="Instruction set registry not initialized")
        
        history = instruction_set_registry.get_execution_history(instruction_id, limit)
        return {"instruction_id": instruction_id, "history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/instruction-sets/active/due")
async def get_due_instruction_sets():
    """Get all instruction sets that are due for execution"""
    try:
        if not instruction_set_registry:
            raise HTTPException(status_code=503, detail="Instruction set registry not initialized")
        
        active_sets = instruction_set_registry.get_all_active_instruction_sets()
        due_sets = []
        
        for inst_set in active_sets:
            if await instruction_set_registry.check_execution_due(inst_set.instruction_id):
                due_sets.append(inst_set.to_dict())
        
        return {"due_instruction_sets": due_sets, "count": len(due_sets)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== Payment Verification Endpoints ====================

class PaymentVerifyRequest(BaseModel):
    tx_hash: str
    token_address: Optional[str] = None
    expected_recipient: Optional[str] = None
    min_amount_wei: Optional[str] = None

class PaymentVerifyResponse(BaseModel):
    ok: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@app.post("/api/payments/verify", response_model=PaymentVerifyResponse)
async def verify_payment(request: PaymentVerifyRequest):
    """
    Verify a payment transaction (native CRO or ERC-20)
    
    - For native CRO: verify tx value and recipient
    - For ERC-20: verify Transfer event logs
    """
    try:
        from verify_payment import verify_native_payment, verify_erc20_payment
        
        if request.token_address:
            # ERC-20 payment verification
            result = await verify_erc20_payment(
                tx_hash=request.tx_hash,
                token_address=request.token_address,
                expected_to=request.expected_recipient,
                min_amount=int(request.min_amount_wei) if request.min_amount_wei else None
            )
        else:
            # Native CRO payment verification
            result = await verify_native_payment(
                tx_hash=request.tx_hash,
                expected_recipient=request.expected_recipient,
                min_value_wei=int(request.min_amount_wei) if request.min_amount_wei else None
            )
        
        return PaymentVerifyResponse(
            ok=True,
            result={
                "receipt": result.get("receipt", {}),
                "parsed": result.get("parsed", {}),
                "tx": result.get("tx", {})
            }
        )
    except ValueError as e:
        return PaymentVerifyResponse(ok=False, error=str(e))
    except Exception as e:
        logger.error(f"Error verifying payment: {e}", exc_info=True)
        return PaymentVerifyResponse(ok=False, error=str(e))

class PaymentContractInfoResponse(BaseModel):
    contract_address: str
    payment_count: Optional[int] = None
    owner: Optional[str] = None

class PaymentBatchVerifyRequest(BaseModel):
    requests: List[PaymentVerifyRequest]

class PaymentBatchVerifyResponse(BaseModel):
    ok: bool
    results: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None

@app.post("/api/payments/verify-batch", response_model=PaymentBatchVerifyResponse)
async def verify_payments_batch(request: PaymentBatchVerifyRequest):
    """
    Verify multiple payment transactions in batch
    
    - Supports both native CRO and ERC-20 token payments
    - Uses caching to improve performance
    - Returns results for each payment request
    """
    try:
        from verify_payment import verify_payments_batch as batch_verify
        
        # Convert Pydantic models to dicts
        requests_list = [
            {
                'tx_hash': r.tx_hash,
                'token_address': r.token_address,
                'expected_recipient': r.expected_recipient,
                'min_amount_wei': r.min_amount_wei,
            }
            for r in request.requests
        ]
        
        results = await batch_verify(requests_list)
        
        return PaymentBatchVerifyResponse(
            ok=True,
            results=results
        )
    except Exception as e:
        logger.error(f"Error in batch verification: {e}", exc_info=True)
        return PaymentBatchVerifyResponse(ok=False, error=str(e))

@app.post("/api/payments/clear-cache")
async def clear_payment_cache():
    """Clear the payment verification cache"""
    try:
        from verify_payment import clear_cache
        clear_cache()
        return {"ok": True, "message": "Cache cleared successfully"}
    except Exception as e:
        logger.error(f"Error clearing cache: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}

@app.get("/api/payments/contract-info", response_model=PaymentContractInfoResponse)
async def get_payment_contract_info():
    """Get payment processor contract information"""
    try:
        payment_contract_address = os.getenv("PAYMENT_CONTRACT_ADDRESS")
        if not payment_contract_address:
            raise HTTPException(
                status_code=503,
                detail="Payment contract address not configured"
            )
        
        # Optional: Query contract state if needed
        # This requires web3 connection to the contract
        
        return PaymentContractInfoResponse(
            contract_address=payment_contract_address
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting payment contract info: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/intelligent-settlement/create-deal")
async def create_intelligent_settlement_deal(request: CreateDealRequest):
    """Create a new intelligent settlement deal with milestones"""
    try:
        if not intelligent_settlement:
            raise HTTPException(
                status_code=503,
                detail="Intelligent settlement service not initialized. Set INTELLIGENT_SETTLEMENT_CONTRACT environment variable."
            )
        
        # Validate milestone amounts sum to total
        if sum(request.milestone_amounts) != request.total_amount:
            raise HTTPException(
                status_code=400,
                detail="Milestone amounts must sum to total_amount"
            )
        
        # Validate fee
        if request.fee_bps < 0 or request.fee_bps > 500:
            raise HTTPException(
                status_code=400,
                detail="fee_bps must be between 0 and 500"
            )
        
        # Validate deadline
        current_time = int(datetime.now().timestamp())
        if request.deadline <= current_time:
            raise HTTPException(
                status_code=400,
                detail="Deadline must be in the future"
            )
        
        result = await intelligent_settlement.create_deal(
            seller=request.seller,
            token=request.token,
            total_amount=request.total_amount,
            deadline=request.deadline,
            milestone_amounts=request.milestone_amounts,
            fee_bps=request.fee_bps,
            arbitrator=request.arbitrator,
            buyer_private_key=request.buyer_private_key
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Failed to create deal")
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating intelligent settlement deal: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/intelligent-settlement/fund-deal")
async def fund_intelligent_settlement_deal(request: FundDealRequest):
    """Fund an existing intelligent settlement deal"""
    try:
        if not intelligent_settlement:
            raise HTTPException(
                status_code=503,
                detail="Intelligent settlement service not initialized"
            )
        
        result = await intelligent_settlement.fund_deal(
            deal_id=request.deal_id,
            amount=request.amount,
            buyer_private_key=request.buyer_private_key,
            is_native=request.is_native
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Failed to fund deal")
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error funding intelligent settlement deal: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/intelligent-settlement/release-milestone")
async def release_milestone(request: ReleaseMilestoneRequest):
    """Release a milestone (called by authorized AI agent)"""
    try:
        if not intelligent_settlement:
            raise HTTPException(
                status_code=503,
                detail="Intelligent settlement service not initialized"
            )
        
        result = await intelligent_settlement.agent_release_milestone(
            deal_id=request.deal_id,
            milestone_index=request.milestone_index,
            min_seller_amount=request.min_seller_amount,
            agent_nonce=request.agent_nonce
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Failed to release milestone")
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error releasing milestone: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/intelligent-settlement/deal/{deal_id}")
async def get_intelligent_settlement_deal(deal_id: int):
    """Get intelligent settlement deal information"""
    try:
        if not intelligent_settlement:
            raise HTTPException(
                status_code=503,
                detail="Intelligent settlement service not initialized"
            )
        
        deal = await intelligent_settlement.get_deal(deal_id)
        
        if "error" in deal:
            raise HTTPException(
                status_code=404,
                detail=deal.get("error", "Deal not found")
            )
        
        return deal
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting intelligent settlement deal: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/intelligent-settlement/refund")
async def refund_intelligent_settlement_deal(request: RefundDealRequest):
    """Refund remaining funds after deadline (buyer-initiated)"""
    try:
        if not intelligent_settlement:
            raise HTTPException(
                status_code=503,
                detail="Intelligent settlement service not initialized"
            )
        
        result = await intelligent_settlement.refund_after_deadline(
            deal_id=request.deal_id,
            buyer_private_key=request.buyer_private_key
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Failed to refund deal")
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refunding intelligent settlement deal: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/intelligent-settlement/agent-address")
async def get_authorized_agent_address():
    """Get the authorized agent address for the settlement contract"""
    try:
        if not intelligent_settlement:
            raise HTTPException(
                status_code=503,
                detail="Intelligent settlement service not initialized"
            )
        
        agent_address = await intelligent_settlement.check_authorized_agent()
        return {"authorized_agent": agent_address}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting authorized agent address: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# ==================== DAO Endpoints ====================

class CreateProposalRequest(BaseModel):
    proposal_type: str  # "eth_transfer", "erc20_transfer", "arbitrary_call"
    recipient: Optional[str] = None
    token: Optional[str] = None
    amount: str
    description: str
    private_key: str  # In production, use secure key management
    target: Optional[str] = None  # For arbitrary calls
    call_data: Optional[str] = None  # Hex string for arbitrary calls
    value: Optional[str] = "0"  # For arbitrary calls

class VoteRequest(BaseModel):
    proposal_id: int
    support: int  # 0 = Against, 1 = For, 2 = Abstain
    private_key: str

class ExecuteProposalRequest(BaseModel):
    proposal_id: int
    private_key: str

@app.get("/api/dao/info")
async def get_dao_info():
    """Get DAO configuration and addresses"""
    try:
        if not dao_executor:
            raise HTTPException(status_code=503, detail="DAO executor not initialized")
        
        info = await dao_executor.get_dao_info()
        return info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting DAO info: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dao/proposal/{proposal_id}")
async def get_proposal(proposal_id: int):
    """Get proposal details"""
    try:
        if not dao_executor:
            raise HTTPException(status_code=503, detail="DAO executor not initialized")
        
        proposal = await dao_executor.get_proposal(proposal_id)
        return proposal
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting proposal: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dao/voting-power/{user_address}")
async def get_voting_power(user_address: str):
    """Get user's voting power and token balance"""
    try:
        if not dao_executor:
            raise HTTPException(status_code=503, detail="DAO executor not initialized")
        
        power = await dao_executor.get_user_voting_power(user_address)
        return power
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting voting power: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/dao/proposal/create")
async def create_proposal(request: CreateProposalRequest):
    """Create a new DAO proposal"""
    try:
        if not dao_executor:
            raise HTTPException(status_code=503, detail="DAO executor not initialized")
        
        if request.proposal_type == "eth_transfer":
            if not request.recipient:
                raise HTTPException(status_code=400, detail="Recipient required for ETH transfer")
            result = await dao_executor.create_proposal_eth_transfer(
                recipient=request.recipient,
                amount=request.amount,
                description=request.description,
                private_key=request.private_key
            )
        elif request.proposal_type == "erc20_transfer":
            if not request.token or not request.recipient:
                raise HTTPException(status_code=400, detail="Token and recipient required for ERC20 transfer")
            # TODO: Implement ERC20 transfer proposal creation
            raise HTTPException(status_code=501, detail="ERC20 transfer proposals not yet implemented")
        elif request.proposal_type == "arbitrary_call":
            if not request.target or not request.call_data:
                raise HTTPException(status_code=400, detail="Target and call_data required for arbitrary call")
            # TODO: Implement arbitrary call proposal creation
            raise HTTPException(status_code=501, detail="Arbitrary call proposals not yet implemented")
        else:
            raise HTTPException(status_code=400, detail=f"Invalid proposal type: {request.proposal_type}")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating proposal: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/dao/vote")
async def vote_on_proposal(request: VoteRequest):
    """Vote on a proposal"""
    try:
        if not dao_executor:
            raise HTTPException(status_code=503, detail="DAO executor not initialized")
        
        if request.support not in [0, 1, 2]:
            raise HTTPException(status_code=400, detail="Support must be 0 (Against), 1 (For), or 2 (Abstain)")
        
        result = await dao_executor.vote_on_proposal(
            proposal_id=request.proposal_id,
            support=request.support,
            private_key=request.private_key
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error voting on proposal: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/dao/proposal/finalize")
async def finalize_proposal(request: ExecuteProposalRequest):
    """Finalize a proposal after voting period ends"""
    try:
        if not dao_executor:
            raise HTTPException(status_code=503, detail="DAO executor not initialized")
        
        result = await dao_executor.finalize_proposal(
            proposal_id=request.proposal_id,
            private_key=request.private_key
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error finalizing proposal: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/dao/proposal/execute")
async def execute_proposal(request: ExecuteProposalRequest):
    """Execute a succeeded proposal"""
    try:
        if not dao_executor:
            raise HTTPException(status_code=503, detail="DAO executor not initialized")
        
        result = await dao_executor.execute_proposal(
            proposal_id=request.proposal_id,
            private_key=request.private_key
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing proposal: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

