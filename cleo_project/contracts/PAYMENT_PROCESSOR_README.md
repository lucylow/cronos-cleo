# Cronos Payment Processor

Complete payment processing system for accepting native CRO and ERC-20 token payments on Cronos blockchain.

## Overview

This system provides:
- **Smart Contract**: `CronosPaymentProcessor.sol` - Accepts native CRO and ERC-20 payments
- **Frontend Component**: React component with wallet integration
- **Backend API**: FastAPI endpoints for payment verification
- **Deployment Scripts**: Hardhat scripts for deploying to Cronos testnet/mainnet

## Quick Start

### 1. Deploy the Contract

```bash
cd cleo_project/contracts

# Create .env file with your private key
echo "PRIVATE_KEY=your_private_key_here" > .env
echo "CRONOS_TESTNET_RPC=https://evm-t3.cronos.org" >> .env

# Deploy to testnet
npm run deploy:payment:testnet

# Or deploy to mainnet
npm run deploy:payment:mainnet
```

After deployment, you'll get:
- Contract address
- Deployment info saved to `deployments/payment-{network}.json`
- ABI saved to `abi/CronosPaymentProcessor.json`

### 2. Configure Backend

Update `cleo_project/backend/.env`:
```env
PAYMENT_CONTRACT_ADDRESS=0xYourDeployedContractAddress
CRONOS_RPC=https://evm-t3.cronos.org  # or mainnet RPC
```

### 3. Configure Frontend

Update `.env` (in project root):
```env
VITE_PAYMENT_CONTRACT_ADDRESS=0xYourDeployedContractAddress
VITE_API_URL=http://localhost:8000
```

### 4. Use the Payment Component

Import and use in your React app:

```tsx
import PaymentProcessor from "./components/PaymentProcessor";

function App() {
  return <PaymentProcessor />;
}
```

## Smart Contract Features

### Functions

- **`payNative()`**: Accept native CRO payments (payable function)
- **`payWithERC20(address token, uint256 amount)`**: Accept ERC-20 token payments
- **`withdraw(address payable to, address token, uint256 amount)`**: Owner can withdraw collected payments
- **`getPayment(uint256 paymentId)`**: Query payment details by ID
- **`getNativeBalance()`**: Get contract's CRO balance

### Events

- **`PaymentReceived(uint256 indexed paymentId, address indexed payer, address token, uint256 amount)`**: Emitted on each payment

## Frontend Usage

The `PaymentProcessor` component provides:

1. **Wallet Connection**: Connects to MetaMask/Cronos wallet
2. **Network Switching**: Automatically switches to Cronos network
3. **Native CRO Payments**: Simple interface for paying with CRO
4. **ERC-20 Payments**: Support for any ERC-20 token
5. **Payment Verification**: Automatically verifies payments via backend
6. **Transaction Tracking**: Links to Cronoscan for transaction viewing

### Example

```tsx
<PaymentProcessor />
```

Users can:
- Switch between native CRO and ERC-20 payment tabs
- Enter amount and token address (for ERC-20)
- Execute payment transactions
- View transaction status and links

## Backend API

### Verify Payment

```http
POST /api/payments/verify
Content-Type: application/json

{
  "tx_hash": "0x...",
  "token_address": "0x..." | null,  // null for native CRO
  "expected_recipient": "0x...",     // optional
  "min_amount_wei": "1000000000000000000"  // optional
}
```

Response:
```json
{
  "ok": true,
  "result": {
    "receipt": {...},
    "parsed": {...},
    "tx": {...}
  }
}
```

### Get Contract Info

```http
GET /api/payments/contract-info
```

Response:
```json
{
  "contract_address": "0x...",
  "payment_count": 42,
  "owner": "0x..."
}
```

## ERC-20 Payment Flow

1. **Approve**: User must approve the payment contract to spend tokens
   ```solidity
   token.approve(paymentContractAddress, amount)
   ```

2. **Pay**: Call `payWithERC20` on the payment contract
   ```solidity
   paymentContract.payWithERC20(tokenAddress, amount)
   ```

The frontend component handles approval automatically.

## Network Configuration

### Cronos Testnet
- **Chain ID**: 338
- **RPC**: `https://evm-t3.cronos.org`
- **Explorer**: `https://testnet.cronoscan.com`
- **Faucet**: `https://cronos.org/faucet`

### Cronos Mainnet
- **Chain ID**: 25
- **RPC**: `https://evm.cronos.org`
- **Explorer**: `https://cronoscan.com`

## Security Considerations

1. **Owner Controls**: Only contract owner can withdraw funds
2. **Payment Verification**: Always verify payments on the backend
3. **Token Approval**: Users must explicitly approve token spending
4. **Event Listening**: Use contract events for reliable payment tracking
5. **Gas Limits**: Set appropriate gas limits for transactions

## Testing

### On Testnet

1. Get testnet CRO from faucet: https://cronos.org/faucet
2. Deploy contract to testnet
3. Use testnet ERC-20 tokens (e.g., devUSDC.e from testnet faucet)
4. Test payment flows

### Example Testnet Tokens

- **USDC.e (Testnet)**: Available from testnet faucet
- **USDT.e (Testnet)**: Available from testnet faucet

## Integration with Existing System

The payment processor integrates with:
- **C.L.E.O. Backend**: Payment verification endpoints
- **Wallet Provider**: Uses existing wallet connection
- **API Client**: Uses existing API utilities

## Troubleshooting

### Contract Not Deploying
- Check private key in `.env`
- Verify RPC endpoint is accessible
- Ensure sufficient CRO balance for gas

### Payments Failing
- Verify contract address is correct
- Check user has sufficient balance
- For ERC-20: Ensure approval was successful
- Check gas limits are sufficient

### Backend Verification Failing
- Verify `PAYMENT_CONTRACT_ADDRESS` in backend `.env`
- Check RPC connection in backend
- Verify transaction has been confirmed on-chain

## Next Steps

1. **Add Payment Webhooks**: Watch `PaymentReceived` events and trigger webhooks
2. **Payment History**: Query contract for all payments by address
3. **Multi-Signature Withdrawals**: Add multi-sig for owner withdrawals
4. **Payment Refunds**: Implement refund mechanism
5. **Gasless Transactions**: Integrate with meta-transaction relayers

## License

MIT
