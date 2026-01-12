# Instruction Sets Module

## Overview

The Instruction Sets module implements recurring and conditional instruction sets for the Cronos CLEO (Cronos Liquidity Execution Orchestrator) system. This enables automated, scheduled execution of multi-step operations with conditional logic, perfect for x402 agentic finance use cases.

## Core Concept

Instruction sets are structured bundles that define:
- **Who pays whom, in what asset, how often, under what conditions, with what limits**
- **Recurring execution**: Execute multiple times (e.g., daily interest payments, weekly payroll, monthly streaming, scheduled rebalancing)
- **Conditional execution**: Each execution checks guardrails (price bands, health factors, KPIs, oracle states, governance flags) and only fires if predicates are true

## Architecture

### Components

1. **Models** (`models.py`)
   - `InstructionSet`: Complete instruction set with schedule, conditions, actions, and limits
   - `Condition`: Represents a condition that must be satisfied
   - `Action`: Represents an action to execute
   - `Schedule`: Schedule configuration for recurring execution
   - `Limits`: Safety limits and caps

2. **Condition Evaluator** (`condition_evaluator.py`)
   - Evaluates conditions (on-chain state, oracle prices, etc.)
   - Supports multiple condition types (price ranges, balances, vault utilization, health factors, etc.)

3. **Registry** (`registry.py`)
   - Manages instruction sets (create, update, execute, monitor)
   - Integrates with x402 executor and pipeline executor
   - Tracks execution history

### Instruction Set Types

- `RecurringPayment`: Recurring payment instructions
- `Payroll`: Payroll automation
- `Subscription`: Subscription payments
- `DEXRebalance`: DEX rebalancing instructions
- `YieldCompound`: Yield compounding automation
- `RiskManagedPortfolio`: Risk-managed portfolio instructions
- `ConditionalSettlement`: Conditional settlement pipelines
- `StreamingYield`: Streaming yield payments
- `NFTRental`: NFT rental fee payments
- `Custom`: Custom instruction sets

### Condition Types

- `TimeBased`: Time-based conditions (block.timestamp >= X)
- `PriceRange`: Price within range [min, max]
- `PriceThreshold`: Price >= X or price <= X
- `BalanceMin`: Balance >= X
- `BalanceMax`: Balance <= X
- `VaultUtilization`: Vault utilization within range
- `HealthFactor`: Health factor >= X
- `PoolLiquidity`: Pool liquidity >= X
- `Volatility`: Volatility <= X
- `ExternalFlag`: Off-chain signal
- `GovernanceFlag`: DAO/governance flag
- `OracleState`: Oracle feed state
- `Composite`: AND/OR of multiple conditions

### Action Types

- `Transfer`: Simple token transfer
- `Swap`: Single DEX swap
- `SwapMultiDEX`: Multi-DEX swap (x402)
- `LPDeposit`: LP token deposit
- `LPWithdraw`: LP token withdrawal
- `Stake`: Staking operation
- `Unstake`: Unstaking operation
- `Borrow`: Borrowing operation
- `Repay`: Repayment operation
- `Bridge`: Bridge operation
- `Compound`: Compound operation
- `Harvest`: Harvest operation
- `CustomCall`: Custom contract call
- `Pipeline`: Execute a settlement pipeline

## API Endpoints

### Create Instruction Set
```
POST /api/instruction-sets
Body: CreateInstructionSetRequest
```

### Get Instruction Set
```
GET /api/instruction-sets/{instruction_id}
```

### Get User Instruction Sets
```
GET /api/instruction-sets/user/{owner}
```

### Update Instruction Set
```
PUT /api/instruction-sets/{instruction_id}
Body: UpdateInstructionSetRequest
```

### Pause Instruction Set
```
POST /api/instruction-sets/{instruction_id}/pause
Query: owner
```

### Resume Instruction Set
```
POST /api/instruction-sets/{instruction_id}/resume
Query: owner
```

### Cancel Instruction Set
```
POST /api/instruction-sets/{instruction_id}/cancel
Query: owner
```

### Execute Instruction Set
```
POST /api/instruction-sets/{instruction_id}/execute
Body: ExecuteInstructionSetRequest
```

### Get Execution History
```
GET /api/instruction-sets/{instruction_id}/history?limit=50
```

### Get Due Instruction Sets
```
GET /api/instruction-sets/active/due
```

## Usage Examples

### Example 1: Recurring Payment
```python
{
    "owner": "0x...",
    "instruction_type": "RecurringPayment",
    "schedule": {
        "interval_seconds": 86400,  # Daily
        "next_execution": 1234567890,
        "max_executions": 365  # One year
    },
    "conditions": [
        {
            "condition_type": "BalanceMin",
            "parameters": {
                "token_address": "0x...",
                "address": "0x...",
                "min_balance": 1000000000000000000  # 1 token
            }
        }
    ],
    "actions": [
        {
            "action_type": "Transfer",
            "target": "0x...",
            "parameters": {
                "to": "0x...",
                "amount": 100000000000000000
            },
            "is_critical": true
        }
    ],
    "limits": {
        "max_notional_per_run": 1000000000000000000,
        "cumulative_cap": 36500000000000000000,
        "max_slippage_bps": 50
    }
}
```

### Example 2: Conditional DEX Rebalance
```python
{
    "owner": "0x...",
    "instruction_type": "DEXRebalance",
    "schedule": {
        "interval_seconds": 3600,  # Hourly
        "next_execution": 1234567890,
        "max_executions": None  # Unlimited
    },
    "conditions": [
        {
            "condition_type": "PriceRange",
            "parameters": {
                "pair": "CRO/USDC",
                "min_price": 0.05,
                "max_price": 0.15
            }
        },
        {
            "condition_type": "Volatility",
            "parameters": {
                "pair": "CRO/USDC",
                "max_volatility": 0.10  # 10%
            }
        }
    ],
    "actions": [
        {
            "action_type": "SwapMultiDEX",
            "target": "x402_router",
            "parameters": {
                "routes": [...],
                "token_in": "CRO",
                "token_out": "USDC",
                "amount_in": 1000000000000000000,
                "min_total_out": 50000000
            },
            "is_critical": true
        }
    ],
    "limits": {
        "max_notional_per_run": 10000000000000000000,
        "max_slippage_bps": 50,
        "max_gas_per_execution": 500000
    }
}
```

## Integration with x402

Instruction sets integrate seamlessly with the x402 settlement layer:
- Actions of type `SwapMultiDEX` are executed via the x402 executor
- Actions of type `Pipeline` are executed via the pipeline executor
- All actions within an instruction set are executed atomically (all-or-nothing)

## Safety Features

- **Limits**: Per-run and cumulative caps
- **Slippage Protection**: Max slippage limits
- **Gas Limits**: Max gas per execution
- **Circuit Breakers**: Emergency pause switches
- **Condition Evaluation**: All conditions must pass before execution
- **Execution History**: Full audit trail

## Future Enhancements

1. **On-Chain Storage**: Move instruction sets to smart contracts for transparency
2. **Keeper Network**: Decentralized keeper network for execution
3. **Advanced Conditions**: More sophisticated condition types
4. **Multi-Signature**: Multi-sig support for sensitive operations
5. **Gas Optimization**: Batch execution of multiple instruction sets
6. **Database Persistence**: Replace in-memory storage with database

## Security Considerations

- Private keys should be stored securely (use key management services in production)
- Instruction sets should be validated before execution
- Limits should be set conservatively
- Circuit breakers should be tested regularly
- Execution history should be monitored for anomalies
