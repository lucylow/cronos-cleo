# C.L.E.O. Quick Start Guide

Get up and running with C.L.E.O. in 5 minutes!

## Prerequisites

- Node.js 18+
- Python 3.11+
- A Cronos wallet with testnet CRO

## Quick Setup

### 1. Clone and Install

```bash
# Install frontend dependencies
npm install

# Install contract dependencies
cd cleo_project/contracts
npm install

# Install backend dependencies
cd ../backend
pip install -r requirements.txt
```

### 2. Get Testnet Tokens

1. Visit https://cronos.org/faucet
2. Get TCRO (Testnet CRO)
3. Visit https://faucet.cronos.org for devUSDC.e

### 3. Configure Environment

**Backend** (`cleo_project/backend/.env`):
```env
CRONOS_RPC=https://evm-t3.cronos.org
```

**Frontend** (`.env`):
```env
VITE_API_URL=http://localhost:8000
```

### 4. Start Services

**Terminal 1 - Backend:**
```bash
cd cleo_project/backend
python main.py
```

**Terminal 2 - Frontend:**
```bash
npm run dev
```

### 5. Test the System

1. Open http://localhost:5173
2. Connect your wallet (MetaMask with Cronos Testnet)
3. Try a small swap (e.g., 100 CRO → USDC.e)
4. Click "Find Optimal Route"
5. Review the optimization results
6. Execute the swap

## Deploy Contracts (Optional)

If you want to deploy your own contracts:

```bash
cd cleo_project/contracts

# Create .env file
echo "PRIVATE_KEY=your_key" > .env
echo "FEE_RECIPIENT=0xYourAddress" >> .env

# Deploy to testnet
npm run deploy:testnet
```

Update backend `.env` with your deployed router address:
```env
ROUTER_CONTRACT_ADDRESS=0xYourDeployedAddress
```

## Troubleshooting

**Backend won't start?**
- Check Python version: `python --version` (need 3.11+)
- Install dependencies: `pip install -r requirements.txt`

**Frontend can't connect?**
- Verify backend is running on port 8000
- Check `VITE_API_URL` in `.env`

**Wallet not connecting?**
- Add Cronos Testnet to MetaMask:
  - Network Name: Cronos Testnet
  - RPC URL: https://evm-t3.cronos.org
  - Chain ID: 338
  - Currency Symbol: TCRO

## Next Steps

- Read [DEPLOYMENT.md](./DEPLOYMENT.md) for full deployment guide
- Check [README.md](./README.md) for project overview
- Review contract code in `cleo_project/contracts/`
- Explore backend API at http://localhost:8000/docs

## Demo Video Script

For hackathon submission:

1. **0:00** - Show single DEX swap with high slippage
2. **0:30** - Demonstrate C.L.E.O. analyzing multiple DEXs
3. **1:00** - Show AI-optimized split (e.g., 60% VVS + 40% CronaSwap)
4. **1:30** - Execute via x402 (single transaction)
5. **2:00** - Show results: lower slippage, better execution
6. **2:30** - Highlight production-ready features

## Support

- [Cronos x402 Docs](https://docs.cronos.org/cronos-x402-facilitator)
- [x402 Examples](https://github.com/cronos-labs/x402-examples)
- Cronos Discord

