# Intelligent Settlement Integration

This document describes the Intelligent Settlement system integrated into C.L.E.O., which provides escrow-based settlement with milestone releases, AI agent orchestration, and x402 facilitator integration.

## Overview

The Intelligent Settlement system enables:
- **Multi-party escrow** (buyer, seller, optional arbitrator)
- **Milestone-based settlement** with automatic releases
- **Deadline-based auto-refund** if conditions aren't met
- **AI agent-driven settlement** via authorized agents
- **x402 facilitator integration** for verified payments
- **Safe ERC-20 and native token settlement**

## Architecture

```
User/DApp
    ↓
Create Deal (with milestones)
    ↓
Fund Deal (ERC20 or native)
    ↓
AI Agent / x402 Facilitator
    ↓
Monitor Conditions (off-chain/on-chain)
    ↓
Release Milestones (when conditions met)
    ↓
Automatic Settlement or Refund
```

## Components

### 1. Smart Contract (`IntelligentSettlement.sol`)

Located in `cleo_project/contracts/IntelligentSettlement.sol`

**Key Features:**
- Deal creation with customizable milestones
- Partial or full funding support
- Agent-driven milestone releases
- Arbitrator dispute resolution
- Deadline-based refunds
- Protocol fee collection

**Main Functions:**
- `createDeal()`: Create a new settlement deal
- `fundDeal()`: Fund a deal (can be done incrementally)
- `agentReleaseMilestone()`: Release milestone (agent-only)
- `arbitratorResolve()`: Resolve disputes (arbitrator-only)
- `refundAfterDeadline()`: Refund if deadline passed

### 2. Python Service (`intelligent_settlement.py`)

Located in `cleo_project/backend/intelligent_settlement.py`

**Responsibilities:**
- Contract interaction via Web3
- Transaction building and signing
- Deal state queries
- Milestone management

### 3. Settlement Agent (`intelligent_settlement_agent.py`)

Located in `cleo_project/backend/intelligent_settlement_agent.py`

**Responsibilities:**
- Monitor active deals
- Check milestone conditions
- Automatically release milestones when conditions are met
- Integrate with x402 facilitator for verification
- Custom condition checking

### 4. API Endpoints

All endpoints are under `/api/intelligent-settlement/`:

- `POST /create-deal`: Create a new deal
- `POST /fund-deal`: Fund an existing deal
- `POST /release-milestone`: Release a milestone (agent)
- `GET /deal/{deal_id}`: Get deal information
- `POST /refund`: Refund after deadline
- `GET /agent-address`: Get authorized agent address
- `POST /register-deal/{deal_id}`: Register deal for monitoring
- `GET /check-conditions/{deal_id}`: Check milestone conditions

## Setup

### 1. Deploy Smart Contract

```bash
cd cleo_project/contracts
npm install
npx hardhat compile
npx hardhat run scripts/deploy.js --network cronos-testnet
```

The deployment script will deploy both `CLECORouter` and `IntelligentSettlement` contracts.

### 2. Environment Variables

Add to your `.env` file:

```bash
# Intelligent Settlement Contract
INTELLIGENT_SETTLEMENT_CONTRACT=0x...  # Deployed contract address

# Settlement Agent (authorized agent for milestone releases)
SETTLEMENT_AGENT_PRIVATE_KEY=0x...  # Private key of authorized agent
SETTLEMENT_AGENT_ADDRESS=0x...  # Address of authorized agent (optional, defaults to deployer)

# Settlement Agent Configuration
SETTLEMENT_AUTO_RELEASE=true  # Enable automatic milestone releases
SETTLEMENT_CHECK_INTERVAL=60  # Check interval in seconds
```

### 3. Configure Authorized Agent

After deployment, the contract owner must set the authorized agent:

```solidity
// In Remix or via script
settlement.setAuthorizedAgent(0xYourAgentAddress);
```

Or use the backend API if the owner key is configured.

## Usage Examples

### Creating a Deal

```python
POST /api/intelligent-settlement/create-deal
{
    "seller": "0xSellerAddress",
    "token": "0x0",  # Native CRO, or ERC20 address
    "total_amount": 1000000000000000000,  # 1 CRO in wei
    "deadline": 1735689600,  # Unix timestamp
    "milestone_amounts": [500000000000000000, 500000000000000000],  # Two 0.5 CRO milestones
    "fee_bps": 25,  # 0.25% protocol fee
    "arbitrator": "0xArbitratorAddress"  # Optional
}
```

