/**
 * Enhanced API client for C.L.E.O. backend
 * Features:
 * - Retry logic with exponential backoff
 * - Request timeout handling
 * - Structured error responses
 * - Request cancellation support
 * - Response caching
 * - Type-safe responses
 */

// Get API base URL from environment or use default
const getApiBaseUrl = (): string => {
  if (typeof window !== 'undefined' && (window as any).__API_BASE_URL__) {
    return (window as any).__API_BASE_URL__;
  }
  // Vite environment variable
  try {
    return (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000';
  } catch {
    return 'http://localhost:8000';
  }
};

const API_BASE_URL = getApiBaseUrl();
const DEFAULT_TIMEOUT = 30000; // 30 seconds
const DEFAULT_RETRY_ATTEMPTS = 3;
const DEFAULT_RETRY_DELAY = 1000; // 1 second

// ==================== Types ====================

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

export interface ApiError {
  message: string;
  code?: string;
  status?: number;
  details?: any;
}

export interface RequestOptions {
  timeout?: number;
  retries?: number;
  retryDelay?: number;
  signal?: AbortSignal;
  cache?: boolean;
  cacheTTL?: number; // Time to live in milliseconds
}

// Gas API Types
export interface GasRecommendation {
  ok: boolean;
  supports1559: boolean;
  maxFeePerGasGwei: string | null;
  maxPriorityFeePerGasGwei: string | null;
  legacyGasPriceGwei: string | null;
  source: string;
}

export interface GasEstimateRequest {
  to?: string;
  data?: string;
  value?: string;
  from_address?: string;
  buffer_percent?: number;
}

export interface GasEstimateResponse {
  ok: boolean;
  estimatedGas: string;
}

export interface TxSendRequest {
  signed_tx?: string;
  tx_request?: {
    to: string;
    data?: string;
    value?: string;
    nonce?: number;
  };
  mode?: 'server';
}

export interface TxSendResponse {
  ok: boolean;
  txHash: string;
}

export interface TxMonitorRequest {
  tx_hash: string;
  confirmations?: number;
  timeout_ms?: number;
}

export interface TxMonitorResponse {
  ok: boolean;
  receipt: {
    blockNumber: number;
    blockHash: string;
    transactionHash: string;
    status: number;
    gasUsed: number;
    confirmations?: number;
  };
}

export interface PaymentVerifyRequest {
  tx_hash: string;
  token_address?: string;
  expected_recipient?: string;
  min_amount_wei?: string;
}

export interface PaymentVerifyResponse {
  ok: boolean;
  result: any;
}

// ==================== Error Handling ====================

class ApiClientError extends Error {
  constructor(
    message: string,
    public code?: string,
    public status?: number,
    public details?: any
  ) {
    super(message);
    this.name = 'ApiClientError';
  }
}

function parseErrorResponse(response: Response, error?: any): ApiError {
  let message = response.statusText || 'Request failed';
  let details: any = null;

  try {
    // Try to parse error response body
    if (response.headers.get('content-type')?.includes('application/json')) {
      return response.json().then((data) => ({
        message: data.detail || data.message || message,
        code: data.code,
        status: response.status,
        details: data,
      })) as any;
    }
  } catch {
    // If parsing fails, use default
  }

  // Handle specific status codes
  switch (response.status) {
    case 400:
      message = 'Invalid request parameters';
      break;
    case 401:
      message = 'Unauthorized - please check your credentials';
      break;
    case 403:
      message = 'Forbidden - insufficient permissions';
      break;
    case 404:
      message = 'Resource not found';
      break;
    case 429:
      message = 'Too many requests - please try again later';
      break;
    case 500:
      message = 'Internal server error - please try again later';
      break;
    case 503:
      message = 'Service unavailable - backend may be starting up';
      break;
  }

  return {
    message,
    status: response.status,
    details: error,
  };
}

// ==================== Caching ====================

interface CacheEntry<T> {
  data: T;
  timestamp: number;
  ttl: number;
}

const cache = new Map<string, CacheEntry<any>>();

function getCacheKey(url: string, options?: RequestInit): string {
  const method = options?.method || 'GET';
  const body = options?.body ? JSON.stringify(options.body) : '';
  return `${method}:${url}:${body}`;
}

function getCached<T>(key: string): T | null {
  const entry = cache.get(key);
  if (!entry) return null;

  const now = Date.now();
  if (now - entry.timestamp > entry.ttl) {
    cache.delete(key);
    return null;
  }

  return entry.data as T;
}

function setCached<T>(key: string, data: T, ttl: number): void {
  cache.set(key, {
    data,
    timestamp: Date.now(),
    ttl,
  });
}

// ==================== Request Utilities ====================

async function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function fetchWithTimeout(
  url: string,
  options: RequestInit,
  timeout: number,
  signal?: AbortSignal
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  // Combine abort signals if both are provided
  if (signal) {
    signal.addEventListener('abort', () => controller.abort());
  }

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    return response;
  } catch (error: any) {
    clearTimeout(timeoutId);
    if (error.name === 'AbortError') {
      throw new ApiClientError('Request timeout', 'TIMEOUT', 408);
    }
    throw error;
  }
}

