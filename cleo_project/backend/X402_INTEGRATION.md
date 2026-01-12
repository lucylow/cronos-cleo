# x402 Integration Guide

This document explains how the Cross-DEX Intelligent Settlement & Routing Engine integrates with Cronos x402 Facilitator.

## Overview

The system uses x402 to execute multi-DEX swaps atomically, ensuring that either all routes execute successfully or none do (atomicity guarantee).

## Architecture

```
User Request
    ↓
AI Agent (Route Optimization)
    ↓
x402 Executor (Prepares Routes)
    ↓
Smart Contract (CrossDEXRouter)
    ↓
x402 Facilitator (Atomic Execution)
    ↓
Multiple DEX Routers (VVS, CronaSwap, MM Finance)
    ↓
Tokens Returned to User
```

## Components

### 1. Smart Contract (`CrossDEXRouter.sol`)

The main router contract that:
- Accepts optimized route splits from the AI agent
- Validates route parameters
- Executes all routes atomically via x402 facilitator
- Handles failures gracefully (reverts all on any failure)

**Key Functions:**
- `executeOptimizedSwap()`: Main entry point for executing optimized swaps
- `_executeRoutes()`: Internal function that uses x402 facilitator
- `_buildOperations()`: Constructs x402 operations from route splits

### 2. x402 Executor (`x402_executor.py`)

Python service that:
- Connects AI optimization results to smart contract
- Prepares route splits in contract format
- Handles transaction signing and submission
- Monitors order status

**Key Methods:**
- `prepare_route_splits()`: Converts AI output to contract format
- `execute_swap()`: Executes swap through contract
- `check_order_status()`: Queries order execution status

### 3. AI Agent (`ai_agent.py`)

Optimizes route splits using:
- Real-time liquidity data from MCP
- Historical volatility metrics
- Machine learning slippage prediction
- Multi-strategy optimization

### 4. MCP Client (`mcp_client.py`)

Integrates with Crypto.com Market Data MCP Server for:
- Real-time price feeds
- Liquidity depth analysis
- Volatility metrics
- Orderbook data

## Setup

### 1. Environment Variables

Create a `.env` file:

```bash
# Cronos RPC
CRONOS_RPC=https://evm-t3.cronos.org

# x402 Facilitator
X402_FACILITATOR_URL=https://facilitator.cronos.org

# Router Contract (deploy first)
ROUTER_CONTRACT_ADDRESS=0x...

# Executor Private Key (for automated execution)
EXECUTOR_PRIVATE_KEY=0x...

# MCP Server (optional)
CRYPTOCOM_MCP_URL=https://mcp.crypto.com/api/v1
CRYPTOCOM_MCP_KEY=your_api_key
```

### 2. Deploy Smart Contract

```bash
# Install dependencies
npm install @crypto.com/facilitator-client
npm install @openzeppelin/contracts

# Compile
npx hardhat compile

# Deploy to Cronos testnet
npx hardhat run scripts/deploy.js --network cronos-testnet
```

### 3. Initialize DEX Registry

After deployment, register DEX routers:

```solidity
// VVS Finance
router.registerDEX(
    "vvs",
    0x145863Eb42Cf62847A6Ca784e6416C1682B1b2Ae,
    0x38ed1739, // swapExactTokensForTokens selector
    "VVS Finance"
);

// CronaSwap
router.registerDEX(
    "cronaswap",
    0xcd7d16fB918511BF72679eC3eC2f2f39c33C2F45,
    0x38ed1739,
    "CronaSwap"
);
```

## Usage

### 1. Optimize Routes

```python
POST /api/optimize
{
    "token_in": "CRO",
    "token_out": "USDC.e",
    "amount_in": 100000,
    "max_slippage": 0.005
}
```

Response includes optimized split across multiple DEXs.

### 2. Simulate Execution

```python
POST /api/simulate
[
    {
        "id": "r_0",
        "dex": "VVS Finance",
        "amountIn": 45000,
        "estimatedOut": 5400,
        "path": ["CRO", "USDC.e"]
    },
    ...
]
```

Returns predicted slippage and gas estimates.

### 3. Execute Swap

```python
POST /api/execute
{
    "token_in": "CRO",
    "token_out": "USDC.e",
    "amount_in": 100000,
    "max_slippage": 0.005
}
```

This will:
1. Get AI optimization
2. Prepare routes for contract
3. Execute via x402
4. Return transaction hash and order ID

### 4. Check Order Status

```python
GET /api/order/{order_id}
```

Returns execution status and results.

## x402 Execution Flow

1. **User submits swap request** → AI agent optimizes routes
2. **Routes prepared** → Converted to contract `RouteSplit[]` format
3. **Contract called** → `executeOptimizedSwap()` receives routes
4. **x402 operations built** → Each route becomes an `Operation`
5. **Atomic execution** → `facilitator.executeConditionalBatch()` executes all
6. **Validation** → All routes must meet minimum output requirements
7. **Success/Failure** → Either all succeed (tokens transferred) or all revert

## Error Handling

The system includes comprehensive error handling:

- **Route validation**: Checks DEX registration, path validity, amount matching
- **Slippage protection**: Validates minimum output before execution
- **Atomic rollback**: Failed routes cause entire transaction to revert
- **Token safety**: Input tokens returned to user on failure

## Gas Optimization

- **Batch execution**: All routes in single transaction
- **Shared approvals**: Single approval per token
- **Efficient routing**: Minimizes intermediate transfers
- **Cronos low fees**: Leverages Cronos's low gas costs

## Testing

### Testnet Testing

1. Get test tokens from Cronos faucet
2. Deploy contract to testnet
3. Register test DEX addresses
4. Execute test swaps

### Simulation Testing

Use the simulator to test without on-chain execution:

```python
from transaction_simulator import TransactionSimulator

simulator = TransactionSimulator(rpc_url)
result = await simulator.simulate_multi_route_swap(routes, pools)
```

## Security Considerations

1. **Private Key Management**: Never commit private keys
2. **Contract Ownership**: Use multi-sig for production
3. **Slippage Limits**: Always validate user-provided slippage
4. **Deadline Enforcement**: Check deadlines before execution
5. **DEX Validation**: Verify DEX router addresses

## Troubleshooting

### "x402 executor not initialized"
- Deploy router contract first
- Set `ROUTER_CONTRACT_ADDRESS` in `.env`

### "DEX not active"
- Register DEX using `registerDEX()`
- Check DEX router address is correct

### "Slippage exceeded"
- Increase `max_slippage` parameter
- Check pool liquidity
- Try smaller trade size

### "Order expired"
- Increase deadline when creating order
- Check network latency

## Next Steps

1. **Production Deployment**: Deploy to Cronos mainnet
2. **Monitoring**: Set up transaction monitoring
3. **Analytics**: Track execution performance
4. **Optimization**: Fine-tune AI model with real data
5. **Expansion**: Add more DEXs and token pairs