### Funding a Deal

```python
POST /api/intelligent-settlement/fund-deal
{
    "deal_id": 1,
    "amount": 1000000000000000000,  # 1 CRO in wei
    "is_native": true  # true for CRO, false for ERC20
}
```

### Releasing a Milestone (Agent)

```python
POST /api/intelligent-settlement/release-milestone
{
    "deal_id": 1,
    "milestone_index": 0,
    "min_seller_amount": 495000000000000000,  # 0.495 CRO (with slippage protection)
    "agent_nonce": 1  # Must be deal.agentNonce + 1
}
```

### Registering for Automated Monitoring

```python
POST /api/intelligent-settlement/register-deal/1
```

The settlement agent will automatically:
1. Monitor the deal status
2. Check milestone conditions
3. Release milestones when conditions are met

## Integration with x402 Facilitator

The settlement agent can integrate with x402 facilitator to verify payment intents:

```python
from intelligent_settlement_agent import create_x402_condition_checker

# Create x402-based condition checker
condition_checker = await create_x402_condition_checker(
    x402_executor=x402_executor,
    deal_id=deal_id,
    verification_data={
        "required_time": 3600,  # Wait 1 hour after deal creation
        # Add other x402 verification parameters
    }
)

# Register deal with x402 condition checker
settlement_agent.register_deal(
    deal_id=deal_id,
    condition_checker=condition_checker
)
```

## Custom Condition Checking

You can implement custom condition checkers for milestone releases:

```python
async def custom_condition_checker(
    deal_id: int,
    milestone_index: int,
    deal: Dict[str, Any],
    milestone: Dict[str, Any]
) -> bool:
    """
    Custom logic to determine if milestone should be released
    
    Examples:
    - Check delivery confirmation (off-chain API)
    - Verify KYC status
    - Check oracle data
    - Verify risk scores
    - Check on-chain events
    """
    # Your custom logic here
    return True  # or False

# Register with settlement agent
settlement_agent.register_deal(
    deal_id=deal_id,
    condition_checker=custom_condition_checker
)
```

## Workflow Examples

### Example 1: Service Payment with Delivery Confirmation

1. **Buyer creates deal** with 2 milestones:
   - 50% on order confirmation
   - 50% on delivery confirmation

2. **Buyer funds deal** with full amount

3. **AI agent monitors** for delivery confirmation (off-chain API/webhook)

4. **Agent releases milestones** automatically when conditions met

### Example 2: x402-Verified Payment

1. **Buyer creates deal** for payment to seller

2. **x402 facilitator verifies** payment intent and conditions

3. **Settlement agent** checks x402 verification status

4. **Agent releases milestone** when x402 confirms

### Example 3: Time-Based Milestone Release

1. **Buyer creates deal** with time-based milestones

2. **Settlement agent** monitors deal age

3. **Agent releases milestones** after required time periods

## Security Considerations

1. **Authorized Agent**: Only the authorized agent can release milestones. Protect the agent private key.

2. **Nonce Protection**: Each milestone release requires a monotonic nonce to prevent replay attacks.

3. **Slippage Protection**: `min_seller_amount` parameter protects against calculation errors.

4. **Deadline Protection**: Buyers can always refund after deadline if deal isn't completed.

5. **Arbitrator**: Optional arbitrator can resolve disputes if needed.

## Testing

```bash
# Test contract deployment
cd cleo_project/contracts
npx hardhat test

# Test backend service
cd cleo_project/backend
python -m pytest tests/test_intelligent_settlement.py
```

## Production Checklist

- [ ] Deploy contract to Cronos mainnet
- [ ] Set authorized agent address
- [ ] Configure protocol treasury
- [ ] Set up monitoring and alerting
- [ ] Implement custom condition checkers
- [ ] Integrate with x402 facilitator
- [ ] Set up backup agent keys
- [ ] Configure gas price limits
- [ ] Set up deal analytics

## Related Documentation

- [x402 Integration Guide](./X402_INTEGRATION.md)
- [Settlement Pipelines](./SETTLEMENT_PIPELINES.md)
- [Cronos x402 Documentation](https://docs.cronos.org/cronos-x402-facilitator/introduction)