async function fetchWithRetry<T>(
  url: string,
  options: RequestInit,
  requestOptions: RequestOptions = {}
): Promise<T> {
  const {
    timeout = DEFAULT_TIMEOUT,
    retries = DEFAULT_RETRY_ATTEMPTS,
    retryDelay = DEFAULT_RETRY_DELAY,
    signal,
    cache: useCache = false,
    cacheTTL = 60000, // Default 1 minute
  } = requestOptions;

  const cacheKey = useCache ? getCacheKey(url, options) : null;

  // Check cache first
  if (useCache && cacheKey) {
    const cached = getCached<T>(cacheKey);
    if (cached !== null) {
      return cached;
    }
  }

  let lastError: Error | null = null;

  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const response = await fetchWithTimeout(url, options, timeout, signal);

      if (!response.ok) {
        const error = await parseErrorResponse(response);
        throw new ApiClientError(
          error.message,
          error.code,
          error.status,
          error.details
        );
      }

      const data = await response.json();

      // Cache successful responses
      if (useCache && cacheKey) {
        setCached(cacheKey, data, cacheTTL);
      }

      return data as T;
    } catch (error: any) {
      lastError = error;

      // Don't retry on certain errors
      if (
        error instanceof ApiClientError &&
        (error.status === 400 || error.status === 401 || error.status === 403 || error.status === 404)
      ) {
        throw error;
      }

      // Don't retry on abort
      if (error.name === 'AbortError' || signal?.aborted) {
        throw new ApiClientError('Request cancelled', 'CANCELLED', 0);
      }

      // If not the last attempt, wait and retry
      if (attempt < retries) {
        const delay = retryDelay * Math.pow(2, attempt); // Exponential backoff
        await sleep(delay);
        continue;
      }
    }
  }

  // If all retries failed, throw the last error
  if (lastError instanceof ApiClientError) {
    throw lastError;
  }
  throw new ApiClientError(
    lastError?.message || 'Request failed after retries',
    'NETWORK_ERROR'
  );
}

// ==================== API Functions ====================

/**
 * Fetch pools for a token pair
 */
export async function fetchPools(
  tokenIn: string,
  tokenOut: string,
  options?: RequestOptions
): Promise<PoolInfo[]> {
  try {
    const data = await fetchWithRetry<{ pools: PoolInfo[] }>(
      `${API_BASE_URL}/api/pools/${tokenIn}/${tokenOut}`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      },
      {
        ...options,
        cache: options?.cache ?? true, // Cache pools by default
        cacheTTL: options?.cacheTTL ?? 30000, // 30 seconds
      }
    );
    return data.pools || [];
  } catch (error: any) {
    console.error('Error fetching pools:', error);
    // Return empty array on error - frontend can use mock data as fallback
    return [];
  }
}

/**
 * Optimize routes using AI agent
 */
export async function optimizeRoutes(
  request: OptimizeRequest,
  options?: RequestOptions
): Promise<OptimizeResponse> {
  return fetchWithRetry<OptimizeResponse>(
    `${API_BASE_URL}/api/optimize`,
    {
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
    },
    {
      ...options,
      timeout: options?.timeout ?? 60000, // 60 seconds for optimization
      cache: false, // Don't cache optimization results
    }
  );
}

/**
 * Simulate execution of routes
 */
export async function simulateExecution(
  routes: SplitRoute[],
  options?: RequestOptions
): Promise<SimulationResult> {
  return fetchWithRetry<SimulationResult>(
    `${API_BASE_URL}/api/simulate`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(routes),
    },
    {
      ...options,
      timeout: options?.timeout ?? 45000, // 45 seconds for simulation
      cache: false,
    }
  );
}

/**
 * Get liquidity data for a trading pair
 */
export async function getLiquidityData(
  pair: string,
  options?: RequestOptions
): Promise<any> {
  try {
    return await fetchWithRetry(
      `${API_BASE_URL}/api/liquidity/${pair}`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      },
      {
        ...options,
        cache: options?.cache ?? true,
        cacheTTL: options?.cacheTTL ?? 10000, // 10 seconds
      }
    );
  } catch (error: any) {
    console.error('Error fetching liquidity data:', error);
    return null;
  }
}

