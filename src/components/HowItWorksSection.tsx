import { motion } from "framer-motion";

const steps = [
  {
    number: 1,
    title: "Trade Request",
    description: "User or AI agent submits swap request with parameters (token pair, amount, slippage tolerance).",
  },
  {
    number: 2,
    title: "Liquidity Analysis",
    description: "C.L.E.O. scans all integrated Cronos DEXs for real-time liquidity, prices, and pool depths.",
  },
  {
    number: 3,
    title: "AI Optimization",
    description: "Machine learning model calculates optimal split ratios to minimize slippage and gas costs.",
  },
  {
    number: 4,
    title: "x402 Execution",
    description: "Atomic multi-DEX execution via Cronos x402 facilitator - all or nothing settlement.",
  },
  {
    number: 5,
    title: "Result & Learning",
    description: "Trade results are recorded to improve future optimizations through reinforcement learning.",
  },
];

export const HowItWorksSection = () => {
  return (
    <section id="how-it-works" className="py-24 bg-card/50">
      <div className="container mx-auto px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="font-display text-3xl md:text-4xl font-bold mb-4">
            How C.L.E.O. Works
          </h2>
          <p className="text-muted-foreground max-w-xl mx-auto">
            The AI orchestration process from trade request to optimized execution
          </p>
        </motion.div>

        <div className="relative">
          {/* Connection Line (Desktop) */}
          <div className="hidden lg:block absolute top-12 left-[10%] right-[10%] h-0.5 bg-border" />

          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-8">
            {steps.map((step, index) => (
              <motion.div
                key={step.number}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.15 }}
                className="text-center relative"
              >
                <motion.div
                  whileHover={{ scale: 1.1 }}
                  className="w-20 h-20 rounded-full bg-gradient-primary flex items-center justify-center mx-auto mb-6 relative z-10 border-4 border-background animate-pulse-glow"
                >
                  <span className="text-2xl font-display font-bold text-primary-foreground">
                    {step.number}
                  </span>
                </motion.div>
                <h3 className="font-display text-lg font-semibold mb-3">{step.title}</h3>
                <p className="text-muted-foreground text-sm leading-relaxed">{step.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};
