import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Activity as ActivityIcon,
  CheckCircle2,
  XCircle,
  Clock,
  ArrowRight,
  Zap,
  Shield,
  TrendingUp,
  AlertCircle,
  Bell,
  Settings,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface ActivityItem {
  id: string;
  type: 'transaction' | 'settlement' | 'agent' | 'system' | 'alert';
  title: string;
  description: string;
  timestamp: string;
  status: 'success' | 'pending' | 'failed' | 'info';
  icon: React.ComponentType<{ className?: string }>;
}

const mockActivities: ActivityItem[] = [
  {
    id: '1',
    type: 'transaction',
    title: 'Swap Executed',
    description: 'Swapped 1,000 CRO for 950 USDT on VVS Finance',
    timestamp: '2 minutes ago',
    status: 'success',
    icon: CheckCircle2,
  },
  {
    id: '2',
    type: 'agent',
    title: 'AI Agent Decision',
    description: 'Agent optimized route selection, saved 4.2% on gas fees',
    timestamp: '15 minutes ago',
    status: 'success',
    icon: Zap,
  },
  {
    id: '3',
    type: 'settlement',
    title: 'Settlement Pending',
    description: 'Multi-leg settlement in progress (WBTC → ETH)',
    timestamp: '1 hour ago',
    status: 'pending',
    icon: Clock,
  },
  {
    id: '4',
    type: 'system',
    title: 'System Update',
    description: 'Gas price optimization algorithm updated',
    timestamp: '2 hours ago',
    status: 'info',
    icon: Settings,
  },
  {
    id: '5',
    type: 'transaction',
    title: 'Transaction Failed',
    description: 'Swap failed due to insufficient liquidity on Cronaswap',
    timestamp: '3 hours ago',
    status: 'failed',
    icon: XCircle,
  },
  {
    id: '6',
    type: 'alert',
    title: 'High Gas Prices',
    description: 'Current gas prices are 25% above average',
    timestamp: '5 hours ago',
    status: 'info',
    icon: AlertCircle,
  },
  {
    id: '7',
    type: 'settlement',
    title: 'Settlement Completed',
    description: 'Successfully settled 3-leg swap with $450 profit',
    timestamp: '1 day ago',
    status: 'success',
    icon: Shield,
  },
  {
    id: '8',
    type: 'agent',
    title: 'Agent Learning',
    description: 'Agent learned new optimal route pattern',
    timestamp: '1 day ago',
    status: 'success',
    icon: TrendingUp,
  },
];

const typeColors = {
  transaction: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
  settlement: 'bg-purple-500/10 text-purple-500 border-purple-500/20',
  agent: 'bg-green-500/10 text-green-500 border-green-500/20',
  system: 'bg-gray-500/10 text-gray-500 border-gray-500/20',
  alert: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20',
};

const statusColors = {
  success: 'text-green-500',
  pending: 'text-yellow-500',
  failed: 'text-red-500',
  info: 'text-blue-500',
};

export default function Activity() {
  const [filter, setFilter] = useState<string>('all');

  const filteredActivities =
    filter === 'all'
      ? mockActivities
      : mockActivities.filter((activity) => activity.type === filter);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Activity</h1>
          <p className="text-muted-foreground mt-1">
            Real-time activity feed and notifications
          </p>
        </div>
        <Button variant="outline">
          <Bell className="h-4 w-4 mr-2" />
          Notification Settings
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Activities</CardTitle>
            <ActivityIcon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mockActivities.length}</div>
            <p className="text-xs text-muted-foreground mt-1">Last 30 days</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Successful</CardTitle>
            <CheckCircle2 className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-500">
              {mockActivities.filter((a) => a.status === 'success').length}
            </div>
            <p className="text-xs text-muted-foreground mt-1">Completed</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending</CardTitle>
            <Clock className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-500">
              {mockActivities.filter((a) => a.status === 'pending').length}
            </div>
            <p className="text-xs text-muted-foreground mt-1">In progress</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Failed</CardTitle>
            <XCircle className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-500">
              {mockActivities.filter((a) => a.status === 'failed').length}
            </div>
            <p className="text-xs text-muted-foreground mt-1">Errors</p>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="all" className="space-y-4">
        <TabsList>
          <TabsTrigger value="all">All</TabsTrigger>
          <TabsTrigger value="transaction">Transactions</TabsTrigger>
          <TabsTrigger value="settlement">Settlements</TabsTrigger>
          <TabsTrigger value="agent">AI Agent</TabsTrigger>
          <TabsTrigger value="system">System</TabsTrigger>
        </TabsList>

        <TabsContent value="all" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Activity Feed</CardTitle>
              <CardDescription>Recent activities and events</CardDescription>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[600px]">
                <div className="space-y-4">
                  {filteredActivities.map((activity, index) => {
                    const Icon = activity.icon;
                    return (
                      <div
                        key={activity.id}
                        className={cn(
                          'flex items-start gap-4 p-4 rounded-lg border transition-colors',
                          index === 0 && 'bg-primary/5 border-primary/20'
                        )}
                      >
                        <div
                          className={cn(
                            'p-2 rounded-lg border',
                            typeColors[activity.type]
                          )}
                        >
                          <Icon className="h-4 w-4" />
                        </div>
                        <div className="flex-1 space-y-1">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <h4 className="font-semibold">{activity.title}</h4>
                              <Badge
                                variant="outline"
                                className={cn('text-xs', typeColors[activity.type])}
                              >
                                {activity.type}
                              </Badge>
                            </div>
                            <span className="text-xs text-muted-foreground">
                              {activity.timestamp}
                            </span>
                          </div>
                          <p className="text-sm text-muted-foreground">
                            {activity.description}
                          </p>
                        </div>
                        <div className={cn('flex items-center', statusColors[activity.status])}>
                          <Icon className="h-5 w-5" />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>

        {['transaction', 'settlement', 'agent', 'system'].map((type) => (
          <TabsContent key={type} value={type} className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="capitalize">{type} Activities</CardTitle>
                <CardDescription>
                  {type === 'transaction' && 'Transaction-related activities'}
                  {type === 'settlement' && 'Settlement activities'}
                  {type === 'agent' && 'AI agent activities'}
                  {type === 'system' && 'System events and updates'}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[600px]">
                  <div className="space-y-4">
                    {mockActivities
                      .filter((a) => a.type === type)
                      .map((activity) => {
                        const Icon = activity.icon;
                        return (
                          <div
                            key={activity.id}
                            className="flex items-start gap-4 p-4 rounded-lg border hover:bg-muted/50 transition-colors"
                          >
                            <div
                              className={cn(
                                'p-2 rounded-lg border',
                                typeColors[activity.type]
                              )}
                            >
                              <Icon className="h-4 w-4" />
                            </div>
                            <div className="flex-1 space-y-1">
                              <div className="flex items-center justify-between">
                                <h4 className="font-semibold">{activity.title}</h4>
                                <span className="text-xs text-muted-foreground">
                                  {activity.timestamp}
                                </span>
                              </div>
                              <p className="text-sm text-muted-foreground">
                                {activity.description}
                              </p>
                            </div>
                            <div className={cn('flex items-center', statusColors[activity.status])}>
                              <Icon className="h-5 w-5" />
                            </div>
                          </div>
                        );
                      })}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}

