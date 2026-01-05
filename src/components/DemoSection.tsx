import { useState, useMemo } from "react";
import { motion } from "framer-motion";
import { Calculator, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";

const dexOptions = [
  { id: "vvs", name: "VVS Finance", abbr: "VVS", color: "bg-primary" },
  { id: "cronaswap", name: "CronaSwap", abbr: "CRS", color: "bg-secondary" },
  { id: "mmf", name: "MM Finance", abbr: "MMF", color: "bg-accent" },
];

export const DemoSection = () => {
  const [tradeAmount, setTradeAmount] = useState([10000]);
  const [activeDexs, setActiveDexs] = useState<string[]>(["vvs", "cronaswap", "mmf"]);
  const [isSimulated, setIsSimulated] = useState(false);

  const toggleDex = (id: string) => {
    setActiveDexs((prev) =>
      prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id]
    );
  };

  const results = useMemo(() => {
    const amount = tradeAmount[0];
    const basePrice = 0.08;
    const dexCount = activeDexs.length || 1;

    const calcSingleSlippage = (amt: number) => {
      if (amt <= 1000) return 0.1;
      if (amt <= 10000) return 0.3;
      if (amt <= 50000) return 0.8;
      if (amt <= 100000) return 1.5;
      if (amt <= 500000) return 3.0;
      return 5.0;
    };

    const singleSlippage = calcSingleSlippage(amount);
    const cleoSlippage = singleSlippage * (0.3 + 0.1 * dexCount);

    const singleOutput = amount * basePrice * (1 - singleSlippage / 100);
    const cleoOutput = amount * basePrice * (1 - cleoSlippage / 100);
    const savings = cleoOutput - singleOutput;

    const singleGas = 0.02 + (amount / 100000) * 0.01;
    const cleoGas = 0.05 + dexCount * 0.01;

    return {
      singleOutput,
      cleoOutput,
      singleSlippage,
      cleoSlippage,
      savings,
      singleGas,
      cleoGas,
      dexCount,
    };
  }, [tradeAmount, activeDexs]);

  const handleSimulate = () => {
    setIsSimulated(true);
  };

  return (
    <section id="demo" className="py-24 relative">
      <div className="absolute inset-0 bg-card/50 rounded-3xl mx-4" />
      <div className="absolute top-0 right-1/4 w-96 h-96 bg-primary/5 rounded-full blur-3xl pointer-events-none" />

      <div className="container mx-auto px-4 relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="font-display text-3xl md:text-4xl font-bold mb-4">
            Interactive Demo
          </h2>
          <p className="text-muted-foreground max-w-xl mx-auto">
            Simulate how C.L.E.O. optimizes your trades across multiple Cronos DEXs with AI-driven routing
          </p>
        </motion.div>

        <div className="grid lg:grid-cols-2 gap-8">
          {/* Controls */}
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            className="glass rounded-2xl p-8"
          >
            <h3 className="font-display text-xl font-semibold mb-8">Trade Parameters</h3>

            <div className="mb-8">
              <div className="flex justify-between items-center mb-4">
                <label className="font-medium">Trade Size (CRO)</label>
                <span className="bg-gradient-primary text-primary-foreground px-3 py-1 rounded-full text-sm font-semibold">
                  {tradeAmount[0].toLocaleString()} CRO
                </span>
              </div>
              <Slider
                value={tradeAmount}
                onValueChange={setTradeAmount}
                min={100}
                max={500000}
                step={100}
                className="w-full"
              />
              <div className="flex justify-between text-sm text-muted-foreground mt-2">
                <span>Small</span>
                <span>Large</span>
              </div>
            </div>

            <div className="mb-8">
              <label className="font-medium block mb-4">Select DEXs for Routing</label>
              <div className="grid grid-cols-3 gap-3">
                {dexOptions.map((dex) => (
                  <button
                    key={dex.id}
                    onClick={() => toggleDex(dex.id)}
                    className={`p-4 rounded-xl text-center transition-all ${
                      activeDexs.includes(dex.id)
                        ? "border-2 border-secondary bg-secondary/10"
                        : "border border-border/50 bg-muted/30 hover:bg-muted/50"
                    }`}
                  >
                    <div className={`w-10 h-10 ${dex.color} rounded-lg mx-auto mb-2 flex items-center justify-center font-bold text-xs`}>
                      {dex.abbr}
                    </div>
                    <span className="text-sm">{dex.name}</span>
                  </button>
                ))}
              </div>
            </div>

            <div className="mb-8">
              <label className="font-medium block mb-4">Target Token</label>
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 rounded-full bg-primary" />
                  <span>CRO</span>
                </div>
                <ArrowRight className="w-4 h-4 text-muted-foreground" />
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 rounded-full bg-blue-500" />
                  <span>USDC</span>
                </div>
              </div>
            </div>

            <Button onClick={handleSimulate} className="w-full bg-gradient-primary hover:shadow-glow">
              <Calculator className="w-4 h-4 mr-2" />
              Simulate Optimized Route
            </Button>
          </motion.div>

          {/* Results */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            className="glass rounded-2xl p-8"
          >
            <div className="flex justify-between items-center mb-8">
              <h3 className="font-display text-xl font-semibold">Optimization Results</h3>
              <span className={`px-4 py-1 rounded-full text-sm font-semibold ${
                results.savings > 0 ? "bg-gradient-secondary text-secondary-foreground" : "bg-destructive/20 text-destructive"
              }`}>
                Saving: ${results.savings.toFixed(2)}
              </span>
            </div>

            {/* Single DEX Result */}
            <div className="bg-muted/30 rounded-xl p-5 mb-4">
              <div className="flex justify-between mb-3">
                <span>Traditional Single-DEX Swap</span>
                <span className="font-semibold">{results.singleOutput.toLocaleString(undefined, { maximumFractionDigits: 2 })} USDC</span>
              </div>
              <div className="h-2 bg-muted rounded-full overflow-hidden mb-3">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: isSimulated ? "100%" : "0%" }}
                  transition={{ duration: 1 }}
                  className="h-full bg-foreground/30 rounded-full"
                />
              </div>
              <div className="text-sm text-muted-foreground">
                Slippage: {results.singleSlippage.toFixed(2)}% • Gas: {results.singleGas.toFixed(3)} CRO
              </div>
            </div>

            {/* C.L.E.O. Result */}
            <div className="bg-muted/30 rounded-xl p-5 mb-6">
              <div className="flex justify-between mb-3">
                <span className="text-secondary">C.L.E.O. Optimized Multi-DEX Route</span>
                <span className="font-semibold text-secondary">{results.cleoOutput.toLocaleString(undefined, { maximumFractionDigits: 2 })} USDC</span>
              </div>
              <div className="h-2 bg-muted rounded-full overflow-hidden flex mb-3">
                {dexOptions.filter(d => activeDexs.includes(d.id)).map((dex, index) => (
                  <motion.div
                    key={dex.id}
                    initial={{ width: 0 }}
                    animate={{ width: isSimulated ? `${100 / (activeDexs.length || 1)}%` : "0%" }}
                    transition={{ duration: 0.8, delay: index * 0.2 }}
                    className={`h-full ${dex.color}`}
                  />
                ))}
              </div>
              <div className="text-sm text-muted-foreground">
                Slippage: <span className="text-secondary">{results.cleoSlippage.toFixed(2)}%</span> • Gas: <span className="text-secondary">{results.cleoGas.toFixed(3)} CRO</span>
              </div>
            </div>

            {/* Chart Placeholder */}
            <div className="bg-muted/20 rounded-xl p-6">
              <h4 className="text-sm font-medium mb-4">Slippage Comparison</h4>
              <div className="flex items-end gap-8 h-32">
                <div className="flex-1 flex flex-col items-center">
                  <motion.div
                    initial={{ height: 0 }}
                    animate={{ height: isSimulated ? `${Math.min(results.singleSlippage * 30, 100)}%` : "0%" }}
                    transition={{ duration: 1 }}
                    className="w-16 bg-foreground/30 rounded-t-lg"
                  />
                  <span className="text-xs mt-2 text-muted-foreground">Single DEX</span>
                  <span className="text-xs font-semibold">{results.singleSlippage.toFixed(2)}%</span>
                </div>
                <div className="flex-1 flex flex-col items-center">
                  <motion.div
                    initial={{ height: 0 }}
                    animate={{ height: isSimulated ? `${Math.min(results.cleoSlippage * 30, 100)}%` : "0%" }}
                    transition={{ duration: 1, delay: 0.2 }}
                    className="w-16 bg-gradient-secondary rounded-t-lg"
                  />
                  <span className="text-xs mt-2 text-muted-foreground">C.L.E.O.</span>
                  <span className="text-xs font-semibold text-secondary">{results.cleoSlippage.toFixed(2)}%</span>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
};
