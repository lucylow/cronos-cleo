import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Bot, Menu, X, Github, Rocket } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";
import ConnectWalletButton from "@/wallet/ConnectWalletButton";

const navLinks = [
  { href: "#demo", label: "Demo" },
  { href: "#features", label: "Features" },
  { href: "#how-it-works", label: "How It Works" },
  { href: "#resources", label: "Resources" },
];

export const Header = () => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  return (
    <header className="fixed top-0 w-full z-50 glass-strong border-b border-border/40 shadow-card">
      <div className="container mx-auto px-4 py-3">
        <nav className="flex justify-between items-center">
          <motion.div 
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex items-center gap-3 group cursor-pointer"
          >
            <div className="w-10 h-10 rounded-xl bg-gradient-primary flex items-center justify-center shadow-glow group-hover:shadow-glow-primary group-hover:scale-110 transition-all duration-300">
              <Bot className="w-5 h-5 text-primary-foreground" />
            </div>
            <span className="font-display font-extrabold text-xl text-gradient-primary group-hover:opacity-90 transition-opacity">
              C.L.E.O.
            </span>
          </motion.div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-6">
            {navLinks.map((link, index) => (
              <motion.a
                key={link.href}
                href={link.href}
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className="text-foreground/70 hover:text-foreground transition-colors font-medium text-sm relative group"
              >
                {link.label}
                <span className="absolute -bottom-1 left-0 w-0 h-0.5 bg-gradient-primary group-hover:w-full transition-all duration-300" />
              </motion.a>
            ))}
          </div>

          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="hidden md:flex items-center gap-3"
          >
            <Button variant="ghost" size="sm" asChild className="text-muted-foreground hover:text-foreground">
              <a href="https://github.com" target="_blank" rel="noopener noreferrer">
                <Github className="w-4 h-4" />
              </a>
            </Button>
            <ConnectWalletButton />
            <Button asChild size="sm" className="bg-gradient-primary hover:shadow-glow-primary transition-all duration-300 hover:scale-105">
              <Link to="/dashboard">
                <Rocket className="w-4 h-4 mr-2" />
                Launch App
              </Link>
            </Button>
          </motion.div>

          {/* Mobile Menu Button */}
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden"
            onClick={() => setIsMenuOpen(!isMenuOpen)}
          >
            {isMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </Button>
        </nav>

        {/* Mobile Navigation */}
        <AnimatePresence>
          {isMenuOpen && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="md:hidden mt-4 pb-4 border-t border-border/50"
            >
              <div className="flex flex-col gap-4 pt-4">
                {navLinks.map((link) => (
                  <a
                    key={link.href}
                    href={link.href}
                    onClick={() => setIsMenuOpen(false)}
                    className="text-foreground/80 hover:text-secondary transition-colors font-medium py-2"
                  >
                    {link.label}
                  </a>
                ))}
                <div className="flex flex-col gap-3 pt-2">
                  <ConnectWalletButton />
                  <Button asChild className="bg-gradient-primary">
                    <Link to="/dashboard" onClick={() => setIsMenuOpen(false)}>
                      <Rocket className="w-4 h-4 mr-2" />
                      Launch App
                    </Link>
                  </Button>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </header>
  );
};
