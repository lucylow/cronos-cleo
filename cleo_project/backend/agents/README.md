# C.L.E.O. Multi-Agent System

## Overview

The C.L.E.O. (Cronos Liquidity Execution Orchestrator) Multi-Agent System is a sophisticated AI-powered system for optimizing and executing token swaps across multiple DEXs on Cronos using x402 for atomic execution.

## Architecture

### Agent Components

1. **OrchestratorAgent** - Main coordinator that manages all other agents
2. **LiquidityAnalyzerAgent** - Monitors real-time liquidity across DEXs (VVS Finance, CronaSwap, MM Finance)
3. **SlippagePredictorAgent** - ML-based slippage prediction using historical data
4. **RouteOptimizerAgent** - Calculates optimal route splits across multiple DEXs
5. **ExecutionAgent** - Executes trades via x402 facilitator for atomic batch execution
6. **RiskManagerAgent** - Monitors execution risks and provides alerts
7. **PerformanceMonitorAgent** - Tracks system performance metrics

### Communication

Agents communicate via a **MessageBus** system using `AgentMessage` objects. This enables:
- Asynchronous inter-agent communication
- Event broadcasting
- Request/response patterns
- Priority-based message handling

## Usage

### Basic Setup

```python
from agents import OrchestratorAgent, message_bus

# Initialize orchestrator
orchestrator = OrchestratorAgent(
    cronos_rpc="https://evm-t3.cronos.org",
    private_key="your_private_key",  # Optional
    x402_facilitator="0x...",  # Optional
    redis_url="redis://localhost:6379"  # Optional
)

# Register and start
message_bus.register_agent(orchestrator)
await orchestrator.start()
```

### Execute a Swap

```python
from decimal import Decimal

result = await orchestrator.execute_swap(
    token_in="0x5C7F8A570d578ED84E63fdFA7b1eE72dEae1AE23",  # WCRO
    token_out="0xc21223249CA28397B4B6541dfFaEcC539BfF0c59",  # USDC
    amount_in=Decimal("1000"),
    max_slippage=Decimal("0.01"),  # 1%
    strategy="ai_optimized"
)
```

### API Endpoints

The multi-agent system is integrated with the FastAPI backend:

- `POST /api/v2/swap` - Execute swap using multi-agent system
- `GET /api/v2/system-status` - Get system status
- `GET /api/multi-agent/request/{request_id}` - Get request status

## Features

### Real-Time Liquidity Monitoring
- Subgraph integration for VVS Finance, CronaSwap, MM Finance
- On-chain reserve updates every 5 seconds
- Redis caching for performance

### AI-Powered Slippage Prediction
- Heuristic ML model (can be replaced with trained models)
- Time-of-day adjustments
- Volatility factor consideration

### Route Optimization Strategies
- **ai_optimized** - ML-based optimal distribution
- **proportional** - Based on liquidity share
- **greedy** - Use best pool first
- **balanced** - Equal distribution

### x402 Atomic Execution
- Batch transaction construction
- Conditional execution via x402 facilitator
- Gas estimation and optimization

## Configuration

Set environment variables:

```bash
CRONOS_RPC=https://evm-t3.cronos.org
PRIVATE_KEY=your_private_key  # Optional for execution
X402_FACILITATOR=0x...  # Optional for execution
REDIS_URL=redis://localhost:6379  # Optional for caching
```

## Development

### Adding a New Agent

1. Create a new file in `agents/` directory
2. Inherit from `BaseAgent`
3. Implement `handle_message()` method
4. Register with message bus in orchestrator

### Testing

```python
# Test individual agent
from agents import LiquidityAnalyzerAgent

agent = LiquidityAnalyzerAgent("https://evm-t3.cronos.org")
await agent.start()
# ... test agent functionality
await agent.stop()
```

## Notes

- The system gracefully degrades if Redis is unavailable
- Execution requires private key and x402 facilitator address
- All agents run asynchronously for optimal performance
- Message queue has a max size of 1000 messages per agent
