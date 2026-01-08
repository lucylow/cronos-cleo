import { Home, Shuffle, Cpu, Settings, User, Folder, BarChart, CreditCard, type LucideIcon } from 'lucide-react';

export type AppRoute = {
  key: string;
  title: string;
  path: string;
  icon?: LucideIcon;
  children?: AppRoute[];
  requiresAuth?: boolean;
};

export const APP_ROUTES: AppRoute[] = [
  { key: 'dashboard', title: 'Dashboard', path: '/dashboard', icon: Home },
  {
    key: 'execution',
    title: 'Execution',
    path: '/execution',
    icon: Shuffle,
    children: [
      { key: 'routes', title: 'Routes', path: '/execution/routes', icon: Folder },
      { key: 'simulator', title: 'Simulator', path: '/execution/simulator', icon: BarChart }
    ]
  },
  {
    key: 'agent',
    title: 'AI Agent',
    path: '/agent',
    icon: Cpu,
    children: [
      { key: 'decisions', title: 'Decisions', path: '/agent/decisions' },
      { key: 'logs', title: 'Agent Logs', path: '/agent/logs' }
    ]
  },
  { key: 'settlement', title: 'Settlement', path: '/settlement', icon: CreditCard },
  { key: 'app', title: 'CLEO App', path: '/app', icon: Shuffle },
  { key: 'settings', title: 'Settings', path: '/settings', icon: Settings },
  { key: 'account', title: 'Account', path: '/account', icon: User }
];
