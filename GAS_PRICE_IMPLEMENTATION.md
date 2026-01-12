# Gas Price Handling Implementation

Complete implementation of gas price handling for Cronos, including EIP-1559 support, gas estimation, transaction sending, and monitoring.

## Backend Implementation (Python/FastAPI)

### Files Created

1. **`cleo_project/backend/gas_utils.py`**
   - Gas recommendation utilities
   - Supports EIP-1559 (maxFeePerGas, maxPriorityFeePerGas) and legacy gasPrice
   - Falls back to third-party APIs or safe defaults
   - Detects EIP-1559 support by checking block baseFeePerGas

2. **`cleo_project/backend/gas_estimate.py`**
   - Gas limit estimation with configurable safety buffer (default 20%)
   - Caps gas limit to prevent runaway transactions

3. **`cleo_project/backend/tx_sender.py`**
   - Broadcast signed transactions
   - Send transactions from server wallet (requires DEPLOY_PRIVATE_KEY)
   - Automatically applies optimal gas settings based on chain support

4. **`cleo_project/backend/monitor.py`**
   - Poll transaction receipts until confirmation
   - Configurable confirmation count and timeout

5. **`cleo_project/backend/verify_payment.py`**
   - Verify native (CRO) payments
   - Verify ERC20 token payments via Transfer event logs

### API Endpoints Added to `main.py`

- `GET /api/gas/recommendation` - Get current gas price recommendations
- `POST /api/gas/estimate` - Estimate gas limit for a transaction
- `POST /api/tx/send` - Send transaction (signed or server-signed)
- `POST /api/tx/monitor` - Monitor transaction until confirmation
- `POST /api/payments/verify` - Verify payment transactions

## Frontend Implementation (React/TypeScript)

### Files Created

1. **`src/hooks/useGas.ts`**
   - React hook for polling gas recommendations
   - Configurable polling interval (default 10 seconds)
   - Auto-refetch on mount and interval

2. **`src/components/GasPriceSelector.tsx`**
   - UI component with Slow/Normal/Fast presets
   - Live gas price display
   - Estimated transaction cost calculator
   - Supports both EIP-1559 and legacy gas pricing

### API Functions Added to `src/lib/api.ts`

- `getGasRecommendation()` - Fetch gas recommendations
- `estimateGas()` - Estimate gas limit
- `sendTransaction()` - Send transaction
- `monitorTransaction()` - Monitor transaction
- `verifyPayment()` - Verify payment

## Usage Examples

### Backend (Python)

```python
from gas_utils import get_gas_recommendation
from gas_estimate import estimate_gas_limit
from tx_sender import send_signed_transaction

# Get gas recommendation
rec = await get_gas_recommendation()
print(f"Supports EIP-1559: {rec['supports1559']}")
print(f"Max Fee: {rec['maxFeePerGas']}")

# Estimate gas
tx_req = {
    'to': '0x...',
    'data': '0x...',
    'value': 0,
    'from': '0x...'
}
gas_limit = await estimate_gas_limit(tx_req, buffer_percent=20)
```

### Frontend (React)

```tsx
import { GasPriceSelector } from './components/GasPriceSelector';
import { useGas } from './hooks/useGas';

function MyComponent() {
  const { gas, loading } = useGas({ interval: 10000 });
  
  return (
    <GasPriceSelector
      onPresetChange={(preset) => console.log('Selected:', preset)}
      onGasParamsChange={(params) => {
        // Use params.maxFeePerGas, params.maxPriorityFeePerGas, etc.
      }}
    />
  );
}
```

## Environment Variables

Add to `.env`:

```bash
# Cronos RPC URL
CRONOS_RPC=https://evm-t3.cronos.org  # Testnet
# CRONOS_RPC=https://evm.cronos.org  # Mainnet

# Optional: Server wallet for sending transactions
DEPLOY_PRIVATE_KEY=your_private_key_here
```

## Features

✅ EIP-1559 support detection  
✅ Legacy gasPrice fallback  
✅ Gas limit estimation with safety buffer  
✅ Transaction sending (client-signed or server-signed)  
✅ Transaction monitoring with confirmations  
✅ Payment verification (native and ERC20)  
✅ React hook for live gas price polling  
✅ UI component with Slow/Normal/Fast presets  
✅ Estimated transaction cost display  

## Testing

1. Start backend:
```bash
cd cleo_project/backend
python main.py
```

2. Test gas recommendation:
```bash
curl http://localhost:8000/api/gas/recommendation
```

3. Use the GasPriceSelector component in your React app to see live gas prices.

## Notes

- Cronos uses EIP-1559 style fee market (base fee + priority fee)
- Always use `estimateGas` before sending transactions
- Add 20-30% buffer to gas estimates for safety
- For production, use reliable RPC providers (not public RPCs)
- Never commit private keys to version control