/**
 * Execute optimized swap
 */
export async function executeSwap(
  request: OptimizeRequest,
  options?: RequestOptions
): Promise<any> {
  return fetchWithRetry(
    `${API_BASE_URL}/api/execute`,
    {
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
    },
    {
      ...options,
      timeout: options?.timeout ?? 120000, // 2 minutes for execution
      retries: options?.retries ?? 1, // Don't retry execution by default
      cache: false,
    }
  );
}

/**
 * Health check
 */
export async function checkHealth(options?: RequestOptions): Promise<boolean> {
  try {
    const response = await fetchWithTimeout(
      `${API_BASE_URL}/health`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      },
      options?.timeout ?? 5000, // 5 seconds for health check
      options?.signal
    );
    return response.ok;
  } catch (error) {
    return false;
  }
}

/**
 * Get dashboard metrics
 */
export async function getDashboardMetrics(
  options?: RequestOptions
): Promise<any> {
  try {
    return await fetchWithRetry(
      `${API_BASE_URL}/api/metrics/dashboard`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      },
      {
        ...options,
        cache: options?.cache ?? true,
        cacheTTL: options?.cacheTTL ?? 30000, // 30 seconds
      }
    );
  } catch (error: any) {
    console.error('Error fetching dashboard metrics:', error);
    return null;
  }
}

/**
 * Get agent status
 */
export async function getAgentStatus(options?: RequestOptions): Promise<any> {
  return await fetchWithRetry(
    `${API_BASE_URL}/api/agent/status`,
    {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    },
    {
      ...options,
      retries: options?.retries ?? 0, // No retries for faster fallback
      timeout: options?.timeout ?? 3000, // 3 second timeout
      cache: options?.cache ?? true,
      cacheTTL: options?.cacheTTL ?? 10000,
    }
  );
}

/**
 * Get recent executions
 */
export async function getRecentExecutions(
  limit: number = 10,
  options?: RequestOptions
): Promise<any> {
  try {
    const data = await fetchWithRetry<{ executions: any[] }>(
      `${API_BASE_URL}/api/executions/recent?limit=${limit}`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      },
      {
        ...options,
        cache: options?.cache ?? true,
        cacheTTL: options?.cacheTTL ?? 15000, // 15 seconds
      }
    );
    return data;
  } catch (error: any) {
    console.error('Error fetching recent executions:', error);
    return null;
  }
}

/**
 * Clear API cache
 */
export function clearCache(): void {
  cache.clear();
}

/**
 * Clear cache for a specific key pattern
 */
export function clearCachePattern(pattern: string): void {
  for (const key of cache.keys()) {
    if (key.includes(pattern)) {
      cache.delete(key);
    }
  }
}

// ==================== Gas API Functions ====================

/**
 * Get gas price recommendation
 */
export async function getGasRecommendation(
  options?: RequestOptions
): Promise<GasRecommendation> {
  return fetchWithRetry<GasRecommendation>(
    `${API_BASE_URL}/api/gas/recommendation`,
    {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    },
    {
      ...options,
      cache: options?.cache ?? true,
      cacheTTL: options?.cacheTTL ?? 10000, // 10 seconds
    }
  );
}

/**
 * Estimate gas limit for a transaction
 */
export async function estimateGas(
  request: GasEstimateRequest,
  options?: RequestOptions
): Promise<GasEstimateResponse> {
  return fetchWithRetry<GasEstimateResponse>(
    `${API_BASE_URL}/api/gas/estimate`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        to: request.to,
        data: request.data,
        value: request.value,
        from_address: request.from_address,
        buffer_percent: request.buffer_percent ?? 20,
      }),
    },
    {
      ...options,
      cache: false,
    }
  );
}

/**
 * Send transaction (signed or server-signed)
 */
export async function sendTransaction(
  request: TxSendRequest,
  options?: RequestOptions
): Promise<TxSendResponse> {
  return fetchWithRetry<TxSendResponse>(
    `${API_BASE_URL}/api/tx/send`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    },
    {
      ...options,
      timeout: options?.timeout ?? 60000,
      retries: options?.retries ?? 1, // Don't retry by default
      cache: false,
    }
  );
}

/**
 * Monitor transaction until confirmation
 */
export async function monitorTransaction(
  request: TxMonitorRequest,
  options?: RequestOptions
): Promise<TxMonitorResponse> {
  return fetchWithRetry<TxMonitorResponse>(
    `${API_BASE_URL}/api/tx/monitor`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        tx_hash: request.tx_hash,
        confirmations: request.confirmations ?? 1,
        timeout_ms: request.timeout_ms ?? 120000,
      }),
    },
    {
      ...options,
      timeout: options?.timeout ?? 180000, // 3 minutes for monitoring
      cache: false,
    }
  );
}

