import React from 'react';
import { Link } from 'react-router-dom';
import { Menu, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import ConnectWalletButton from '@/wallet/ConnectWalletButton';

type Props = { onOpenSidebar?: () => void };

export default function NavBar({ onOpenSidebar }: Props) {
  return (
    <header className="sticky top-0 z-30 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-14 items-center justify-between px-4">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={onOpenSidebar} className="lg:hidden">
            <Menu className="h-5 w-5" />
          </Button>

          <Link to="/" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <Sparkles className="h-4 w-4" />
            </div>
            <div className="hidden sm:block">
              <p className="text-sm font-bold text-foreground">C.L.E.O.</p>
              <p className="text-xs text-muted-foreground">Cross-DEX Execution</p>
            </div>
          </Link>
        </div>

        <nav className="hidden md:flex items-center gap-6">
          <Link to="/execution/routes" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
            Routes
          </Link>
          <Link to="/execution/simulator" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
            Simulator
          </Link>
          <Link to="/agent" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
            AI Agent
          </Link>
          <Link to="/dao" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
            Governance
          </Link>
        </nav>

        <ConnectWalletButton />
      </div>
    </header>
  );
}
