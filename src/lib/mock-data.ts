/*
  mock-data.ts
  Comprehensive frontend mock data for CLEO (Cronos C.L.E.O.)
  Purpose: provide realistic mock fixtures for the frontend demo
*/

// --------------------------- Seeded RNG ---------------------------

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
function uid(prefix = 'id') { return `${prefix}_${Math.random().toString(36).slice(2, 10)}`; }
function nowSeconds() { return Math.floor(Date.now() / 1000); }

// --------------------------- Token Metadata ---------------------------

export type TokenMeta = {
  symbol: string;
  name: string;
  address: string;
  decimals: number;
  chain: string;
  isNative?: boolean;
  feeOnTransfer?: boolean;
};

export const MOCK_TOKENS: TokenMeta[] = [
  { symbol: 'CRO', name: 'Cronos', address: '0x000000000000000000000000000000000000CRO0', decimals: 18, chain: 'cronos', isNative: true },
  { symbol: 'USDC.e', name: 'USDC (e)', address: '0x0000000000000000000000000000000000USDCe', decimals: 6, chain: 'cronos' },
  { symbol: 'USDT', name: 'Tether USD', address: '0x000000000000000000000000000000000000USDT', decimals: 6, chain: 'cronos' },
  { symbol: 'WETH', name: 'Wrapped ETH', address: '0x00000000000000000000000000000000WETH00', decimals: 18, chain: 'cronos' },
  { symbol: 'DAI', name: 'Dai Stablecoin', address: '0x00000000000000000000000000000DAI0000', decimals: 18, chain: 'cronos' },
  { symbol: 'FEE', name: 'Fee-On-Transfer Token', address: '0xFEETOKEN0000000000000000000000000000', decimals: 18, chain: 'cronos', feeOnTransfer: true }
];

export function getToken(symbolOrAddr: string) {
  return MOCK_TOKENS.find(t => t.symbol === symbolOrAddr || t.address === symbolOrAddr) || null;
}

// --------------------------- DEX Pools ---------------------------

export type DexPool = {
  id: string;
  dex: string;
  pair: string;
  tokenA: string;
  tokenB: string;
  reserveA: number;
  reserveB: number;
  feeBps: number;
  lastUpdated: number;
  tvl?: number;
  historical?: { ts: number; reserveA: number; reserveB: number }[];
};

const initialPools: DexPool[] = [
  { id: 'pool_vvs_cro_usdc', dex: 'VVS Finance', pair: 'CRO-USDC.e', tokenA: getToken('CRO')!.address, tokenB: getToken('USDC.e')!.address, reserveA: 1_200_000, reserveB: 540_000, feeBps: 25, lastUpdated: nowSeconds(), tvl: 1_200_000 * 0.15 + 540_000 },
  { id: 'pool_crona_cro_usdc', dex: 'CronaSwap', pair: 'CRO-USDC.e', tokenA: getToken('CRO')!.address, tokenB: getToken('USDC.e')!.address, reserveA: 680_000, reserveB: 300_000, feeBps: 30, lastUpdated: nowSeconds(), tvl: 680_000 * 0.15 + 300_000 },
  { id: 'pool_mm_cro_usdc', dex: 'MM Finance', pair: 'CRO-USDC.e', tokenA: getToken('CRO')!.address, tokenB: getToken('USDC.e')!.address, reserveA: 350_000, reserveB: 165_000, feeBps: 30, lastUpdated: nowSeconds(), tvl: 350_000 * 0.15 + 165_000 },
  { id: 'pool_vvs_cro_fee', dex: 'VVS Finance', pair: 'CRO-FEE', tokenA: getToken('CRO')!.address, tokenB: getToken('FEE')!.address, reserveA: 80_000, reserveB: 40_000, feeBps: 30, lastUpdated: nowSeconds(), tvl: 80_000 * 0.15 + 40_000 }
];

function generateInitialHistory(p: DexPool, points = 96) {
  const arr: { ts: number; reserveA: number; reserveB: number }[] = [];
  const now = nowSeconds();
  for (let i = points - 1; i >= 0; i--) {
    const ts = now - i * 15 * 60;
    const driftA = p.reserveA * (1 + (rand(-0.01, 0.01) * (i / points)));
    const driftB = p.reserveB * (1 + (rand(-0.01, 0.01) * (i / points)));
    arr.push({ ts, reserveA: Math.max(1, Math.floor(driftA * (0.8 + rand(0.2, 1)))), reserveB: Math.max(1, Math.floor(driftB * (0.8 + rand(0.2, 1)))) });
  }
  return arr;
}

const poolStore: Record<string, DexPool> = {};
for (const p of initialPools) poolStore[p.id] = { ...p, historical: generateInitialHistory(p) };

export function getMockPoolsSnapshot() {
  return Object.values(poolStore).map(p => ({ ...p }));
}

export function updatePoolReservesRandomly() {
  for (const id of Object.keys(poolStore)) {
    const p = poolStore[id];
    const deltaA = Math.floor(p.reserveA * rand(-0.002, 0.002));
    const deltaB = Math.floor(p.reserveB * rand(-0.002, 0.002));
    p.reserveA = Math.max(0, p.reserveA + deltaA);
    p.reserveB = Math.max(0, p.reserveB + deltaB);
    p.lastUpdated = nowSeconds();
    if (rng() < 0.15) p.historical!.push({ ts: p.lastUpdated, reserveA: p.reserveA, reserveB: p.reserveB });
  }
}

// --------------------------- Price Series ---------------------------

export type PricePoint = { ts: number; priceCRO_USDC: number; vol24h: number; liquidityUSD: number };

