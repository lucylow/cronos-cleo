/*
  mock-data.ts

  Comprehensive frontend mock data + mock API handlers for CLEO (Cronos C.L.E.O.)
  Purpose: provide realistic, extensive, edge-case-aware mock fixtures and server
  handlers to power the frontend demo, unit tests, and end-to-end workflows.

  How to use:
  - Import named exports (getMockTokens, getMockPools, mockMCPHandler, mockAgentDecision, etc.)
  - Start a small express dev mock server or use Next.js API routes that import this module
  - The dataset contains deterministic seeded RNG so tests are reproducible

  This file intentionally contains a large variety of data shapes and helpers:
  - Token & pair metadata
  - DEX liquidity pools snapshots across time
  - Historical tick/pricing series
  - Mempool event generator (front-running, sandwich attempt, miner inclusion delays)
  - Large trade scenario generator (institutional-sized trades)
  - AI decision stub with deterministic pseudo-random routing suggestions
  - Mock transaction receipts and failure modes
  - Edge cases: drained pools, fee-on-transfer tokens, stuck approvals
  - Helpers to seed localStorage or in-memory stores for frontend emulators

  Notes:
  - This is mock data only. Replace addresses and values with real sources for production.
*/

// --------------------------- Imports & Utilities ---------------------------

import crypto from 'crypto';

