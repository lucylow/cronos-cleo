# Frontend-Backend Integration Guide

This guide ensures the frontend and backend are fully integrated and working together.

## Configuration

### Backend Configuration

The backend runs on `http://localhost:8000` by default. CORS is configured to allow requests from:
- `http://localhost:8080` (Vite default)
- `http://localhost:5173` (Vite alternative port)
- `http://127.0.0.1:8080`
- `http://127.0.0.1:5173`
- `http://localhost:3000` (React dev server)

### Frontend Configuration

The frontend uses environment variables to configure the API URL:

**Create `.env` file in project root:**
```bash
VITE_API_URL=http://localhost:8000
```

If not set, defaults to `http://localhost:8000`.

## API Integration Points

### Core API Endpoints

1. **Health Check**
   - Frontend: `api.health()`
   - Backend: `GET /health`
   - Used by: `CLEOFrontend` component for connection status

2. **Route Optimization**
   - Frontend: `api.optimize(request)`
   - Backend: `POST /api/optimize`
   - Used by: `CLEOSwapInterface`, `CLEOFrontend`

3. **Pool Information**
   - Frontend: `api.getPools(tokenIn, tokenOut)`
   - Backend: `GET /api/pools/{token_in}/{token_out}`
   - Used by: `CLEOFrontend`

4. **Simulation**
   - Frontend: `api.simulate(routes)`
   - Backend: `POST /api/simulate`
   - Used by: `CLEOFrontend`

5. **Execution**
   - Frontend: `api.execute(request)`
   - Backend: `POST /api/execute`
   - Used by: `CLEOSwapInterface`

6. **Liquidity Data**
   - Frontend: `api.getLiquidity(pair)`
   - Backend: `GET /api/liquidity/{pair}`
   - Used by: `CLEOFrontend`

### Dashboard & Agent Endpoints

7. **Dashboard Metrics**
   - Frontend: `api.getDashboardMetrics()`
   - Backend: `GET /api/metrics/dashboard`
   - Used by: `Dashboard` page

8. **Agent Status**
   - Frontend: `api.getAgentStatus()`
   - Backend: `GET /api/agent/status`
   - Used by: `Agent` page

9. **Recent Executions**
   - Frontend: `api.getRecentExecutions(limit)`
   - Backend: `GET /api/executions/recent?limit={limit}`
   - Used by: `Dashboard` page

## Component Integration

### CLEOSwapInterface
- ✅ Uses `WalletProvider` hooks (not wagmi)
- ✅ Calls `api.optimize()` for route optimization
- ✅ Calls `api.execute()` for swap execution
- ✅ Handles errors gracefully

### CLEOFrontend
- ✅ Checks backend health on mount
- ✅ Falls back to local calculations if backend unavailable
- ✅ Uses `api.getPools()` for pool data
- ✅ Uses `api.optimize()` for AI optimization

### Dashboard
- ✅ Fetches metrics from `api.getDashboardMetrics()`
- ✅ Displays real-time data with auto-refresh
- ✅ Shows recent executions

### Agent
- ✅ Fetches status from `api.getAgentStatus()`
- ✅ Displays agent availability and statistics
- ✅ Shows recent decisions

## Running the Application

### 1. Start Backend

```bash
cd cleo_project/backend
python main.py
# Or: uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at `http://localhost:8000`

### 2. Start Frontend

```bash
npm run dev
```

Frontend will be available at `http://localhost:8080`

### 3. Verify Integration

1. Open browser console
2. Check for API connection status in the UI
3. Navigate to Dashboard - should show metrics
4. Navigate to Agent page - should show agent status
5. Try a swap in CLEOSwapInterface - should connect to backend

## Troubleshooting

### CORS Errors
- Ensure backend CORS includes your frontend port
- Check that `VITE_API_URL` matches backend URL
- Verify backend is running on the expected port

### Connection Issues
- Check backend health: `curl http://localhost:8000/health`
- Verify frontend can reach backend (check browser network tab)
- Ensure no firewall blocking localhost connections

### API Errors
- Check backend logs for detailed error messages
- Verify all required environment variables are set
- Check that services (liquidity monitor, AI agent) are initialized

## Environment Variables

### Backend (.env in `cleo_project/backend/`)

```bash
# Cronos RPC
CRONOS_RPC=https://evm-t3.cronos.org

# Contract Addresses (optional)
ROUTER_CONTRACT_ADDRESS=0x...
SETTLEMENT_PIPELINE_CONTRACT=0x...

# Multi-agent System (optional)
ORCHESTRATOR_PRIVATE_KEY=...
X402_FACILITATOR=0x...
REDIS_URL=redis://localhost:6379

# Executor (optional)
EXECUTOR_PRIVATE_KEY=...
```

### Frontend (.env in project root)

```bash
# Backend API URL
VITE_API_URL=http://localhost:8000

# Router Contract (optional)
VITE_ROUTER_ADDRESS=0x...
```

## Integration Checklist

- ✅ CORS configured correctly
- ✅ Frontend API client implemented
- ✅ All core endpoints integrated
- ✅ Dashboard connected to backend
- ✅ Agent page connected to backend
- ✅ Error handling in place
- ✅ Wallet integration working
- ✅ Health check implemented
- ✅ Fallback mechanisms for offline backend
