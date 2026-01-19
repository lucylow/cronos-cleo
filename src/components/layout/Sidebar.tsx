import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { APP_ROUTES } from '@/routes/menu';
import { cn } from '@/lib/utils';
import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';

type Props = { open?: boolean; onClose?: () => void };

export default function Sidebar({ open = false, onClose }: Props) {
  const location = useLocation();
  const pathname = location.pathname;

  const isActive = (path: string) => {
    if (path === '/') return pathname === '/';
    return pathname.startsWith(path);
  };

  return (
    <>
      {/* Mobile overlay */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          />
        )}
      </AnimatePresence>

      {/* Sidebar */}
      <motion.aside
        initial={false}
        animate={{ x: open ? 0 : '-100%' }}
        transition={{ type: 'spring', damping: 25, stiffness: 200 }}
        className={cn(
          "fixed top-0 left-0 z-50 h-full w-64 sm:w-72 bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/60 border-r border-border/50",
          "lg:translate-x-0 lg:static lg:z-auto"
        )}
        aria-label="Sidebar navigation"
        role="navigation"
      >
        <div className="flex items-center justify-between p-4 border-b border-border/50 bg-gradient-to-r from-primary/5 to-transparent">
          <span className="text-sm font-semibold text-foreground">Navigation</span>
          <Button variant="ghost" size="icon" onClick={onClose} className="lg:hidden hover:bg-muted/50">
            <X className="h-4 w-4" />
          </Button>
        </div>

        <nav className="p-4 space-y-2 overflow-y-auto h-[calc(100%-60px)]">
          {APP_ROUTES.map((route) => {
            const Icon = route.icon;
            const active = isActive(route.path);
            
            return (
              <div key={route.key}>
                <Link
                  to={route.path}
                  onClick={onClose}
                  className={cn(
                    "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 relative group",
                    active
                      ? "bg-primary/10 text-primary border border-primary/20 shadow-sm"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted/50 hover:border-border/50 border border-transparent"
                  )}
                  aria-current={active ? "page" : undefined}
                  aria-label={`Navigate to ${route.title}`}
                >
                  {Icon && (
                    <Icon className={cn(
                      "h-4 w-4 transition-transform",
                      active ? "text-primary" : "group-hover:scale-110"
                    )} aria-hidden="true" />
                  )}
                  <span className="relative z-10">{route.title}</span>
                </Link>
                
                {route.children && (
                  <div className="ml-6 mt-1 space-y-1">
                    {route.children.map((child) => {
                      const childActive = isActive(child.path);
                      const ChildIcon = child.icon;
                      return (
                        <Link
                          key={child.key}
                          to={child.path}
                          onClick={onClose}
                          className={cn(
                            "flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-all duration-200",
                            childActive
                              ? "text-primary bg-primary/10 border border-primary/20 font-medium"
                              : "text-muted-foreground hover:text-foreground hover:bg-muted/30 border border-transparent"
                          )}
                          aria-current={childActive ? "page" : undefined}
                          aria-label={`Navigate to ${child.title}`}
                        >
                          {ChildIcon && <ChildIcon className="h-3.5 w-3.5" aria-hidden="true" />}
                          {child.title}
                        </Link>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </nav>
      </motion.aside>
    </>
  );
}
