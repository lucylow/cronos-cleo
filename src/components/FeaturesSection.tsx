import { motion } from "framer-motion";
import { Bot, Atom, Network, Fuel, Shield, LineChart } from "lucide-react";

const features = [
  {
    icon: Bot,
    title: "AI-Powered Routing",
    description: "Machine learning algorithms analyze real-time liquidity, volatility, and gas prices to determine optimal split ratios across DEXs.",
  },
  {
    icon: Atom,
    title: "x402 Atomic Execution",
    description: "Execute multi-DEX trades atomically via Cronos x402. All swaps succeed or all revert - eliminating partial execution risk.",
  },
  {
    icon: Network,
    title: "Multi-DEX Aggregation",
    description: "Intelligently splits orders across VVS Finance, CronaSwap, MM Finance, and other Cronos DEXs for maximum liquidity access.",
  },
  {
    icon: Fuel,
    title: "Gas Optimization",
    description: "Batch transactions and share approvals to minimize gas costs, leveraging Cronos's low-fee environment for complex operations.",
  },
  {
    icon: Shield,
    title: "MEV Protection",
    description: "Advanced routing strategies and timing algorithms protect against front-running and sandwich attacks common in DeFi.",
  },
  {
    icon: LineChart,
    title: "Real-time Analytics",
    description: "Comprehensive dashboards showing execution quality, slippage savings, and performance metrics for every trade.",
  },
];

export const FeaturesSection = () => {
  return (
    <section id="features" className="py-24">
      <div className="container mx-auto px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="font-display text-3xl md:text-4xl font-bold mb-4">
            Powerful Features
          </h2>
          <p className="text-muted-foreground max-w-xl mx-auto">
            C.L.E.O. combines cutting-edge AI with Cronos x402 infrastructure for unparalleled DeFi execution
          </p>
        </motion.div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature, index) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: index * 0.1 }}
              whileHover={{ y: -10, transition: { duration: 0.2 } }}
              className="glass rounded-2xl p-8 group cursor-pointer hover:border-primary/30 transition-colors"
            >
              <div className="w-16 h-16 rounded-xl bg-gradient-primary flex items-center justify-center mb-6 group-hover:shadow-glow transition-shadow">
                <feature.icon className="w-8 h-8 text-primary-foreground" />
              </div>
              <h3 className="font-display text-xl font-semibold mb-3">{feature.title}</h3>
              <p className="text-muted-foreground leading-relaxed">{feature.description}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
};
