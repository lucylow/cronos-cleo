import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { BookOpen, Zap, PieChart, Settings, Bot } from "lucide-react";
import { useWallet } from "@/wallet/WalletProvider";
import ConnectWalletButton from "@/wallet/ConnectWalletButton";

// -------------------- Types --------------------

type Token = {
  symbol: string;
  address: string;
  decimals: number;
};

type DexPool = {
  dex: string;
  pair: string;
  reserveIn: number;
  reserveOut: number;
  feeBps: number;
};

type SplitRoute = {
  id: string;
  dex: string;
  amountIn: number;
  estimatedOut: number;
  path: string[];
};

type SimulationResult = {
  totalIn: number;
  totalOut: number;
  slippagePct: number;
  gasEstimate: number;
  routeBreakdown: SplitRoute[];
};

// -------------------- Constants & Mocks --------------------

const MOCK_POOLS: DexPool[] = [
  { dex: "VVS Finance", pair: "CRO-USDC.e", reserveIn: 1_000_000, reserveOut: 500_000, feeBps: 25 },
  { dex: "CronaSwap", pair: "CRO-USDC.e", reserveIn: 600_000, reserveOut: 300_000, feeBps: 30 },
  { dex: "MM Finance", pair: "CRO-USDC.e", reserveIn: 350_000, reserveOut: 200_000, feeBps: 30 },
];

const fmt = (n: number, digits = 4) => (n >= 1 ? n.toFixed(digits) : n.toPrecision(digits));

// -------------------- Utility Functions --------------------

function estimateSwapOutCROtoUSDC(amountIn: number, pool: DexPool) {
  const x = pool.reserveIn;
  const y = pool.reserveOut;
  const amountInWithFee = amountIn * (1 - pool.feeBps / 10000);
  const newX = x + amountInWithFee;
  const newY = (x * y) / newX;
  return y - newY;
}

function uid(prefix = "r") {
  return `${prefix}_${Math.random().toString(36).slice(2, 9)}`;
}

function suggestSplits(amountIn: number, pools: DexPool[], maxImpactPct = 5) {
  const capacities = pools.map((p) => ({ pool: p, capacity: (p.reserveIn * maxImpactPct) / 100 }));
  let remaining = amountIn;
  const route: SplitRoute[] = [];
  for (const c of capacities.sort((a, b) => b.capacity - a.capacity)) {
    if (remaining <= 0) break;
    const take = Math.min(remaining, c.capacity);
    const out = estimateSwapOutCROtoUSDC(take, c.pool);
    route.push({ id: uid("r"), dex: c.pool.dex, amountIn: take, estimatedOut: out, path: ["CRO", "USDC.e"] });
    remaining -= take;
  }
  if (remaining > 0) {
    const biggest = pools.reduce((a, b) => (a.reserveIn > b.reserveIn ? a : b));
    const out = estimateSwapOutCROtoUSDC(remaining, biggest);
    route.push({ id: uid("r"), dex: biggest.dex, amountIn: remaining, estimatedOut: out, path: ["CRO", "USDC.e"] });
  }
  return route;
}

async function mockSimulateExecution(routes: SplitRoute[]): Promise<SimulationResult> {
  await new Promise((r) => setTimeout(r, 200));
  const totalIn = routes.reduce((s, r) => s + r.amountIn, 0);
  const totalOut = routes.reduce((s, r) => s + r.estimatedOut, 0);
  const slippagePct = ((routes[0].estimatedOut / (routes[0].amountIn || 1)) - 1) * -100;
  const gasEstimate = 120_000 + routes.length * 12_000;
  return { totalIn, totalOut, slippagePct: Math.abs(slippagePct), gasEstimate, routeBreakdown: routes };
}

// -------------------- Small UI Components --------------------

function Logo() {
  return (
    <div className="flex items-center gap-3">
      <div className="w-10 h-10 rounded-xl bg-gradient-primary flex items-center justify-center">
        <Bot className="w-6 h-6 text-white" />
      </div>
      <div>
        <h1 className="text-xl font-bold text-gradient-primary">C.L.E.O.</h1>
        <p className="text-xs text-muted-foreground">Cross-DEX Liquidity Execution Orchestrator</p>
      </div>
    </div>
  );
}

// -------------------- Main Functional Components --------------------

