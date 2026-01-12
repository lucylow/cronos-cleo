# C.L.E.O. Deployment Guide

Complete deployment guide for the Cross-DEX Intelligent Settlement Engine.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Smart Contract Deployment](#smart-contract-deployment)
3. [Backend Setup](#backend-setup)
4. [Frontend Setup](#frontend-setup)
5. [Environment Configuration](#environment-configuration)
6. [Testing](#testing)
7. [Production Deployment](#production-deployment)

## Prerequisites

### Required Software

- **Node.js** 18+ and npm
- **Python** 3.11+
- **Hardhat** (for contract deployment)
- **Git**

### Required Accounts & Keys

- Cronos Testnet/Mainnet wallet with CRO for gas
- Private key for contract deployment (keep secure!)
- Cronoscan API key (for contract verification)

## Smart Contract Deployment

### 1. Install Dependencies

```bash
cd cleo_project/contracts
npm install
```

### 2. Configure Environment

Create a `.env` file in `cleo_project/contracts/`:

```env
# Network RPC URLs
CRONOS_TESTNET_RPC=https://evm-t3.cronos.org
CRONOS_MAINNET_RPC=https://evm.cronos.org

# Deployer Private Key (NEVER commit this!)
PRIVATE_KEY=your_private_key_here

# Fee Recipient Address
FEE_RECIPIENT=0xYourFeeRecipientAddress

# Cronoscan API Key (for verification)
CRONOSCAN_API_KEY=your_api_key_here

# x402 Facilitator Addresses
# Update these with actual facilitator addresses from Cronos docs
X402_FACILITATOR_TESTNET=0x0000000000000000000000000000000000000000
X402_FACILITATOR_MAINNET=0x0000000000000000000000000000000000000000
```

### 3. Update Facilitator Addresses

**IMPORTANT**: Before deploying, update the facilitator addresses in `scripts/deploy.js`:

```javascript
const FACILITATOR_ADDRESSES = {
  338: "0x...", // Cronos Testnet - Get from Cronos x402 docs
  25: "0x...",  // Cronos Mainnet - Get from Cronos x402 docs
};
```

Get the latest facilitator addresses from:
- [Cronos x402 Documentation](https://docs.cronos.org/cronos-x402-facilitator/introduction)
- [Cronos x402 Examples](https://github.com/cronos-labs/x402-examples)

### 4. Deploy to Testnet

```bash
# Compile contracts
npm run compile

# Deploy to Cronos Testnet
npm run deploy:testnet
```

The deployment script will:
- Deploy the CLECORouter contract
- Save deployment info to `deployments/` directory
- Optionally verify the contract on Cronoscan

### 5. Verify Deployment

After deployment, you'll see output like:

```
✅ CLECORouter deployed to: 0x...
📄 Deployment info saved to: deployments/cronos_testnet-1234567890.json
```

Check the contract on Cronoscan:
- Testnet: https://testnet.cronoscan.com/address/YOUR_CONTRACT_ADDRESS
- Mainnet: https://cronoscan.com/address/YOUR_CONTRACT_ADDRESS

### 6. Register DEX Routers

After deployment, register DEX routers (this requires owner privileges):

```javascript
// Using Hardhat console or a script
const router = await ethers.getContractAt("CLECORouter", "YOUR_ROUTER_ADDRESS");

// Register VVS Finance
await router.registerDEX(
  "vvs",
  "0x145863Eb42Cf62847A6Ca784e6416C1682B1b2Ae", // VVS Router
  "0x38ed1739" // swapExactTokensForTokens selector
);

// Register CronaSwap
await router.registerDEX(
  "cronaswap",
  "0xcd7d16fB918511BF72679eC3eC2f2f39c33C2F45", // CronaSwap Router
  "0x38ed1739"
);
```

## Backend Setup

### 1. Install Dependencies

```bash
cd cleo_project/backend
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in `cleo_project/backend/`:

```env
# Cronos RPC
CRONOS_RPC=https://evm-t3.cronos.org

# Router Contract Address (from deployment)
ROUTER_CONTRACT_ADDRESS=0xYourDeployedRouterAddress

# Executor Private Key (for executing swaps - keep secure!)
EXECUTOR_PRIVATE_KEY=your_executor_private_key

# Optional: Multi-agent system
ORCHESTRATOR_PRIVATE_KEY=your_orchestrator_key
X402_FACILITATOR=0xFacilitatorAddress
REDIS_URL=redis://localhost:6379

# Optional: Pipeline executor
SETTLEMENT_PIPELINE_CONTRACT=0xPipelineContractAddress

# Database (optional, for historical data)
DATABASE_URL=postgresql://user:password@localhost/cleo

# MCP Client (Crypto.com API)
CRYPTOCOM_MCP_KEY=your_mcp_api_key
```

### 3. Run Backend

```bash
# Development mode
python main.py

# Or with uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The backend will be available at `http://localhost:8000`

### 4. Verify Backend Health

```bash
curl http://localhost:8000/health
```

Should return:
```json
{
  "status": "healthy",
  "services": {
    "liquidity_monitor": true,
    "ai_agent": true,
    "data_pipeline": true,
    "mcp_client": true,
    "x402_executor": true
  }
}
```

## Frontend Setup

### 1. Install Dependencies

```bash
# From project root
npm install
```

### 2. Configure Environment

Create a `.env` file in the project root:

```env
# Backend API URL
VITE_API_URL=http://localhost:8000

# Router Contract Address
VITE_ROUTER_ADDRESS=0xYourDeployedRouterAddress

# Cronos Network
VITE_CHAIN_ID=338  # 338 for testnet, 25 for mainnet
VITE_RPC_URL=https://evm-t3.cronos.org
```

### 3. Run Frontend

```bash
npm run dev
```

The frontend will be available at `http://localhost:5173`

## Environment Configuration

### Complete `.env` Example

**Backend** (`cleo_project/backend/.env`):
```env
CRONOS_RPC=https://evm-t3.cronos.org
ROUTER_CONTRACT_ADDRESS=0xYourRouterAddress
EXECUTOR_PRIVATE_KEY=your_key
CRYPTOCOM_MCP_KEY=your_mcp_key
```

**Frontend** (`.env`):
```env
VITE_API_URL=http://localhost:8000
VITE_ROUTER_ADDRESS=0xYourRouterAddress
VITE_CHAIN_ID=338
```

**Contracts** (`cleo_project/contracts/.env`):
```env
PRIVATE_KEY=your_deployer_key
FEE_RECIPIENT=0xYourFeeRecipient
CRONOSCAN_API_KEY=your_api_key
```

## Testing

### Smart Contract Tests

```bash
cd cleo_project/contracts
npm test
```

### Backend Tests

```bash
cd cleo_project/backend
pytest tests/  # If tests are added
```

### Integration Testing

1. Deploy to testnet
2. Get test tokens from faucets:
   - TCRO: https://cronos.org/faucet
   - devUSDC.e: https://faucet.cronos.org
3. Test swap through frontend
4. Verify transaction on Cronoscan

## Production Deployment

### Security Checklist

- [ ] Use secure key management (not plain .env files)
- [ ] Enable rate limiting on API
- [ ] Use HTTPS for all endpoints
- [ ] Enable CORS only for trusted domains
- [ ] Audit smart contracts
- [ ] Set appropriate gas limits
- [ ] Monitor for unusual activity
- [ ] Set up alerts for failed transactions

### Recommended Infrastructure

**Backend:**
- Docker containerization
- Load balancer (nginx/HAProxy)
- Redis for caching
- PostgreSQL for historical data
- Monitoring (Prometheus/Grafana)

**Frontend:**
- Vercel/Netlify for static hosting
- CDN for assets
- Environment-specific builds

### Deployment Steps

1. **Deploy Contracts to Mainnet**
   ```bash
   npm run deploy:mainnet
   ```

2. **Update Backend Environment**
   - Switch to mainnet RPC
   - Update contract addresses
   - Configure production database

3. **Deploy Backend**
   - Use Docker or cloud service (AWS/GCP/Azure)
   - Set up environment variables securely
   - Configure monitoring

4. **Deploy Frontend**
   - Build production bundle: `npm run build`
   - Deploy to hosting service
   - Update environment variables

5. **Post-Deployment**
   - Verify all services are running
   - Test with small amounts first
   - Monitor for errors
   - Gradually increase limits

## Troubleshooting

### Contract Deployment Fails

- Check RPC URL is correct
- Ensure wallet has enough CRO for gas
- Verify facilitator address is correct
- Check contract compilation for errors

### Backend Won't Start

- Verify Python version (3.11+)
- Check all dependencies installed
- Verify environment variables set
- Check RPC connection: `curl $CRONOS_RPC`

### Frontend Can't Connect

- Verify backend is running
- Check CORS settings
- Verify API URL in `.env`
- Check browser console for errors

### Swaps Failing

- Check token approvals
- Verify router contract address
- Check slippage settings
- Ensure sufficient liquidity
- Verify facilitator is working

## Support

For issues or questions:
- Check [Cronos x402 Documentation](https://docs.cronos.org/cronos-x402-facilitator)
- Join Cronos Discord
- Review [x402 Examples](https://github.com/cronos-labs/x402-examples)

## Next Steps

After successful deployment:

1. Register additional DEX routers
2. Fine-tune AI model with historical data
3. Set up monitoring and alerts
4. Optimize gas costs
5. Add more token pairs
6. Implement advanced features (recurring swaps, limit orders, etc.)

