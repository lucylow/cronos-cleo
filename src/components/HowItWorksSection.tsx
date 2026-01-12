import { motion } from "framer-motion";
import { Send, Search, Cpu, Zap, TrendingUp, ArrowRight } from "lucide-react";

const steps = [
  {
    number: 1,
    icon: Send,
    title: "Trade Request",
    description: "User or AI agent submits swap request with parameters (token pair, amount, slippage tolerance).",
    color: "primary",
  },
  {
    number: 2,
    icon: Search,
    title: "Liquidity Analysis",
    description: "C.L.E.O. scans all integrated Cronos DEXs for real-time liquidity, prices, and pool depths.",
    color: "secondary",
  },
  {
    number: 3,
    icon: Cpu,
    title: "AI Optimization",
    description: "Machine learning model calculates optimal split ratios to minimize slippage and gas costs.",
    color: "accent",
  },
  {
    number: 4,
    icon: Zap,
    title: "x402 Execution",
    description: "Atomic multi-DEX execution via Cronos x402 facilitator - all or nothing settlement.",
    color: "secondary",
  },
  {
    number: 5,
    icon: TrendingUp,
    title: "Result & Learning",
    description: "Trade results are recorded to improve future optimizations through reinforcement learning.",
    color: "primary",
  },
];

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.15,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 40, scale: 0.9 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      type: "spring" as const,
      stiffness: 80,
      damping: 15,
    },
  },
};

export const HowItWorksSection = () => {
  return (
    <section id="how-it-works" className="py-28 relative overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 bg-gradient-to-b from-card/30 via-card/60 to-card/30" />
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-primary/5 rounded-full blur-[120px]" />
      
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
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-secondary/10 border border-secondary/20 mb-6"
          >
            <Zap className="w-4 h-4 text-secondary" />
            <span className="text-sm font-medium text-secondary">5-Step Process</span>
          </motion.div>
          
          <h2 className="font-display text-4xl md:text-5xl font-bold mb-6">
            How <span className="text-gradient-primary">C.L.E.O.</span> Works
          </h2>
          <p className="text-muted-foreground max-w-2xl mx-auto text-lg">
            The AI orchestration process from trade request to optimized execution
          </p>
        </motion.div>

        {/* Desktop Timeline */}
        <div className="hidden lg:block relative">
          {/* Connection Line */}
          <div className="absolute top-16 left-[10%] right-[10%] h-1 bg-border rounded-full overflow-hidden">
            <motion.div
              initial={{ scaleX: 0 }}
              whileInView={{ scaleX: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 1.5, ease: "easeOut" }}
              className="h-full bg-gradient-to-r from-primary via-secondary to-primary origin-left"
            />
          </div>

          <motion.div
            variants={containerVariants}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-50px" }}
            className="grid grid-cols-5 gap-6"
          >
            {steps.map((step, index) => (
              <motion.div
                key={step.number}
                variants={itemVariants}
                className="text-center relative group"
              >
                {/* Step circle */}
                <motion.div
                  whileHover={{ scale: 1.1 }}
                  className="relative mx-auto mb-8"
                >
                  <div className={`w-20 h-20 rounded-full bg-gradient-primary flex items-center justify-center relative z-10 border-4 border-background shadow-glow group-hover:shadow-[0_0_50px_hsl(var(--primary)/0.5)] transition-shadow duration-300`}>
                    <step.icon className="w-8 h-8 text-primary-foreground" />
                  </div>
                  
                  {/* Pulse ring */}
                  <div className="absolute inset-0 rounded-full bg-primary/20 animate-ping opacity-30" style={{ animationDuration: "2s" }} />
                  
                  {/* Number badge */}
                  <div className="absolute -top-2 -right-2 w-7 h-7 rounded-full bg-secondary flex items-center justify-center text-sm font-bold text-secondary-foreground z-20">
                    {step.number}
                  </div>
                </motion.div>
                
                <h3 className="font-display text-lg font-semibold mb-3 group-hover:text-primary transition-colors">
                  {step.title}
                </h3>
                <p className="text-muted-foreground text-sm leading-relaxed px-2">
                  {step.description}
                </p>
              </motion.div>
            ))}
          </motion.div>
        </div>

        {/* Mobile/Tablet Timeline */}
        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          className="lg:hidden space-y-6"
        >
          {steps.map((step, index) => (
            <motion.div
              key={step.number}
              variants={itemVariants}
              className="flex gap-6 items-start relative"
            >
              {/* Vertical line */}
              {index < steps.length - 1 && (
                <div className="absolute left-[28px] top-16 bottom-0 w-0.5 bg-border" />
              )}
              
              {/* Step circle */}
              <div className="flex-shrink-0 relative">
                <div className="w-14 h-14 rounded-full bg-gradient-primary flex items-center justify-center shadow-glow">
                  <step.icon className="w-6 h-6 text-primary-foreground" />
                </div>
                <div className="absolute -top-1 -right-1 w-6 h-6 rounded-full bg-secondary flex items-center justify-center text-xs font-bold text-secondary-foreground">
                  {step.number}
                </div>
              </div>
              
              {/* Content */}
              <div className="flex-1 glass rounded-xl p-5 border border-border/50">
                <h3 className="font-display text-lg font-semibold mb-2">
                  {step.title}
                </h3>
                <p className="text-muted-foreground text-sm leading-relaxed">
                  {step.description}
                </p>
              </div>
            </motion.div>
          ))}
        </motion.div>

        {/* CTA */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.5 }}
          className="text-center mt-16"
        >
          <a
            href="#demo"
            className="inline-flex items-center gap-2 text-secondary hover:text-secondary/80 font-medium transition-colors group"
          >
            Try the interactive demo
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </a>
        </motion.div>
      </div>
    </section>
  );
};
