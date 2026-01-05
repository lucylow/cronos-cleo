import { motion } from "framer-motion";
import { Github, Twitter } from "lucide-react";

export const Footer = () => {
  return (
    <footer id="resources" className="py-20 border-t border-border/50">
      <div className="container mx-auto px-4">
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-12 mb-16">
          {/* Brand */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h3 className="font-display text-2xl font-bold text-gradient-primary mb-4">C.L.E.O.</h3>
            <p className="text-muted-foreground mb-6">
              Cronos Liquidity Execution Orchestrator<br />
              AI-Powered Multi-DEX Routing via x402
            </p>
            <div className="flex gap-4">
              <a href="https://github.com" target="_blank" rel="noopener noreferrer" className="text-foreground/70 hover:text-secondary transition-colors">
                <Github className="w-6 h-6" />
              </a>
              <a href="https://twitter.com/cronos_chain" target="_blank" rel="noopener noreferrer" className="text-foreground/70 hover:text-secondary transition-colors">
                <Twitter className="w-6 h-6" />
              </a>
            </div>
          </motion.div>

          {/* Hackathon Links */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.1 }}
          >
            <h4 className="font-display font-semibold mb-4">Hackathon Links</h4>
            <ul className="space-y-3 text-muted-foreground">
              <li>
                <a href="https://hackathon.cronos.org" target="_blank" rel="noopener noreferrer" className="hover:text-secondary transition-colors">
                  Cronos x402 Hackathon
                </a>
              </li>
              <li>
                <a href="https://docs.cronos.org" target="_blank" rel="noopener noreferrer" className="hover:text-secondary transition-colors">
                  Cronos Documentation
                </a>
              </li>
              <li>
                <a href="https://github.com/cronos-labs/x402-examples" target="_blank" rel="noopener noreferrer" className="hover:text-secondary transition-colors">
                  x402 Examples
                </a>
              </li>
            </ul>
          </motion.div>

          {/* Technical Stack */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.2 }}
          >
            <h4 className="font-display font-semibold mb-4">Technical Stack</h4>
            <ul className="space-y-3 text-muted-foreground">
              <li>Cronos EVM</li>
              <li>x402 Facilitator</li>
              <li>Crypto.com AI Agent SDK</li>
              <li>VVS Finance Integration</li>
            </ul>
          </motion.div>

          {/* Project Status */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 }}
          >
            <h4 className="font-display font-semibold mb-4">Project Status</h4>
            <div className="glass rounded-xl p-4 border-secondary/30">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-2.5 h-2.5 bg-secondary rounded-full animate-pulse" />
                <span className="font-semibold text-sm">Cronos Hackathon 2025</span>
              </div>
              <p className="text-sm text-muted-foreground">Track: x402 Agentic Finance/Payment</p>
              <p className="text-sm text-muted-foreground">Submission Deadline: Jan 23, 2026</p>
            </div>
          </motion.div>
        </div>

        {/* Copyright */}
        <div className="pt-8 border-t border-border/30 text-center text-muted-foreground">
          <p>C.L.E.O. - Cronos Liquidity Execution Orchestrator • Built for the Cronos x402 Paytech Hackathon 2025</p>
          <p className="text-sm mt-2">This is a demonstration project for hackathon submission purposes.</p>
        </div>
      </div>
    </footer>
  );
};
