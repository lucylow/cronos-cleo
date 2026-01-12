# Multi-Leg Transactions & Batching

Institutional-grade multi-leg transaction orchestration and batching system for Cronos blockchain.

## Overview

This module implements comprehensive multi-leg transaction management with:

- **Atomic Execution**: All legs succeed or all fail
- **Compensation Support**: Saga pattern for rollback/compensation
- **Batching Strategies**: Time-window, business logic, and gas optimization
- **Reconciliation**: On-chain vs off-chain state reconciliation
- **Audit Trails**: Complete audit logging for compliance
- **Idempotency**: Duplicate prevention via idempotency keys

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Multi-Leg Transaction System                │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────┐ │
│  │ Coordinator  │───▶│   Batching   │───▶│ Execution │ │
│  │              │    │   Service    │    │  Layer    │ │
│  └──────────────┘    └──────────────┘    └───────────┘ │
│         │                    │                   │       │
│         ▼                    ▼                   ▼       │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────┐ │
│  │   Database   │    │ Reconciliation│   │   x402    │ │
│  │   Models     │    │   Service     │   │ Executor  │ │
│  └──────────────┘    └──────────────┘    └───────────┘ │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Core Components

### 1. MultiLegCoordinator

Orchestrates multi-leg transactions with atomicity guarantees.

**Features:**
- Transaction creation with idempotency
- Sequential leg execution
- Atomic failure handling
- Compensation/rollback support
- Audit logging

**Example:**
```python
from multi_leg.coordinator import MultiLegCoordinator, CompensationStrategy

coordinator = MultiLegCoordinator(
    db_session=session,
    w3=web3,
    compensation_strategy=CompensationStrategy.SAGA
)

# Create transaction
transaction = coordinator.create_transaction(
    transaction_type="swap",
    initiator="0x...",
    legs=[
        {
            "type": "debit",
            "target_address": "0x...",
            "amount_in": "1000000000000000000",
            "token_in": "0x...",
            "requires_compensation": True
        },
        {
            "type": "swap",
            "target_address": "0x...",
            "amount_in": "1000000000000000000",
            "amount_out": "950000000000000000",
            "token_in": "0x...",
            "token_out": "0x...",
            "requires_compensation": True
        },
        {
            "type": "credit",
            "target_address": "0x...",
            "amount_out": "950000000000000000",
            "token_out": "0x...",
            "requires_compensation": False
        }
    ],
    idempotency_key="unique-key-123"
)

# Execute transaction
result = await coordinator.execute_transaction(
    transaction_id=transaction.transaction_id,
    atomic=True
)
```

### 2. BatchingService

Batches multiple transactions/legs for optimized execution.

**Strategies:**
- `TIME_WINDOW`: Batch by time window (e.g., every 60 seconds)
- `BUSINESS_LOGIC`: Batch by business context
- `GAS_OPTIMIZATION`: Batch for gas savings
- `SIZE_LIMIT`: Batch until size limit reached
- `HYBRID`: Combination of strategies

**Example:**
```python
from multi_leg.batching import BatchingService, BatchingStrategy

batching_service = BatchingService(
    db_session=session,
    w3=web3
)

# Add to batch
batch_id = batching_service.add_to_batch(
    transaction_id="mlt_...",
    batch_type="time_window",
    strategy=BatchingStrategy.TIME_WINDOW,
    time_window_seconds=60,
    max_size=100
)

# Execute batch
result = await batching_service.execute_batch(batch_id)
```

### 3. ReconciliationService

Reconciles on-chain state with off-chain records.

**Features:**
- On-chain transaction verification
- Discrepancy detection
- Automated reconciliation
- Audit records

**Example:**
```python
from multi_leg.reconciliation import ReconciliationService

reconciliation_service = ReconciliationService(
    db_session=session,
    w3=web3
)

# Reconcile transaction
result = await reconciliation_service.reconcile_transaction(
    transaction_id="mlt_...",
    on_chain_tx_hash="0x..."
)
```

## Database Models

### MultiLegTransaction
Main transaction record tracking the overall transaction state.

### TransactionLeg
Individual leg of a transaction with execution details.

### Batch
Batch record for grouped execution.

### BatchItem
Item within a batch (transaction or leg reference).