/**
 * Verify payment transaction
 */
export async function verifyPayment(
  request: PaymentVerifyRequest,
  options?: RequestOptions
): Promise<PaymentVerifyResponse> {
  return fetchWithRetry<PaymentVerifyResponse>(
    `${API_BASE_URL}/api/payments/verify`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    },
    {
      ...options,
      cache: false,
    }
  );
}

// ==================== DAO API ====================

export interface DAOInfo {
  dao_address: string;
  token_address: string;
  treasury_address: string;
  quorum_percentage: number;
  proposal_threshold: string;
  voting_period_seconds: number;
}

export interface Proposal {
  id: number;
  proposer: string;
  start_time: number;
  end_time: number;
  for_votes: string;
  against_votes: string;
  abstain_votes: string;
  status: number;
  proposal_type: number;
  target: string;
  value: string;
  token: string;
  recipient: string;
  call_data: string;
  description: string;
}

export interface VotingPower {
  balance: string;
  can_propose: boolean;
  proposal_threshold: string;
  total_supply: string;
}

export async function getDAOInfo(options?: RequestOptions): Promise<DAOInfo> {
  return fetchWithRetry<DAOInfo>(
    `${API_BASE_URL}/api/dao/info`,
    {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    },
    options
  );
}

export async function getProposal(
  proposalId: number,
  options?: RequestOptions
): Promise<Proposal> {
  return fetchWithRetry<Proposal>(
    `${API_BASE_URL}/api/dao/proposal/${proposalId}`,
    {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    },
    options
  );
}

export async function getVotingPower(
  userAddress: string,
  options?: RequestOptions
): Promise<VotingPower> {
  return fetchWithRetry<VotingPower>(
    `${API_BASE_URL}/api/dao/voting-power/${userAddress}`,
    {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    },
    options
  );
}

export interface CreateProposalRequest {
  proposal_type: 'eth_transfer' | 'erc20_transfer' | 'arbitrary_call';
  recipient?: string;
  token?: string;
  amount: string;
  description: string;
  private_key: string;
  target?: string;
  call_data?: string;
  value?: string;
}

export interface VoteRequest {
  proposal_id: number;
  support: 0 | 1 | 2; // 0 = Against, 1 = For, 2 = Abstain
  private_key: string;
}

export interface ExecuteProposalRequest {
  proposal_id: number;
  private_key: string;
}

export async function createProposal(
  request: CreateProposalRequest,
  options?: RequestOptions
): Promise<{ tx_hash: string; proposal_id: number | null; status: string }> {
  return fetchWithRetry(
    `${API_BASE_URL}/api/dao/proposal/create`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    },
    {
      ...options,
      cache: false,
    }
  );
}

export async function voteOnProposal(
  request: VoteRequest,
  options?: RequestOptions
): Promise<{ tx_hash: string; status: string }> {
  return fetchWithRetry(
    `${API_BASE_URL}/api/dao/vote`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    },
    {
      ...options,
      cache: false,
    }
  );
}

export async function finalizeProposal(
  request: ExecuteProposalRequest,
  options?: RequestOptions
): Promise<{ tx_hash: string; status: string }> {
  return fetchWithRetry(
    `${API_BASE_URL}/api/dao/proposal/finalize`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    },
    {
      ...options,
      cache: false,
    }
  );
}

export async function executeProposal(
  request: ExecuteProposalRequest,
  options?: RequestOptions
): Promise<{ tx_hash: string; status: string }> {
  return fetchWithRetry(
    `${API_BASE_URL}/api/dao/proposal/execute`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    },
    {
      ...options,
      cache: false,
    }
  );
}

// Export API object for convenience
export const api = {
  optimize: optimizeRoutes,
  execute: executeSwap,
  simulate: simulateExecution,
  getPools: fetchPools,
  getLiquidity: getLiquidityData,
  health: checkHealth,
  getDashboardMetrics,
  getAgentStatus,
  getRecentExecutions,
  // Gas API
  getGasRecommendation: getGasRecommendation,
  estimateGas: estimateGas,
  sendTransaction: sendTransaction,
  monitorTransaction: monitorTransaction,
  verifyPayment: verifyPayment,
  // DAO API
  getDAOInfo,
  getProposal,
  getVotingPower,
  createProposal,
  voteOnProposal,
  finalizeProposal,
  executeProposal,
  clearCache,
  clearCachePattern,
};

// Export error class for type checking
export { ApiClientError };
