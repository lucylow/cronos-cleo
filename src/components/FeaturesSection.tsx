import { motion } from "framer-motion";
import { Bot, Atom, Network, Fuel, Shield, LineChart, Sparkles } from "lucide-react";

const features = [
  {
    icon: Bot,
    title: "AI-Powered Routing",
    description: "Machine learning algorithms analyze real-time liquidity, volatility, and gas prices to determine optimal split ratios across DEXs.",
    gradient: "from-primary to-primary-foreground/20",
  },
  {
    icon: Atom,
    title: "x402 Atomic Execution",
    description: "Execute multi-DEX trades atomically via Cronos x402. All swaps succeed or all revert - eliminating partial execution risk.",
    gradient: "from-secondary to-secondary/20",
  },
  {
    icon: Network,
    title: "Multi-DEX Aggregation",
    description: "Intelligently splits orders across VVS Finance, CronaSwap, MM Finance, and other Cronos DEXs for maximum liquidity access.",
    gradient: "from-accent to-accent/20",
  },
  {
    icon: Fuel,
    title: "Gas Optimization",
    description: "Batch transactions and share approvals to minimize gas costs, leveraging Cronos's low-fee environment for complex operations.",
    gradient: "from-emerald-500 to-emerald-500/20",
  },
  {
    icon: Shield,
    title: "MEV Protection",
    description: "Advanced routing strategies and timing algorithms protect against front-running and sandwich attacks common in DeFi.",
    gradient: "from-amber-500 to-amber-500/20",
  },
  {
    icon: LineChart,
    title: "Real-time Analytics",
    description: "Comprehensive dashboards showing execution quality, slippage savings, and performance metrics for every trade.",
    gradient: "from-sky-500 to-sky-500/20",
  },
];

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 30, scale: 0.95 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      type: "spring" as const,
      stiffness: 100,
      damping: 15,
    },
  },
};

export const FeaturesSection = () => {
  return (
    <section id="features" className="py-28 relative overflow-hidden">
      {/* Background elements */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/4 left-0 w-[500px] h-[500px] bg-primary/5 rounded-full blur-[100px]" />
        <div className="absolute bottom-1/4 right-0 w-[400px] h-[400px] bg-secondary/5 rounded-full blur-[100px]" />
      </div>

      <div className="container mx-auto px-4 relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-20"
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 border border-primary/20 mb-6"
          >
            <Sparkles className="w-4 h-4 text-primary" />
            <span className="text-sm font-medium text-primary">Powerful Capabilities</span>
          </motion.div>
          
          <h2 className="font-display text-4xl md:text-5xl font-bold mb-6">
            Built for <span className="text-gradient-primary">Optimal Execution</span>
          </h2>
          <p className="text-muted-foreground max-w-2xl mx-auto text-lg">
            C.L.E.O. combines cutting-edge AI with Cronos x402 infrastructure for unparalleled DeFi execution performance
          </p>
        </motion.div>

        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          className="grid md:grid-cols-2 lg:grid-cols-3 gap-6"
        >
          {features.map((feature) => (
            <motion.div
              key={feature.title}
              variants={itemVariants}
              whileHover={{ y: -8, transition: { duration: 0.2 } }}
              className="group relative"
            >
              {/* Card glow effect on hover */}
              <div className="absolute inset-0 rounded-2xl bg-gradient-to-br opacity-0 group-hover:opacity-100 transition-opacity duration-500 blur-xl -z-10"
                style={{ background: `linear-gradient(135deg, hsl(var(--primary) / 0.2), hsl(var(--secondary) / 0.1))` }}
              />
              
              <div className="glass rounded-2xl p-8 h-full border border-border/50 group-hover:border-primary/30 transition-all duration-300 relative overflow-hidden">
                {/* Subtle gradient overlay */}
                <div className={`absolute top-0 right-0 w-32 h-32 bg-gradient-to-bl ${feature.gradient} opacity-10 blur-2xl`} />
                
                <div className="relative z-10">
                  <div className="w-14 h-14 rounded-xl bg-gradient-primary flex items-center justify-center mb-6 group-hover:shadow-glow group-hover:scale-110 transition-all duration-300">
                    <feature.icon className="w-7 h-7 text-primary-foreground" />
                  </div>
                  <h3 className="font-display text-xl font-semibold mb-3 group-hover:text-primary transition-colors">
                    {feature.title}
                  </h3>
                  <p className="text-muted-foreground leading-relaxed">
                    {feature.description}
                  </p>
                </div>
              </div>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
};
