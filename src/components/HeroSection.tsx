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
    <section className="relative min-h-screen flex items-center justify-center pt-24 pb-16 overflow-hidden">
      {/* Enhanced Background Effects */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/4 left-1/5 w-[500px] h-[500px] bg-primary/15 rounded-full blur-[120px] animate-pulse" />
        <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] bg-secondary/12 rounded-full blur-[100px] animate-pulse" style={{ animationDelay: "1s" }} />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-accent/5 rounded-full blur-[150px]" />
        {/* Grid overlay */}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(139,92,246,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(139,92,246,0.03)_1px,transparent_1px)] bg-[size:60px_60px]" />
      </div>

      <div className="container mx-auto px-4 text-center relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.9, ease: "easeOut" }}
        >
          {/* Pre-title badge */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-primary/10 border border-primary/20 text-primary text-sm font-medium mb-8"
          >
            <Zap className="w-3.5 h-3.5" />
            Powered by x402 Protocol
          </motion.div>

          <h1 className="font-display font-bold mb-6">
            <motion.span 
              className="block text-6xl md:text-8xl lg:text-9xl text-gradient-primary mb-3 tracking-tight"
              initial={{ opacity: 0, scale: 0.9, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.2, ease: "easeOut" }}
            >
              C.L.E.O.
            </motion.span>
            <motion.span 
              className="block text-xl md:text-2xl lg:text-3xl text-muted-foreground font-normal tracking-wide"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.4 }}
            >
              Cronos Liquidity Execution Orchestrator
            </motion.span>
          </h1>
          
          <motion.p 
            className="text-lg md:text-xl text-muted-foreground/80 max-w-2xl mx-auto mb-12 leading-relaxed"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6 }}
          >
            AI-powered multi-DEX routing with atomic cross-DEX execution. 
            <span className="text-foreground font-medium"> Reduce slippage by up to 90%</span> on Cronos.
          </motion.p>

          {/* Feature Badges */}
          <motion.div 
            className="flex flex-wrap justify-center gap-3 mb-14"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.8 }}
          >
            {badges.map((badge, index) => (
              <motion.div
                key={badge.label}
                initial={{ opacity: 0, scale: 0.8, y: 10 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                transition={{ delay: 0.8 + index * 0.1, type: "spring", stiffness: 200 }}
                whileHover={{ scale: 1.05, y: -2 }}
                className="glass px-5 py-2.5 rounded-full flex items-center gap-2.5 text-sm font-medium border border-border/50 hover:border-primary/30 transition-colors cursor-default"
              >
                <badge.icon className="w-4 h-4 text-primary" />
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
            <Button size="lg" className="bg-gradient-primary hover:shadow-glow transition-all duration-300 text-base px-8 h-12" asChild>
              <a href="#demo">
                <PlayCircle className="w-5 h-5 mr-2" />
                Try Interactive Demo
              </a>
            </Button>
            <Button variant="outline" size="lg" className="border-border/60 hover:bg-muted/50 text-base px-8 h-12" asChild>
              <a href="https://hackathon.cronos.org" target="_blank" rel="noopener noreferrer">
                <Trophy className="w-5 h-5 mr-2" />
                Cronos Hackathon Entry
              </a>
            </Button>
          </motion.div>

          {/* Scroll indicator */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1.5 }}
            className="absolute bottom-8 left-1/2 -translate-x-1/2"
          >
            <motion.div
              animate={{ y: [0, 8, 0] }}
              transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
              className="w-6 h-10 rounded-full border-2 border-muted-foreground/30 flex justify-center pt-2"
            >
              <div className="w-1.5 h-1.5 rounded-full bg-muted-foreground/50" />
            </motion.div>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
};
