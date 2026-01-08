'use client';

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
          "fixed top-0 left-0 z-50 h-full w-64 bg-card border-r border-border",
          "lg:translate-x-0 lg:static lg:z-auto"
        )}
      >
        <div className="flex items-center justify-between p-4 border-b border-border">
          <span className="text-sm font-semibold text-foreground">Navigation</span>
          <Button variant="ghost" size="icon" onClick={onClose} className="lg:hidden">
            <X className="h-4 w-4" />
          </Button>
        </div>

        <nav className="p-4 space-y-1 overflow-y-auto h-[calc(100%-60px)]">
          {APP_ROUTES.map((route) => {
            const Icon = route.icon;
            const active = isActive(route.path);
            
            return (
              <div key={route.key}>
                <Link
                  to={route.path}
                  onClick={onClose}
                  className={cn(
                    "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                    active
                      ? "bg-primary/10 text-primary"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted"
                  )}
                >
                  {Icon && <Icon className="h-4 w-4" />}
                  {route.title}
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
                            "flex items-center gap-2 px-3 py-1.5 rounded-md text-sm transition-colors",
                            childActive
                              ? "text-primary bg-primary/5"
                              : "text-muted-foreground hover:text-foreground"
                          )}
                        >
                          {ChildIcon && <ChildIcon className="h-3.5 w-3.5" />}
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
