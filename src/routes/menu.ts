import { Home, Shuffle, Cpu, Settings, User, Folder, BarChart, CreditCard, ShieldCheck, Vote, TrendingUp, Activity, Wallet, FileText, BookOpen, Bell, Sparkles, PlusCircle, type LucideIcon } from 'lucide-react';

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
  { key: 'payments', title: 'Payments', path: '/payments', icon: CreditCard },
  { key: 'payment-review', title: 'Payment Review', path: '/payment-review', icon: ShieldCheck, requiresAuth: true },
  { key: 'analytics', title: 'Analytics', path: '/analytics', icon: TrendingUp },
  { key: 'transactions', title: 'Transactions', path: '/transactions', icon: Activity },
  { key: 'portfolio', title: 'Portfolio', path: '/portfolio', icon: Wallet },
  { key: 'activity', title: 'Activity', path: '/activity', icon: Bell },
  { key: 'reports', title: 'Reports', path: '/reports', icon: FileText },
  { key: 'documentation', title: 'Documentation', path: '/documentation', icon: BookOpen },
  {
    key: 'dao',
    title: 'DAO Governance',
    path: '/dao',
    icon: Vote,
    children: [
      { key: 'dao-create', title: 'Create Proposal', path: '/dao/create', icon: PlusCircle }
    ]
  },
  { key: 'nft', title: 'NFT Collection', path: '/nft', icon: Sparkles },
  { key: 'app', title: 'CLEO App', path: '/app', icon: Shuffle },
  { key: 'settings', title: 'Settings', path: '/settings', icon: Settings },
  { key: 'account', title: 'Account', path: '/account', icon: User }
];
