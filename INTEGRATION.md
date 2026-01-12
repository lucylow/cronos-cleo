# Backend-Frontend Integration Guide

This document explains how the backend and frontend are integrated in the C.L.E.O. project.

## Architecture Overview

```
┌─────────────────┐         HTTP/REST         ┌─────────────────┐
│   Frontend      │ ──────────────────────────> │    Backend       │
│   (React/TS)    │ <────────────────────────── │   (FastAPI)      │
└─────────────────┘                             └─────────────────┘
                                                         │
                                                         ▼
                                              ┌─────────────────┐
                                              │   AI Services    │
                                              │  - Route Opt.    │
                                              │  - Liquidity     │
                                              │  - Data Pipeline │
                                              └─────────────────┘
```

## Backend Structure

```
cleo_project/backend/
├── main.py                 # FastAPI server
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── README.md              # Backend documentation
├── run.sh / run.bat       # Startup scripts
└── ai/
    ├── __init__.py
    ├── ai_agent.py        # AI route optimizer
    ├── liquidity_monitor.py  # DEX pool monitor
    └── data_pipeline.py   # Data collection & training
```

## Frontend Integration

The frontend uses the API client in `src/lib/api.ts` to communicate with the backend:

### Key Functions

1. **`fetchPools(tokenIn, tokenOut)`** - Fetches available DEX pools
2. **`optimizeRoutes(request)`** - Calls AI agent to optimize route splits
3. **`simulateExecution(routes)`** - Simulates execution of routes
4. **`getLiquidityData(pair)`** - Gets liquidity data for a trading pair
5. **`checkHealth()`** - Checks backend connection status

### Usage in Components

The `CLEOFrontend` component automatically:
- Loads pools from backend on mount
- Uses AI optimization when routes are calculated
- Falls back to local calculations if backend is unavailable
- Shows connection status in the header

## API Endpoints

### GET `/health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "services": {
    "liquidity_monitor": true,
    "ai_agent": true,
    "data_pipeline": true
  }
}
```

### GET `/api/pools/{token_in}/{token_out}`
Get available pools for a token pair.

**Response:**
```json
{
  "pools": [
    {
      "dex": "vvs_finance",
      "pair": "CRO-USDC.e",
      "reserveIn": 1000000,
      "reserveOut": 500000,
      "feeBps": 25,
      "address": "0x..."
    }
  ]
}
```

### POST `/api/optimize`
Optimize route splits using AI agent.

**Request:**
```json
{
  "token_in": "CRO",
  "token_out": "USDC.e",
  "amount_in": 100000,
  "max_slippage": 0.005
}
```

**Response:**
```json
{
  "optimized_split": {...},
  "routes": [...],
  "predicted_improvement": 0.05,
  "risk_metrics": {...}
}
```

### POST `/api/simulate`
Simulate execution of routes.

**Request:**
```json
[
  {
    "id": "r_0",
    "dex": "vvs_finance",
    "amountIn": 50000,
    "estimatedOut": 25000,
    "path": ["CRO", "USDC.e"]
  }
]
```

**Response:**
```json
{
  "totalIn": 100000,
  "totalOut": 50000,
  "slippagePct": 0.5,
  "gasEstimate": 144000,
  "routeBreakdown": [...]
}
```

## Configuration

### Backend Environment Variables

Create `cleo_project/backend/.env`:

```env
CRONOS_RPC=https://evm-t3.cronos.org
CRYPTOCOM_MCP_KEY=your_key_here  # Optional
DATABASE_URL=sqlite:///./cleo_data.db
```

### Frontend Environment Variables

Create `.env` in project root:

```env
VITE_API_URL=http://localhost:8000
```

## Running the Integrated System

### Option 1: Manual (Two Terminals)

**Terminal 1 - Backend:**
```bash
cd cleo_project/backend
pip install -r requirements.txt
python main.py
```

**Terminal 2 - Frontend:**
```bash
npm install
npm run dev
```

### Option 2: Using Scripts

**Backend:**
```bash
cd cleo_project/backend
./run.sh  # Linux/Mac
# or
run.bat   # Windows
```

**Frontend:**
```bash
npm run dev
```

## Fallback Behavior

The frontend is designed to work even if the backend is unavailable:

1. **Pools**: Falls back to `MOCK_POOLS` if API fails
2. **Optimization**: Falls back to `suggestSplits()` local algorithm
3. **Simulation**: Falls back to local calculation
4. **Connection Status**: Shows red indicator when backend is offline

## Development Tips

1. **Backend Development**: Use `uvicorn main:app --reload` for auto-reload
2. **Frontend Development**: Vite hot-reloads automatically
3. **API Testing**: Visit `http://localhost:8000/docs` for Swagger UI
4. **Debugging**: Check browser console and backend logs

## Troubleshooting

### Backend won't start
- Check Python version (3.8+)
- Install dependencies: `pip install -r requirements.txt`
- Check port 8000 is available

### Frontend can't connect
- Verify backend is running on port 8000
- Check `VITE_API_URL` in `.env`
- Check CORS settings in `main.py`

### API calls failing
- Check backend logs for errors
- Verify network connectivity
- Check browser console for CORS errors

## Next Steps

- [ ] Add authentication/API keys
- [ ] Implement WebSocket for real-time updates
- [ ] Add rate limiting
- [ ] Set up production deployment
- [ ] Add monitoring and logging

