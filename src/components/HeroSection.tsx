import { motion } from "framer-motion";
import { Zap, Bot, Layers, Fuel, PlayCircle, Trophy } from "lucide-react";
import { Button } from "@/components/ui/button";

const badges = [
  { icon: Zap, label: "x402 Atomic Execution" },
  { icon: Bot, label: "AI-Optimized Routing" },
  { icon: Layers, label: "Multi-DEX Aggregation" },
  { icon: Fuel, label: "Gas Optimization" },
];

export const HeroSection = () => {
  return (
    <section className="relative min-h-screen flex items-center justify-center pt-20 overflow-hidden">
      {/* Background Effects */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/4 left-1/5 w-96 h-96 bg-primary/10 rounded-full blur-3xl animate-pulse" />
        <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-secondary/10 rounded-full blur-3xl animate-pulse" style={{ animationDelay: "1s" }} />
      </div>

      <div className="container mx-auto px-4 text-center relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
        >
          <h1 className="font-display font-bold mb-4">
            <motion.span 
              className="block text-5xl md:text-7xl lg:text-8xl text-gradient-primary mb-2"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5, delay: 0.2 }}
            >
              C.L.E.O.
            </motion.span>
            <motion.span 
              className="block text-2xl md:text-3xl lg:text-4xl text-gradient-hero"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.5, delay: 0.4 }}
            >
              Cronos Liquidity Execution Orchestrator
            </motion.span>
          </h1>
          
          <motion.p 
            className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto mb-10"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6 }}
          >
            AI-Powered Multi-DEX Routing via x402 • Reduce slippage by up to 90% with atomic cross-DEX execution on Cronos
          </motion.p>

          {/* Badges */}
          <motion.div 
            className="flex flex-wrap justify-center gap-3 mb-12"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.8 }}
          >
            {badges.map((badge, index) => (
              <motion.div
                key={badge.label}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.8 + index * 0.1 }}
                className="glass px-4 py-2 rounded-full flex items-center gap-2 text-sm font-medium"
              >
                <badge.icon className="w-4 h-4 text-secondary" />
                <span>{badge.label}</span>
              </motion.div>
            ))}
          </motion.div>

          {/* CTA Buttons */}
          <motion.div 
            className="flex flex-col sm:flex-row gap-4 justify-center"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1 }}
          >
            <Button size="lg" className="bg-gradient-primary hover:shadow-glow transition-all duration-300" asChild>
              <a href="#demo">
                <PlayCircle className="w-5 h-5 mr-2" />
                Try Interactive Demo
              </a>
            </Button>
            <Button variant="outline" size="lg" asChild>
              <a href="https://hackathon.cronos.org" target="_blank" rel="noopener noreferrer">
                <Trophy className="w-5 h-5 mr-2" />
                Cronos Hackathon Entry
              </a>
            </Button>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
};
