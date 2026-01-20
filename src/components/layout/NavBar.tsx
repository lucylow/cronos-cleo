import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Menu, Sparkles, User, LogOut } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import ConnectWalletButton from '@/wallet/ConnectWalletButton';
import { useAuth } from '@/contexts/AuthContext';

type Props = { onOpenSidebar?: () => void };

export default function NavBar({ onOpenSidebar }: Props) {
  const { isAuthenticated, user, signOut } = useAuth();
  const navigate = useNavigate();
  
  const navLinks = [
    { to: "/execution/routes", label: "Routes", ariaLabel: "View swap routes" },
    { to: "/execution/simulator", label: "Simulator", ariaLabel: "Open route simulator" },
    { to: "/agent", label: "AI Agent", ariaLabel: "View AI agent status" },
    { to: "/dao", label: "Governance", ariaLabel: "DAO governance" },
  ];

  const handleSignOut = () => {
    signOut();
    navigate('/signin');
  };

  const getInitials = (name?: string, email?: string) => {
    if (name) {
      return name
        .split(' ')
        .map(n => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2);
    }
    if (email) {
      return email[0].toUpperCase();
    }
    return 'U';
  };

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

        <div className="flex items-center gap-2">
          <ConnectWalletButton />
          
          {isAuthenticated ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="relative h-9 w-9 rounded-full">
                  <Avatar className="h-9 w-9">
                    <AvatarFallback>
                      {getInitials(user?.name, user?.email)}
                    </AvatarFallback>
                  </Avatar>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuLabel>
                  <div className="flex flex-col space-y-1">
                    <p className="text-sm font-medium leading-none">
                      {user?.name || 'Account'}
                    </p>
                    <p className="text-xs leading-none text-muted-foreground">
                      {user?.email}
                    </p>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild>
                  <Link to="/account" className="cursor-pointer">
                    <User className="mr-2 h-4 w-4" />
                    Account Settings
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleSignOut} className="cursor-pointer text-destructive">
                  <LogOut className="mr-2 h-4 w-4" />
                  Sign Out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <Button variant="outline" onClick={() => navigate('/signin')}>
              Sign In
            </Button>
          )}
        </div>
      </div>
    </header>
  );
}