function RouteBuilder({ amountIn, onChange }: { amountIn: number; onChange: (routes: SplitRoute[]) => void }) {
  const [maxImpact, setMaxImpact] = useState(5);
  const [pools, setPools] = useState(MOCK_POOLS);

  useEffect(() => {
    const routes = suggestSplits(amountIn, pools, maxImpact);
    onChange(routes);
  }, [amountIn, maxImpact, pools, onChange]);

  return (
    <Card className="bg-card/50 border-border/50 backdrop-blur-sm">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <PieChart className="w-5 h-5 text-primary" />
          Multi-DEX Route Builder
          <span className="ml-auto text-sm font-normal text-muted-foreground">Max impact: {maxImpact}%</span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid md:grid-cols-2 gap-6">
          <div className="space-y-3">
            <h4 className="font-semibold text-sm text-foreground">Suggested Splits</h4>
            <div className="space-y-2">
              {suggestSplits(amountIn, pools, maxImpact).map((r) => (
                <motion.div
                  key={r.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="flex justify-between items-center p-3 rounded-lg bg-muted/50 border border-border/50"
                >
                  <div>
                    <p className="font-medium text-foreground">{r.dex}</p>
                    <p className="text-xs text-muted-foreground">Path: {r.path.join(" → ")}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-foreground">In: {fmt(r.amountIn, 2)}</p>
                    <p className="text-xs text-accent">Out: {fmt(r.estimatedOut, 2)}</p>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>

          <div className="space-y-4">
            <h4 className="font-semibold text-sm text-foreground">Routing Controls</h4>
            <div className="space-y-2">
              <label className="text-xs text-muted-foreground">Max Pool Impact (%)</label>
              <Input
                type="number"
                value={maxImpact}
                onChange={(e) => setMaxImpact(Number(e.target.value))}
                className="w-full bg-background/50"
              />
            </div>

            <div className="space-y-2">
              {pools.map((p) => (
                <div key={p.dex} className="flex justify-between items-center p-2 rounded bg-muted/30 text-sm">
                  <div>
                    <p className="font-medium text-foreground">{p.dex}</p>
                    <p className="text-xs text-muted-foreground">Reserve: {fmt(p.reserveIn)} CRO</p>
                  </div>
                  <p className="text-muted-foreground">Fee: {p.feeBps / 100}%</p>
                </div>
              ))}
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={() => setPools((s) => [...s].sort(() => Math.random() - 0.5))}
              className="w-full"
            >
              Re-scan Pools
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function SimulatorView({ routes, onSimulated }: { routes: SplitRoute[]; onSimulated?: (r: SimulationResult) => void }) {
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [running, setRunning] = useState(false);

  async function run() {
    setRunning(true);
    const res = await mockSimulateExecution(routes);
    setResult(res);
    onSimulated?.(res);
    setRunning(false);
  }

  useEffect(() => {
    run();
  }, [JSON.stringify(routes.map((r) => ({ d: r.dex, a: r.amountIn })))]);

  return (
    <Card className="bg-card/50 border-border/50 backdrop-blur-sm">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Zap className="w-5 h-5 text-accent" />
          Simulation
          <span className="ml-auto text-sm font-normal text-muted-foreground">Preview before x402 batching</span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid md:grid-cols-2 gap-6">
          <div className="space-y-4">
            <h4 className="font-semibold text-sm text-foreground">Summary</h4>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between p-2 rounded bg-muted/30">
                <span className="text-muted-foreground">Total In</span>
                <span className="font-medium text-foreground">{fmt(result?.totalIn || 0, 2)} CRO</span>
              </div>
              <div className="flex justify-between p-2 rounded bg-muted/30">
                <span className="text-muted-foreground">Total Out (est)</span>
                <span className="font-medium text-accent">{fmt(result?.totalOut || 0, 2)} USDC.e</span>
              </div>
              <div className="flex justify-between p-2 rounded bg-muted/30">
                <span className="text-muted-foreground">Gas Estimate</span>
                <span className="font-medium text-foreground">{result?.gasEstimate || "—"} units</span>
              </div>
            </div>
            <Button onClick={run} disabled={running} variant="outline" size="sm" className="w-full">
              {running ? "Simulating…" : "Re-run Simulation"}
            </Button>
          </div>

          <div className="space-y-3">
            <h4 className="font-semibold text-sm text-foreground">Route Breakdown</h4>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {routes.map((r) => (
                <div key={r.id} className="p-2 rounded bg-muted/30 text-sm">
                  <div className="flex justify-between">
                    <span className="font-medium text-foreground">{r.dex}</span>
                    <span className="text-muted-foreground">In: {fmt(r.amountIn, 2)} CRO</span>
                  </div>
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span>Out: {fmt(r.estimatedOut, 2)}</span>
                    <span>{r.path.join("→")}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function ChartPerformance({ history }: { history: { time: string; value: number }[] }) {
  return (
    <Card className="bg-card/50 border-border/50 backdrop-blur-sm">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Execution Performance (mock)</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={120}>
          <LineChart data={history}>
            <XAxis dataKey="time" hide />
            <YAxis hide domain={["auto", "auto"]} />
            <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))" }} />
            <Line type="monotone" dataKey="value" stroke="hsl(var(--accent))" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

function TxPreview({ simulation }: { simulation?: SimulationResult | null }) {
  return (
    <Card className="bg-card/50 border-border/50 backdrop-blur-sm">
      <CardHeader>
        <CardTitle className="text-sm">Transaction Preview (x402 batch)</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-xs text-muted-foreground">
          Dry-run preview of the x402 bundle to be submitted to Cronos.
        </p>
        <div className="space-y-1 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Total In</span>
            <span className="text-foreground">{fmt(simulation?.totalIn || 0, 2)} CRO</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Total Out</span>
            <span className="text-accent">{fmt(simulation?.totalOut || 0, 2)} USDC.e</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Gas</span>
            <span className="text-foreground">{simulation?.gasEstimate || "—"}</span>
          </div>
        </div>
        <Button className="w-full" size="sm">
          Submit x402 Batch (Demo)
        </Button>
      </CardContent>
    </Card>
  );
}

// -------------------- Page Layout --------------------

export default function CLEOFrontend() {
  const { account } = useWallet();
  const [amount, setAmount] = useState(100000);
  const [routes, setRoutes] = useState(suggestSplits(100000, MOCK_POOLS, 5));
  const [simulation, setSimulation] = useState<SimulationResult | null>(null);
  const [history, setHistory] = useState<{ time: string; value: number }[]>(() => {
    const now = Date.now();
    return Array.from({ length: 20 }).map((_, i) => ({
      time: new Date(now - (19 - i) * 60_000).toLocaleTimeString(),
      value: Math.random() * 0.5 + 0.2,
    }));
  });

  useEffect(() => {
    if (simulation) {
      setHistory((h) => [
        ...h.slice(-18),
        { time: new Date().toLocaleTimeString(), value: simulation.totalOut / Math.max(simulation.totalIn, 1) },
      ]);
    }
  }, [simulation?.totalOut]);

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-border/50 bg-background/80 backdrop-blur-lg">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Logo />
          <div className="flex items-center gap-4">
            <span className="text-xs text-muted-foreground hidden sm:block">Cronos x402 Hackathon • Agentic Finance</span>
            <ConnectWalletButton />
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Left Column - Main Controls */}
          <div className="lg:col-span-2 space-y-6">
            <Card className="bg-card/50 border-border/50 backdrop-blur-sm">
              <CardHeader>
                <CardTitle>Quick Swap Simulator — Multi-DEX Routing</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-4 items-end">
                  <div className="space-y-2">
                    <label className="text-sm text-muted-foreground">Amount (CRO)</label>
                    <Input
                      type="number"
                      value={amount}
                      onChange={(e) => setAmount(Number(e.target.value || 0))}
                      className="w-48 bg-background/50"
                    />
                  </div>
                  <Button onClick={() => setRoutes(suggestSplits(amount, MOCK_POOLS, 5))}>
                    Recompute Routes
                  </Button>
                </div>
              </CardContent>
            </Card>

            <RouteBuilder amountIn={amount} onChange={(r) => setRoutes(r)} />
            <SimulatorView routes={routes} onSimulated={(res) => setSimulation(res)} />

            <div className="grid md:grid-cols-2 gap-6">
              <ChartPerformance history={history} />
              <TxPreview simulation={simulation} />
            </div>
          </div>

          {/* Right Column - Settings */}
          <div className="space-y-6">
            <Card className="bg-card/50 border-border/50 backdrop-blur-sm">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Settings className="w-4 h-4" />
                  Tools & Settings
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm text-muted-foreground">Mode</label>
                  <Select defaultValue="demo">
                    <SelectTrigger className="bg-background/50">
                      <SelectValue placeholder="Demo" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="demo">Demo</SelectItem>
                      <SelectItem value="testnet">Testnet</SelectItem>
                      <SelectItem value="mainnet">Mainnet</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">MEV Protection</span>
                  <Switch defaultChecked />
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Auto Re-route</span>
                  <Switch defaultChecked />
                </div>

                <Button variant="outline" size="sm" className="w-full">
                  Open Advanced Audit Log
                </Button>
              </CardContent>
            </Card>

            <Card className="bg-card/50 border-border/50 backdrop-blur-sm">
              <CardHeader>
                <CardTitle className="text-sm">About this Demo</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  This frontend is a prototype for the Cronos C.L.E.O. project. It demonstrates a multi-DEX split route
                  builder, simulation, and a single x402 batch preview. The AI decisioning is mocked locally — for
                  production you'd hook the Crypto.com AI Agent SDK + MCP data feeds, and use x402 facilitator SDK for
                  atomic batch submission.
                </p>
              </CardContent>
            </Card>

            <Card className="bg-card/50 border-border/50 backdrop-blur-sm">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-sm">
                  <BookOpen className="w-4 h-4" />
                  Quick Links
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <a href="https://github.com/AAgentFun/x402-facilitator" target="_blank" rel="noopener noreferrer" className="block text-sm text-accent hover:underline">
                  x402 Facilitator SDK
                </a>
                <a href="https://github.com/crypto-com/agent-sdk" target="_blank" rel="noopener noreferrer" className="block text-sm text-accent hover:underline">
                  Crypto.com AI Agent SDK
                </a>
                <a href="https://cronos.org/faucet" target="_blank" rel="noopener noreferrer" className="block text-sm text-accent hover:underline">
                  Cronos Testnet Faucet
                </a>
              </CardContent>
            </Card>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-border/50 py-6 mt-12">
        <p className="text-center text-xs text-muted-foreground">
          Built for Cronos x402 Hackathon • Demo frontend • Not for production use
        </p>
      </footer>
    </div>
  );
}
