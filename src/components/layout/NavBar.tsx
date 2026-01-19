import React from 'react';
import { Link } from 'react-router-dom';
import { Menu, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import ConnectWalletButton from '@/wallet/ConnectWalletButton';

type Props = { onOpenSidebar?: () => void };

export default function NavBar({ onOpenSidebar }: Props) {
  const navLinks = [
    { to: "/execution/routes", label: "Routes", ariaLabel: "View swap routes" },
    { to: "/execution/simulator", label: "Simulator", ariaLabel: "Open route simulator" },
    { to: "/agent", label: "AI Agent", ariaLabel: "View AI agent status" },
    { to: "/dao", label: "Governance", ariaLabel: "DAO governance" },
  ];

  return (
    <header className="sticky top-0 z-30 border-b border-border/50 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 shadow-sm">
      <div className="flex h-14 items-center justify-between px-4">
        <div className="flex items-center gap-4">
          <Button 
            variant="ghost" 
            size="icon" 
            onClick={onOpenSidebar} 
            className="lg:hidden hover:bg-muted/50"
          >
            <Menu className="h-5 w-5" />
          </Button>

          <Link to="/" className="flex items-center gap-2 group">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-primary text-primary-foreground shadow-sm group-hover:shadow-glow transition-all duration-300">
              <Sparkles className="h-4 w-4" />
            </div>
            <div className="hidden sm:block">
              <p className="text-sm font-bold text-foreground">C.L.E.O.</p>
              <p className="text-xs text-muted-foreground">Cross-DEX Execution</p>
            </div>
          </Link>
        </div>

        <nav className="hidden md:flex items-center gap-1" aria-label="Main navigation">
          {navLinks.map((link) => (
            <Link
              key={link.to}
              to={link.to}
              className="text-sm text-muted-foreground hover:text-foreground transition-all duration-200 px-3 py-1.5 rounded-md hover:bg-muted/50 relative group"
              aria-label={link.ariaLabel}
            >
              {link.label}
              <span className="absolute bottom-0 left-1/2 -translate-x-1/2 w-0 h-0.5 bg-primary group-hover:w-3/4 transition-all duration-300" />
            </Link>
          ))}
        </nav>

        <ConnectWalletButton />
      </div>
    </header>
  );
}
