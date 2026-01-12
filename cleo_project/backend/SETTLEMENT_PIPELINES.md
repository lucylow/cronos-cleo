# Automated Settlement Pipelines

Automated settlement pipelines are multi-step, on-chain workflows that execute complex financial operations atomically—either all steps succeed together or the entire transaction reverts. This system demonstrates "financially complex, multi-step x402 automation" for the Cronos x402 hackathon.

## Core Concepts

### What is a Settlement Pipeline?

A settlement pipeline transforms a high-level financial instruction (e.g., "pay supplier if delivery confirmed", "settle trade after collateral posted", "execute cross-DEX swap with min output") into a sequence of low-level blockchain operations that execute as one atomic unit.

**Key Characteristics:**
- **Multi-step**: Involves 3+ operations (transfer → swap → deposit → callback → emit event)
- **Conditional**: Each step (or the entire pipeline) has predicates that must pass
- **Atomic**: All succeed or all revert (no partial execution)
- **Automated**: Triggered by time, events, oracle data, or AI agents without manual intervention
- **Deterministic**: Same inputs always produce same outputs

## Architecture

### Smart Contract Layer (`SettlementPipeline.sol`)

The smart contract provides:
- Pipeline creation and management
- Atomic execution via x402 facilitator
- Multiple pipeline patterns (Cross-DEX, Invoice, Yield Harvest)
- Recurring pipeline scheduling
- Safety mechanisms (circuit breakers, value limits)

### Backend Services

1. **PipelineExecutor** (`pipeline_executor.py`)
   - Creates and manages pipelines
   - Validates pipelines before execution
   - Executes pipelines on-chain via x402
   - Simulates pipeline execution

2. **PipelineSafetyService** (`pipeline_safety.py`)
   - Pre-execution validation
   - Circuit breaker management
   - Volatility and liquidity checks
   - Risk scoring

3. **PipelineScheduler** (`pipeline_scheduler.py`)
   - Recurring pipeline execution
   - Automated scheduling
   - Execution tracking

## Pipeline Patterns

### 1. Cross-DEX Settlement

**Use Case**: Split a large swap across multiple DEXs to minimize slippage

**Example**: Swap 100k CRO → USDC across VVS, CronaSwap, and MM Finance

```python
POST /api/pipelines/cross-dex-settlement
{
  "creator": "0x...",
  "routes": [
    {
      "router": "0xVVS_Router",
      "path": ["CRO", "USDC"],
      "amountIn": 45000,
      "minAmountOut": 22000
    },
    {
      "router": "0xCRONA_Router",
      "path": ["CRO", "USDC"],
      "amountIn": 30000,
      "minAmountOut": 14700
    },
    {
      "router": "0xMMF_Router",
      "path": ["CRO", "USDC"],
      "amountIn": 25000,
      "minAmountOut": 12250
    }
  ],
  "tokenIn": "0xCRO",
  "tokenOut": "0xUSDC",
  "totalAmountIn": 100000,
  "minTotalOut": 48950,
  "deadline": 1735689600
}
```

**Pipeline Steps**:
1. Execute swap on VVS (45k CRO)
2. Execute swap on CronaSwap (30k CRO)
3. Execute swap on MM Finance (25k CRO)
4. Aggregate USDC output
5. Transfer to recipient

### 2. Invoice Payment Settlement

**Use Case**: Pay supplier only if delivery NFT exists and is owned by recipient

**Example**: Pay 10k USDC for invoice #1234 after delivery confirmation

```python
POST /api/pipelines/invoice-payment
{
  "creator": "0xBuyer",
  "invoiceId": 1234,
  "currency": "0xUSDC",
  "amount": 10000000000,  // 10k USDC (6 decimals)
  "recipient": "0xSupplier",
  "deliveryTokenId": 5678,
  "deliveryNFT": "0xDeliveryNFT",
  "receiptNFT": "0xReceiptNFT"
}
```

**Pipeline Steps**:
1. Verify delivery NFT exists and owner == recipient
2. Transfer 10k USDC to supplier
3. Burn delivery NFT
4. Mint receipt NFT to supplier

### 3. Yield Harvest + Compound

**Use Case**: Automatically harvest rewards and compound them back into LP position

**Example**: Harvest VVS rewards, swap to balance, add liquidity, stake LP tokens

```python
POST /api/pipelines/yield-harvest
{
  "creator": "0xFarmer",
  "farmAddress": "0xVVS_Farm",
  "rewardToken": "0xVVS",
  "lpToken": "0xLP_CRO_USDC",
  "token0": "0xCRO",
  "token1": "0xUSDC",
  "router": "0xVVS_Router",
  "minRewardThreshold": 1000000000  // 1 VVS minimum
}
```

**Pipeline Steps**:
1. Check if rewards > threshold
2. Claim VVS rewards
3. Swap VVS → USDC (if needed for balance)
4. Add liquidity (CRO-USDC → LP tokens)
5. Stake LP tokens back in farm

## API Endpoints

### Create Pipelines

