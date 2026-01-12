/**
 * API client for C.L.E.O. backend
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface PoolInfo {
  dex: string;
  pair: string;
  reserveIn: number;
  reserveOut: number;
  feeBps: number;
  address?: string;
}

export interface SplitRoute {
  id: string;
  dex: string;
  amountIn: number;
  estimatedOut: number;
  path: string[];
  pool_address?: string;
}

export interface SimulationResult {
  totalIn: number;
  totalOut: number;
  slippagePct: number;
  gasEstimate: number;
  routeBreakdown: SplitRoute[];
}

export interface OptimizeRequest {
  token_in: string;
  token_out: string;
  amount_in: number;
  max_slippage?: number;
}

export interface OptimizeResponse {
  optimized_split: any;
  routes: SplitRoute[];
  predicted_improvement: number;
  risk_metrics: any;
}

/**
 * Fetch pools for a token pair
 */
export async function fetchPools(tokenIn: string, tokenOut: string): Promise<PoolInfo[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/pools/${tokenIn}/${tokenOut}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch pools: ${response.statusText}`);
    }
    const data = await response.json();
    return data.pools || [];
  } catch (error) {
    console.error('Error fetching pools:', error);
    // Return empty array on error - frontend can use mock data as fallback
    return [];
  }
}

/**
 * Optimize routes using AI agent
 */
export async function optimizeRoutes(request: OptimizeRequest): Promise<OptimizeResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/optimize`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        token_in: request.token_in,
        token_out: request.token_out,
        amount_in: request.amount_in,
        max_slippage: request.max_slippage || 0.005,
      }),
    });

    if (!response.ok) {
      throw new Error(`Optimization failed: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error optimizing routes:', error);
    throw error;
  }
}

/**
 * Simulate execution of routes
 */
export async function simulateExecution(routes: SplitRoute[]): Promise<SimulationResult> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/simulate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(routes),
    });

    if (!response.ok) {
      throw new Error(`Simulation failed: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error simulating execution:', error);
    throw error;
  }
}

/**
 * Get liquidity data for a trading pair
 */
export async function getLiquidityData(pair: string): Promise<any> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/liquidity/${pair}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch liquidity: ${response.statusText}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching liquidity data:', error);
    return null;
  }
}

/**
 * Execute optimized swap
 */
export async function executeSwap(request: OptimizeRequest): Promise<any> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        token_in: request.token_in,
        token_out: request.token_out,
        amount_in: request.amount_in,
        max_slippage: request.max_slippage || 0.005,
      }),
    });

    if (!response.ok) {
      throw new Error(`Execution failed: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error executing swap:', error);
    throw error;
  }
}

/**
 * Health check
 */
export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/health`);
    return response.ok;
  } catch (error) {
    return false;
  }
}

// Export API object for convenience
export const api = {
  optimize: optimizeRoutes,
  execute: executeSwap,
  simulate: simulateExecution,
  getPools: fetchPools,
  getLiquidity: getLiquidityData,
  health: checkHealth,
};