// Seeded RNG for reproducible results
function seedRandom(seed: string) {
  let h = 2166136261 >>> 0;
  for (let i = 0; i < seed.length; i++) h = Math.imul(h ^ seed.charCodeAt(i), 16777619) >>> 0;
  return function () {
    h += 0x6D2B79F5;
    let t = Math.imul(h ^ (h >>> 15), 1 | h);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const rng = seedRandom('cleo-mock-seed-v1');
function rand(min = 0, max = 1) { return min + (max - min) * rng(); }
function sample<T>(arr: T[]) { return arr[Math.floor(rng() * arr.length)]; }
function uid(prefix = 'id') { return `${prefix}_${crypto.randomBytes(6).toString('hex')}`; }

function nowSeconds() { return Math.floor(Date.now() / 1000); }

// --------------------------- Token Metadata ---------------------------

export type TokenMeta = {
  symbol: string;
  name: string;
  address: string;
  decimals: number;
  chain: string;
  isNative?: boolean;
  feeOnTransfer?: boolean; // some tokens burn on transfer
};

export const MOCK_TOKENS: TokenMeta[] = [
  { symbol: 'CRO', name: 'Cronos', address: '0x000000000000000000000000000000000000CRO0', decimals: 18, chain: 'cronos', isNative: true },
  { symbol: 'USDC.e', name: 'USDC (e)', address: '0x0000000000000000000000000000000000USDCe', decimals: 6, chain: 'cronos' },
  { symbol: 'USDT', name: 'Tether USD', address: '0x000000000000000000000000000000000000USDT', decimals: 6, chain: 'cronos' },
  { symbol: 'WETH', name: 'Wrapped ETH', address: '0x00000000000000000000000000000000WETH00', decimals: 18, chain: 'cronos' },
  { symbol: 'DAI', name: 'Dai Stablecoin', address: '0x00000000000000000000000000000DAI0000', decimals: 18, chain: 'cronos' },
  { symbol: 'FEE', name: 'Fee-On-Transfer Token', address: '0xFEETOKEN0000000000000000000000000000', decimals: 18, chain: 'cronos', feeOnTransfer: true },
  { symbol: 'WBTC', name: 'Wrapped BTC', address: '0x00000000000000000000000000000000WBTC00', decimals: 8, chain: 'cronos' },
  { symbol: 'MATIC', name: 'Polygon', address: '0x000000000000000000000000000000MATIC0', decimals: 18, chain: 'cronos' },
  { symbol: 'LINK', name: 'Chainlink', address: '0x0000000000000000000000000000000LINK0', decimals: 18, chain: 'cronos' },
  { symbol: 'UNI', name: 'Uniswap', address: '0x00000000000000000000000000000000UNI00', decimals: 18, chain: 'cronos' },
  { symbol: 'AAVE', name: 'Aave Token', address: '0x0000000000000000000000000000000AAVE0', decimals: 18, chain: 'cronos' },
  { symbol: 'ATOM', name: 'Cosmos', address: '0x000000000000000000000000000000ATOM0', decimals: 18, chain: 'cronos' },
  { symbol: 'VVS', name: 'VVS Finance', address: '0x0000000000000000000000000000000VVS00', decimals: 18, chain: 'cronos' },
  { symbol: 'MMF', name: 'MM Finance', address: '0x0000000000000000000000000000000MMF00', decimals: 18, chain: 'cronos' }
];

export function getToken(symbolOrAddr: string) {
  return MOCK_TOKENS.find(t => t.symbol === symbolOrAddr || t.address === symbolOrAddr) || null;
}

// --------------------------- DEX Pools & Liquidity Snapshots ---------------------------

export type DexPool = {
  id: string;
  dex: string;
  pair: string; // e.g. CRO-USDC.e
  tokenA: string; // address
  tokenB: string; // address
  reserveA: number; // human units
  reserveB: number; // human units
  feeBps: number; // e.g. 25 means 0.25%
  lastUpdated: number; // unix seconds
  tvl?: number; // USD equivalent (approx)
  historical?: { ts: number; reserveA: number; reserveB: number }[];
};

const initialPools: DexPool[] = [
  { id: 'pool_vvs_cro_usdc', dex: 'VVS Finance', pair: 'CRO-USDC.e', tokenA: getToken('CRO')!.address, tokenB: getToken('USDC.e')!.address, reserveA: 1_200_000, reserveB: 540_000, feeBps: 25, lastUpdated: nowSeconds(), tvl: 1_200_000 * 0.15 + 540_000 },
  { id: 'pool_crona_cro_usdc', dex: 'CronaSwap', pair: 'CRO-USDC.e', tokenA: getToken('CRO')!.address, tokenB: getToken('USDC.e')!.address, reserveA: 680_000, reserveB: 300_000, feeBps: 30, lastUpdated: nowSeconds(), tvl: 680_000 * 0.15 + 300_000 },
  { id: 'pool_mm_cro_usdc', dex: 'MM Finance', pair: 'CRO-USDC.e', tokenA: getToken('CRO')!.address, tokenB: getToken('USDC.e')!.address, reserveA: 350_000, reserveB: 165_000, feeBps: 30, lastUpdated: nowSeconds(), tvl: 350_000 * 0.15 + 165_000 },
  // Additional CRO pairs
  { id: 'pool_vvs_cro_usdt', dex: 'VVS Finance', pair: 'CRO-USDT', tokenA: getToken('CRO')!.address, tokenB: getToken('USDT')!.address, reserveA: 950_000, reserveB: 425_000, feeBps: 25, lastUpdated: nowSeconds(), tvl: 950_000 * 0.15 + 425_000 },
  { id: 'pool_mm_cro_usdt', dex: 'MM Finance', pair: 'CRO-USDT', tokenA: getToken('CRO')!.address, tokenB: getToken('USDT')!.address, reserveA: 420_000, reserveB: 190_000, feeBps: 30, lastUpdated: nowSeconds(), tvl: 420_000 * 0.15 + 190_000 },
  { id: 'pool_vvs_cro_weth', dex: 'VVS Finance', pair: 'CRO-WETH', tokenA: getToken('CRO')!.address, tokenB: getToken('WETH')!.address, reserveA: 1_500_000, reserveB: 225, feeBps: 25, lastUpdated: nowSeconds(), tvl: 1_500_000 * 0.15 + 225 * 2500 },
  { id: 'pool_crona_cro_weth', dex: 'CronaSwap', pair: 'CRO-WETH', tokenA: getToken('CRO')!.address, tokenB: getToken('WETH')!.address, reserveA: 880_000, reserveB: 132, feeBps: 30, lastUpdated: nowSeconds(), tvl: 880_000 * 0.15 + 132 * 2500 },
  // Stablecoin pairs
  { id: 'pool_vvs_usdc_usdt', dex: 'VVS Finance', pair: 'USDC.e-USDT', tokenA: getToken('USDC.e')!.address, tokenB: getToken('USDT')!.address, reserveA: 2_500_000, reserveB: 2_480_000, feeBps: 5, lastUpdated: nowSeconds(), tvl: 2_500_000 + 2_480_000 },
  { id: 'pool_mm_usdc_dai', dex: 'MM Finance', pair: 'USDC.e-DAI', tokenA: getToken('USDC.e')!.address, tokenB: getToken('DAI')!.address, reserveA: 1_800_000, reserveB: 1_790_000, feeBps: 5, lastUpdated: nowSeconds(), tvl: 1_800_000 + 1_790_000 },
  // Other token pairs
  { id: 'pool_vvs_usdc_weth', dex: 'VVS Finance', pair: 'USDC.e-WETH', tokenA: getToken('USDC.e')!.address, tokenB: getToken('WETH')!.address, reserveA: 3_200_000, reserveB: 1280, feeBps: 25, lastUpdated: nowSeconds(), tvl: 3_200_000 + 1280 * 2500 },
  { id: 'pool_crona_weth_wbtc', dex: 'CronaSwap', pair: 'WETH-WBTC', tokenA: getToken('WETH')!.address, tokenB: getToken('WBTC')!.address, reserveA: 850, reserveB: 21, feeBps: 30, lastUpdated: nowSeconds(), tvl: 850 * 2500 + 21 * 45000 },
  { id: 'pool_vvs_cro_link', dex: 'VVS Finance', pair: 'CRO-LINK', tokenA: getToken('CRO')!.address, tokenB: getToken('LINK')!.address, reserveA: 750_000, reserveB: 35_000, feeBps: 25, lastUpdated: nowSeconds(), tvl: 750_000 * 0.15 + 35_000 * 12 },
  { id: 'pool_mm_cro_atom', dex: 'MM Finance', pair: 'CRO-ATOM', tokenA: getToken('CRO')!.address, tokenB: getToken('ATOM')!.address, reserveA: 620_000, reserveB: 28_000, feeBps: 30, lastUpdated: nowSeconds(), tvl: 620_000 * 0.15 + 28_000 * 8 }
];

// Add more exotic pools for edge cases
initialPools.push({ id: 'pool_vvs_cro_fee', dex: 'VVS Finance', pair: 'CRO-FEE', tokenA: getToken('CRO')!.address, tokenB: getToken('FEE')!.address, reserveA: 80_000, reserveB: 40_000, feeBps: 30, lastUpdated: nowSeconds(), tvl: 80_000 * 0.15 + 40_000 });

// Make a mutable in-memory store for pools for mocking dynamic updates
const poolStore: Record<string, DexPool> = {};
for (const p of initialPools) poolStore[p.id] = { ...p, historical: generateInitialHistory(p) };

function generateInitialHistory(p: DexPool, points = 96) {
  // generate 96 points ~ 24h hourly-ish using seeded rng
  const arr: { ts: number; reserveA: number; reserveB: number }[] = [];
  const now = nowSeconds();
  for (let i = points - 1; i >= 0; i--) {
    const ts = now - i * 15 * 60; // 15-minute intervals
    const driftA = p.reserveA * (1 + (rand(-0.01, 0.01) * (i / points)));
    const driftB = p.reserveB * (1 + (rand(-0.01, 0.01) * (i / points)));
    arr.push({ ts, reserveA: Math.max(1, Math.floor(driftA * (0.8 + rand(0.2, 1)))), reserveB: Math.max(1, Math.floor(driftB * (0.8 + rand(0.2, 1)))) });
  }
  return arr;
}

export function getMockPoolsSnapshot() {
  return Object.values(poolStore).map(p => ({ ...p }));
}

export function updatePoolReservesRandomly() {
  // Simulate small random trades and liquidity movements
  for (const id of Object.keys(poolStore)) {
    const p = poolStore[id];
    const deltaA = Math.floor(p.reserveA * rand(-0.002, 0.002));
    const deltaB = Math.floor(p.reserveB * rand(-0.002, 0.002));
    p.reserveA = Math.max(0, p.reserveA + deltaA);
    p.reserveB = Math.max(0, p.reserveB + deltaB);
    p.lastUpdated = nowSeconds();
    // append to historical every minute roughly
    if (rng() < 0.15) p.historical!.push({ ts: p.lastUpdated, reserveA: p.reserveA, reserveB: p.reserveB });
  }
}

// --------------------------- Price Series & Market Data ---------------------------

export type PricePoint = { ts: number; priceCRO_USDC: number; vol24h: number; liquidityUSD: number };

export function generatePriceSeries(hours = 48) {
  const out: PricePoint[] = [];
  const now = nowSeconds();
  let base = 0.15; // assume CRO approx $0.15
  for (let i = hours * 4; i >= 0; i--) {
    const ts = now - i * 15 * 60; // 15 min
    // random walk with occasional shocks
    if (rng() < 0.01) base *= 1 + rand(-0.2, 0.2);
    base = base * (1 + rand(-0.002, 0.002));
    const vol24h = Math.abs(rand(0.8, 5.6)); // % vol
    const liquidityUSD = 1_000_000 + rand(-200_000, 200_000);
    out.push({ ts, priceCRO_USDC: Number((base).toFixed(6)), vol24h: Number(vol24h.toFixed(2)), liquidityUSD: Math.floor(liquidityUSD) });
  }
  return out;
}

export const MOCK_PRICE_SERIES = generatePriceSeries(72);

export function getLatestPrice() {
  return MOCK_PRICE_SERIES[MOCK_PRICE_SERIES.length - 1];
}

// --------------------------- Mempool & Sandwich Simulation ---------------------------

export type MempoolEvent = {
  id: string;
  type: 'tx' | 'sandwich' | 'priority' | 'cancel';
  from: string;
  to?: string;
  gasPriceGwei: number;
  amountIn?: number;
  pair?: string;
  timestamp: number;
  note?: string;
};

function randomWallet() { return '0x' + crypto.randomBytes(20).toString('hex'); }

export function generateMempoolEvents(count = 50) {
  const events: MempoolEvent[] = [];
  for (let i = 0; i < count; i++) {
    const type = rng() < 0.05 ? 'sandwich' : (rng() < 0.02 ? 'cancel' : 'tx');
    const ev: MempoolEvent = { id: uid('mp'), type, from: randomWallet(), gasPriceGwei: Number(rand(1, 300).toFixed(2)), timestamp: nowSeconds() - Math.floor(rand(0, 60 * 60)) };
    if (type === 'tx') { ev.amountIn = Math.floor(rand(1, 250000)); ev.pair = sample(['CRO-USDC.e', 'CRO-USDT', 'CRO-DAI']); }
    if (type === 'sandwich') { ev.amountIn = Math.floor(rand(1000, 200000)); ev.pair = 'CRO-USDC.e'; ev.note = 'detected sandwich candidate'; }
    events.push(ev);
  }
  return events;
}

// --------------------------- Agent Decisioning Mock ---------------------------

export type AgentRoute = { dex: string; amountIn: number; estimatedOut: number; path: string[]; minOut?: number };

export function mockAgentDecision(amountIn: number, pools: DexPool[], constraints?: any): { routes: AgentRoute[]; condition: string; meta: any } {
  // Decisioning stub: allocate to pools proportionally by reserveA with small stochastic improvement
  const totalRes = pools.reduce((s, p) => s + p.reserveA, 0) + 1;
  const routes: AgentRoute[] = [];
  let remaining = amountIn;
  const maxImpact = constraints?.maxPoolImpactPct || 6;
  // sort pools by preference: larger reserve first
  const sorted = [...pools].sort((a, b) => b.reserveA - a.reserveA);
  for (const p of sorted) {
    const cap = Math.floor((p.reserveA * maxImpact) / 100);
    if (cap <= 0) continue;
    const take = Math.min(remaining, Math.max(0, Math.floor(cap * (0.6 + rng() * 0.4))));
    if (take <= 0) continue;
    const estOut = estimateSwapOut(take, p);
    routes.push({ dex: p.dex, amountIn: take, estimatedOut: estOut, path: [getToken('CRO')!.symbol, getToken('USDC.e')!.symbol], minOut: Math.floor(estOut * 0.995) });
    remaining -= take;
    if (remaining <= 0) break;
  }
  // if still leftover send to largest pool
  if (remaining > 0) {
    const biggest = sorted[0];
    const estOut = estimateSwapOut(remaining, biggest);
    routes.push({ dex: biggest.dex, amountIn: remaining, estimatedOut: estOut, path: [getToken('CRO')!.symbol, getToken('USDC.e')!.symbol], minOut: Math.floor(estOut * 0.995) });
    remaining = 0;
  }
  const condition = `totalOut >= ${Math.floor(routes.reduce((s, r) => s + (r.estimatedOut || 0), 0))}`;
  return { routes, condition, meta: { generatedAt: nowSeconds(), seed: 'cleo-mock-v1' } };
}

function estimateSwapOut(amountIn: number, pool: DexPool) {
  // Constant-product estimated swap with fee
  const x = pool.reserveA;
  const y = pool.reserveB;
  const amountInWithFee = amountIn * (1 - pool.feeBps / 10000);
  const newX = x + amountInWithFee;
  const newY = (x * y) / newX;
  const amountOut = Math.max(0, y - newY);
  return Math.floor(amountOut);
}

// --------------------------- Large Trade Scenarios ---------------------------

export type LargeTradeScenario = {
  name: string;
  amountIn: number;
  description: string;
  expectedRisks: string[];
  suggestedRoutes: AgentRoute[];
};

export function generateLargeTradeScenarios() {
  const basePools = getMockPoolsSnapshot();
  const scenarios: LargeTradeScenario[] = [];
  const sizes = [50_000, 100_000, 250_000, 1_000_000];
  for (const size of sizes) {
    const decision = mockAgentDecision(size, basePools, { maxPoolImpactPct: 8 });
    scenarios.push({ name: `Institutional-${size}`, amountIn: size, description: `Swap ${size} CRO -> USDC.e`, expectedRisks: ['slippage', 'MEV', 'pool depletion'], suggestedRoutes: decision.routes });
  }
  return scenarios;
}

// --------------------------- Mock Transaction Receipts & Failures ---------------------------

export type MockTxReceipt = {
  txHash: string;
  status: 'success' | 'reverted' | 'timeout' | 'partial';
  gasUsed: number;
  blockNumber?: number;
  logs?: any[];
  errorReason?: string;
};

export function mockTxReceiptSuccess() {
  return { txHash: uid('tx'), status: 'success', gasUsed: Math.floor(rand(80_000, 450_000)), blockNumber: Math.floor(rand(8_000_000, 9_000_000)), logs: [] } as MockTxReceipt;
}

export function mockTxReceiptFailure(reason = 'INSUFFICIENT_OUTPUT_AMOUNT') {
  return { txHash: uid('tx'), status: 'reverted', gasUsed: Math.floor(rand(50_000, 200_000)), errorReason: reason } as MockTxReceipt;
}

export function mockPartialExecution() {
  return { txHash: uid('tx'), status: 'partial', gasUsed: Math.floor(rand(120_000, 550_000)), errorReason: 'PARTIAL_FILL: fallback used' } as MockTxReceipt;
}

// --------------------------- Mock API handlers (Express-like) ---------------------------

export function mockMCPHandler(req: any, res: any) {
  // Query params: pair
  const pair = req.query?.pair || 'CRO-USDC.e';
  // Return latest price + per-pool liquidity
  const latest = getLatestPrice();
  const pools = getMockPoolsSnapshot().filter(p => p.pair === pair);
  res.json({ pair, price: latest.priceCRO_USDC, vol1h: latest.vol24h, pools: pools.map(p => ({ id: p.id, dex: p.dex, reserveA: p.reserveA, reserveB: p.reserveB })) });
}

export async function mockAgentDecisionHandler(req: any, res: any) {
  // Expect body: { amountIn }
  const body = req.body || {};
  const amountIn = Number(body.amountIn || 100000);
  const pools = getMockPoolsSnapshot();
  const decision = mockAgentDecision(amountIn, pools, { maxPoolImpactPct: 5 });
  // Provide additional diagnostics and a confidence score
  const confidence = Number((0.6 + rng() * 0.35).toFixed(2));
  res.json({ decision, debug: { confidence, generatedAt: nowSeconds() } });
}

// --------------------------- Helper: seed localStorage / IndexedDB ---------------------------

export function seedLocalMockData() {
  if (typeof window === 'undefined' || !window.localStorage) return;
  localStorage.setItem('cleo.mock.tokens', JSON.stringify(MOCK_TOKENS));
  localStorage.setItem('cleo.mock.pools', JSON.stringify(getMockPoolsSnapshot()));
  localStorage.setItem('cleo.mock.priceSeries', JSON.stringify(MOCK_PRICE_SERIES));
}

// --------------------------- Edge Case Generators ---------------------------

export function generateDrainedPoolScenario(poolId: string) {
  const p = poolStore[poolId];
  if (!p) return null;
  // drain >95% of reserveA
  const drained = { ...p, reserveA: Math.max(0, Math.floor(p.reserveA * 0.04)), reserveB: Math.floor(p.reserveB * 0.1), lastUpdated: nowSeconds() };
  poolStore[poolId] = { ...drained, historical: p.historical };
  return drained;
}

export function generateFeeOnTransferScenario() {
  // Swap with FEE token which burns on transfer; return behavior indicates slippage+loss
  const p = Object.values(poolStore).find(x => x.pair.includes('FEE'));
  if (!p) return null;
  return { pool: p, note: 'Fee-on-transfer present — expect ~1% implicit burn in effective out' };
}

export function generateNetworkCongestionScenario() {
  // Increase mempool gasPrice and simulate delays
  const evs = generateMempoolEvents(200);
  evs.forEach(e => e.gasPriceGwei *= 2);
  return evs;
}

// --------------------------- Utilities for Frontend Visualizations ---------------------------

export function buildRoutePieData(routes: AgentRoute[]) {
  return routes.map(r => ({ name: r.dex, value: r.amountIn }));
}

export function summarizeSimulation(routes: AgentRoute[]) {
  const totalIn = routes.reduce((s, r) => s + r.amountIn, 0);
  const totalOut = routes.reduce((s, r) => s + (r.estimatedOut || 0), 0);
  const avgSlippagePct = routes.length ? (routes.reduce((s, r) => s + ((r.amountIn ? (r.estimatedOut / Math.max(r.amountIn, 1)) : 1) - 1), 0) * -100) / routes.length : 0;
  return { totalIn, totalOut, avgSlippagePct: Number(avgSlippagePct.toFixed(3)) };
}

// --------------------------- Test Fixtures Export ---------------------------

export const FIXTURES = {
  tokens: MOCK_TOKENS,
  pools: getMockPoolsSnapshot(),
  priceSeries: MOCK_PRICE_SERIES,
  mempool: generateMempoolEvents(60),
  largeTrades: generateLargeTradeScenarios(),
  sampleDecision: mockAgentDecision(100_000, getMockPoolsSnapshot(), { maxPoolImpactPct: 5 }),
};

// --------------------------- Example usage (commented) ---------------------------

/*
  // in server setup (express) you might do:
  import express from 'express';
  import { mockMCPHandler, mockAgentDecisionHandler } from './mock-data';
  const app = express(); app.use(express.json());
  app.get('/mcp', mockMCPHandler);
  app.post('/agent/decision', mockAgentDecisionHandler);
  app.listen(3333);

  // in frontend unit tests:
  import { FIXTURES } from './mock-data';
  expect(FIXTURES.tokens.length).toBeGreaterThan(0);

  // in UI seeds:
  seedLocalMockData();
*/

// --------------------------- End of mock-data.ts ---------------------------