- `POST /api/pipelines/cross-dex-settlement` - Create cross-DEX settlement
- `POST /api/pipelines/invoice-payment` - Create invoice payment
- `POST /api/pipelines/yield-harvest` - Create yield harvest pipeline

### Pipeline Management

- `GET /api/pipelines/{pipeline_id}` - Get pipeline details
- `GET /api/pipelines/user/{user_address}` - Get user's pipelines
- `POST /api/pipelines/{pipeline_id}/validate` - Validate pipeline
- `POST /api/pipelines/{pipeline_id}/simulate` - Simulate execution
- `POST /api/pipelines/{pipeline_id}/execute` - Execute pipeline

### Recurring Pipelines

- `POST /api/pipelines/{pipeline_id}/schedule-recurring` - Schedule recurring execution

## Safety Mechanisms

### Pre-Execution Checks

1. **Circuit Breaker**: Global pause for all pipelines
2. **Deadline Validation**: Ensure pipeline hasn't expired
3. **Value Limits**: Maximum pipeline value restrictions
4. **Step Validation**: Verify all steps are valid
5. **High-Value Approval**: Human approval for >5% treasury value
6. **Liquidity Checks**: Verify sufficient liquidity exists
7. **Slippage Validation**: Ensure slippage limits are reasonable

### During Execution

- Per-step minimum outputs
- Global minimum output condition
- Atomic execution (all or nothing)
- x402 conditional batch execution

### Post-Execution

- Receipt NFTs / events
- Accounting updates
- Scheduled next execution (for recurring)

## Usage Example

### Complete Workflow

```python
# 1. Create a cross-DEX settlement pipeline
response = requests.post(
    "http://localhost:8000/api/pipelines/cross-dex-settlement",
    json={
        "creator": "0xUser",
        "routes": [...],
        "tokenIn": "0xCRO",
        "tokenOut": "0xUSDC",
        "totalAmountIn": 100000,
        "minTotalOut": 48950,
        "deadline": 1735689600
    }
)
pipeline_id = response.json()["pipeline_id"]

# 2. Validate pipeline
validation = requests.post(
    f"http://localhost:8000/api/pipelines/{pipeline_id}/validate"
)
print(validation.json())  # {"valid": True, ...}

# 3. Simulate execution
simulation = requests.post(
    f"http://localhost:8000/api/pipelines/{pipeline_id}/simulate"
)
print(simulation.json())  # {"estimated_gas": 180000, ...}

# 4. Execute pipeline
execution = requests.post(
    f"http://localhost:8000/api/pipelines/{pipeline_id}/execute",
    json={"private_key": "0x..."}  # In production, use secure key management
)
print(execution.json())  # {"success": True, "tx_hash": "0x...", ...}

# 5. Schedule for recurring execution (optional)
schedule = requests.post(
    f"http://localhost:8000/api/pipelines/{pipeline_id}/schedule-recurring",
    json={
        "interval_seconds": 86400,  # Daily
        "max_executions": 30
    }
)
```

## Integration with x402

The settlement pipelines leverage Cronos x402 for atomic multi-contract execution:

```solidity
// All pipeline steps execute atomically via x402
facilitator.executeConditionalBatch(
    operations,        // Array of pipeline steps
    minTotalOut,       // Global condition
    deadline
);
```

**Benefits**:
- Sub-second blocks → settlement finality in <1s
- 10x lower gas → complex pipelines remain economical
- Native x402 → atomic execution without custom assembly
- Growing DEX ecosystem → multiple routing options

## Production Considerations

### Security

1. **Private Key Management**: Never store private keys in code. Use secure key management services (AWS KMS, HashiCorp Vault, etc.)
2. **Access Control**: Implement proper authentication and authorization
3. **Rate Limiting**: Prevent abuse of API endpoints
4. **Monitoring**: Set up alerts for failed pipelines

### Scalability

1. **Database**: Store pipeline state in PostgreSQL
2. **Caching**: Use Redis for frequently accessed data
3. **Queue System**: Use Celery for async pipeline execution
4. **Load Balancing**: Scale backend services horizontally

### Monitoring

1. **Pipeline Status**: Track success/failure rates
2. **Gas Usage**: Monitor gas consumption per pipeline type
3. **Execution Times**: Track pipeline execution duration
4. **Error Rates**: Alert on high failure rates

## Demo Script

For the hackathon demo:

1. **Show single DEX swap**: 100k CRO→USDC → 2.8% slippage
2. **Show CLEO pipeline**: Same swap → 0.32% slippage (8.75x improvement)
3. **Show atomic revert**: When VVS pool depleted, entire pipeline reverts
4. **Show recurring harvest**: Pipeline executing automatically 3x

This demonstrates:
- ✅ Multi-step atomic execution
- ✅ Conditional execution
- ✅ Integration across DeFi protocols
- ✅ Automated recurring execution
- ✅ Safety mechanisms

## Next Steps

1. Deploy `SettlementPipeline.sol` to Cronos testnet
2. Update contract address in environment variables
3. Test each pipeline pattern
4. Set up monitoring and alerts
5. Create frontend UI for pipeline management
6. Record demo video