export function generatePriceSeries(hours = 48) {
  const out: PricePoint[] = [];
  const now = nowSeconds();
  let base = 0.15;
  for (let i = hours * 4; i >= 0; i--) {
    const ts = now - i * 15 * 60;
    if (rng() < 0.01) base *= 1 + rand(-0.2, 0.2);
    base = base * (1 + rand(-0.002, 0.002));
    const vol24h = Math.abs(rand(0.8, 5.6));
    const liquidityUSD = 1_000_000 + rand(-200_000, 200_000);
    out.push({ ts, priceCRO_USDC: Number(base.toFixed(6)), vol24h: Number(vol24h.toFixed(2)), liquidityUSD: Math.floor(liquidityUSD) });
  }
  return out;
}

export const MOCK_PRICE_SERIES = generatePriceSeries(72);

export function getLatestPrice() {
  return MOCK_PRICE_SERIES[MOCK_PRICE_SERIES.length - 1];
}

// --------------------------- Agent Decisioning ---------------------------

export type AgentRoute = { dex: string; amountIn: number; estimatedOut: number; path: string[]; minOut?: number };

function estimateSwapOut(amountIn: number, pool: DexPool) {
  const x = pool.reserveA;
  const y = pool.reserveB;
  const amountInWithFee = amountIn * (1 - pool.feeBps / 10000);
  const newX = x + amountInWithFee;
  const newY = (x * y) / newX;
  return Math.max(0, Math.floor(y - newY));
}

export function mockAgentDecision(amountIn: number, pools: DexPool[], constraints?: { maxPoolImpactPct?: number }): { routes: AgentRoute[]; condition: string; meta: any } {
  const totalRes = pools.reduce((s, p) => s + p.reserveA, 0) + 1;
  const routes: AgentRoute[] = [];
  let remaining = amountIn;
  const maxImpact = constraints?.maxPoolImpactPct || 6;
  const sorted = [...pools].sort((a, b) => b.reserveA - a.reserveA);
  
  for (const p of sorted) {
    const cap = Math.floor((p.reserveA * maxImpact) / 100);
    if (cap <= 0) continue;
    const take = Math.min(remaining, Math.max(0, Math.floor(cap * (0.6 + rng() * 0.4))));
    if (take <= 0) continue;
    const estOut = estimateSwapOut(take, p);
    routes.push({ dex: p.dex, amountIn: take, estimatedOut: estOut, path: ['CRO', 'USDC.e'], minOut: Math.floor(estOut * 0.995) });
    remaining -= take;
    if (remaining <= 0) break;
  }
  
  if (remaining > 0) {
    const biggest = sorted[0];
    const estOut = estimateSwapOut(remaining, biggest);
    routes.push({ dex: biggest.dex, amountIn: remaining, estimatedOut: estOut, path: ['CRO', 'USDC.e'], minOut: Math.floor(estOut * 0.995) });
  }
  
  const condition = `totalOut >= ${Math.floor(routes.reduce((s, r) => s + (r.estimatedOut || 0), 0))}`;
  return { routes, condition, meta: { generatedAt: nowSeconds(), seed: 'cleo-mock-v1' } };
}

// --------------------------- Mock API Handlers ---------------------------

export function mockMCPHandler(pair = 'CRO-USDC.e') {
  const latest = getLatestPrice();
  const pools = getMockPoolsSnapshot().filter(p => p.pair === pair);
  return { pair, price: latest.priceCRO_USDC, vol1h: latest.vol24h, pools: pools.map(p => ({ id: p.id, dex: p.dex, reserveA: p.reserveA, reserveB: p.reserveB })) };
}

export function mockAgentDecisionHandler(amountIn: number) {
  const pools = getMockPoolsSnapshot();
  const decision = mockAgentDecision(amountIn, pools, { maxPoolImpactPct: 5 });
  const confidence = Number((0.6 + rng() * 0.35).toFixed(2));
  return { decision, debug: { confidence, generatedAt: nowSeconds() } };
}

// --------------------------- Utilities ---------------------------

export function buildRoutePieData(routes: AgentRoute[]) {
  return routes.map(r => ({ name: r.dex, value: r.amountIn }));
}

export function summarizeSimulation(routes: AgentRoute[]) {
  const totalIn = routes.reduce((s, r) => s + r.amountIn, 0);
  const totalOut = routes.reduce((s, r) => s + (r.estimatedOut || 0), 0);
  const avgSlippagePct = routes.length ? (routes.reduce((s, r) => s + ((r.amountIn ? (r.estimatedOut / Math.max(r.amountIn, 1)) : 1) - 1), 0) * -100) / routes.length : 0;
  return { totalIn, totalOut, avgSlippagePct: Number(avgSlippagePct.toFixed(3)) };
}

export function seedLocalMockData() {
  if (typeof window === 'undefined' || !window.localStorage) return;
  localStorage.setItem('cleo.mock.tokens', JSON.stringify(MOCK_TOKENS));
  localStorage.setItem('cleo.mock.pools', JSON.stringify(getMockPoolsSnapshot()));
  localStorage.setItem('cleo.mock.priceSeries', JSON.stringify(MOCK_PRICE_SERIES));
}

// --------------------------- Fixtures Export ---------------------------

export const FIXTURES = {
  tokens: MOCK_TOKENS,
  pools: getMockPoolsSnapshot(),
  priceSeries: MOCK_PRICE_SERIES,
  sampleDecision: mockAgentDecision(100_000, getMockPoolsSnapshot(), { maxPoolImpactPct: 5 }),
};