### AuditLog
Complete audit trail for compliance and debugging.

### ReconciliationRecord
On-chain vs off-chain reconciliation records.

## API Endpoints

### Create Multi-Leg Transaction
```http
POST /api/multi-leg/create
Content-Type: application/json

{
  "transaction_type": "swap",
  "initiator": "0x...",
  "legs": [
    {
      "type": "debit",
      "target_address": "0x...",
      "amount_in": "1000000000000000000",
      "token_in": "0x...",
      "requires_compensation": true
    }
  ],
  "idempotency_key": "unique-key-123"
}
```

### Execute Transaction
```http
POST /api/multi-leg/execute
Content-Type: application/json

{
  "transaction_id": "mlt_...",
  "atomic": true
}
```

### Add to Batch
```http
POST /api/batching/add
Content-Type: application/json

{
  "transaction_id": "mlt_...",
  "batch_type": "time_window",
  "strategy": "time_window",
  "time_window_seconds": 60,
  "max_size": 100
}
```

### Execute Batch
```http
POST /api/batching/{batch_id}/execute
```

### Reconcile Transaction
```http
POST /api/reconciliation/{transaction_id}?on_chain_tx_hash=0x...
```

## Smart Contract Integration

### MultiSend.sol

Gas-optimized multi-send contract for batching transfers:

```solidity
// Execute multiple native CRO transfers
function multiNativeSend(
    address[] calldata recipients,
    uint256[] calldata amounts
) external payable;

// Execute multiple ERC20 transfers
function multiTokenSend(
    address token,
    address[] calldata recipients,
    uint256[] calldata amounts
) external;

// Atomic batch execution via x402
function executeBatchAtomic(
    bytes32 batchId,
    Transfer[] calldata transfers,
    uint256 deadline
) external;
```

## Integration with Existing Systems

The multi-leg system integrates with:

1. **x402 Executor**: For atomic on-chain execution
2. **Pipeline Executor**: For complex multi-step pipelines
3. **AI Agent**: For route optimization
4. **Liquidity Monitor**: For pool data

See `integration.py` for integration examples.

## Best Practices

1. **Idempotency**: Always use idempotency keys for critical operations
2. **Compensation**: Mark legs that require compensation
3. **Deadlines**: Set appropriate deadlines for time-sensitive operations
4. **Batching**: Use batching for gas optimization
5. **Reconciliation**: Regularly reconcile on-chain vs off-chain state
6. **Audit Logs**: Review audit logs for compliance

## Gas Optimization

Batching can significantly reduce gas costs:

- **Individual transfers**: ~65,000 gas each
- **Batched transfers**: ~21,000 base + 5,000 per transfer
- **Savings**: ~39,000 gas per transfer in batch

Example: 10 transfers
- Individual: 650,000 gas
- Batched: 71,000 gas
- **Savings: 579,000 gas (89%)**

## Error Handling

The system supports multiple error handling strategies:

1. **Atomic Rollback**: All legs revert on failure
2. **Saga Compensation**: Execute compensating transactions
3. **Partial Success**: Allow partial execution (non-atomic mode)
4. **Manual Intervention**: Flag for manual review

## Monitoring & Metrics

Key metrics to monitor:

- Transaction success rate
- Average execution time
- Gas savings from batching
- Reconciliation discrepancies
- Compensation execution rate

## Security Considerations

1. **Access Control**: Restrict coordinator access
2. **Input Validation**: Validate all leg definitions
3. **Deadline Enforcement**: Enforce transaction deadlines
4. **Compensation Safety**: Ensure compensation logic is correct
5. **Audit Trails**: Maintain complete audit logs

## Future Enhancements

- [ ] Support for cross-chain multi-leg transactions
- [ ] Advanced compensation strategies
- [ ] Real-time reconciliation
- [ ] Machine learning for batching optimization
- [ ] Integration with Layer 2 solutions

## References

- [Saga Pattern](https://microservices.io/patterns/data/saga.html)
- [Atomic Transactions](https://en.wikipedia.org/wiki/Atomicity_(database_systems))
- [Gas Optimization](https://ethereum.org/en/developers/docs/gas/)
- [x402 Facilitator](https://docs.cronos.org/)

