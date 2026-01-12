import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { TrendingUp, Zap, PieChart, Activity, Loader2, AlertCircle } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { api, ApiClientError } from '@/lib/api';

interface DashboardMetrics {
  total_volume_usd?: number;
  total_executions?: number;
  avg_savings_pct?: number;
  agent_status?: string;
  success_rate?: number;
  recent_executions?: Array<{
    id: string;
    timestamp: number;
    token_in: string;
    token_out: string;
    amount_in: number;
    amount_out: number;
    savings_pct: number;
    status: string;
  }>;
}

export default function Dashboard() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        setError(null);
        const data = await api.getDashboardMetrics();
        setMetrics(data);
      } catch (err) {
        const errorMessage = err instanceof ApiClientError 
          ? err.message 
          : 'Failed to load dashboard metrics';
        console.error('Failed to load dashboard metrics:', err);
        setError(errorMessage);
      } finally {
        setLoading(false);
      }
    };

    fetchMetrics();
    // Refresh every 30 seconds
    const interval = setInterval(fetchMetrics, 30000);
    return () => clearInterval(interval);
  }, []);

  const formatCurrency = (value: number) => {
    if (value >= 1000000) {
      return `$${(value / 1000000).toFixed(2)}M`;
    }
    return `$${value.toLocaleString()}`;
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
        <p className="text-muted-foreground">Cross-DEX Liquidity Execution Overview</p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : error ? (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Total Volume</CardTitle>
                <TrendingUp className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {metrics?.total_volume_usd ? formatCurrency(metrics.total_volume_usd) : '$0'}
                </div>
                <p className="text-xs text-muted-foreground">All-time volume</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Executions</CardTitle>
                <Zap className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {metrics?.total_executions?.toLocaleString() || '0'}
                </div>
                <p className="text-xs text-muted-foreground">Total successful swaps</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Avg Savings</CardTitle>
                <PieChart className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {metrics?.avg_savings_pct?.toFixed(1) || '0.0'}%
                </div>
                <p className="text-xs text-muted-foreground">vs single-DEX routing</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Agent Status</CardTitle>
                <Activity className={`h-4 w-4 ${metrics?.agent_status === 'active' ? 'text-green-500' : 'text-muted-foreground'}`} />
              </CardHeader>
              <CardContent>
                <div className={`text-2xl font-bold ${metrics?.agent_status === 'active' ? 'text-green-500' : ''}`}>
                  {metrics?.agent_status === 'active' ? 'Active' : 'Offline'}
                </div>
                <p className="text-xs text-muted-foreground">AI routing status</p>
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Recent Executions</CardTitle>
              </CardHeader>
              <CardContent>
                {metrics?.recent_executions && metrics.recent_executions.length > 0 ? (
                  <div className="space-y-2">
                    {metrics.recent_executions.slice(0, 5).map((exec) => (
                      <div key={exec.id} className="flex items-center justify-between p-2 rounded-lg bg-muted/50">
                        <div>
                          <p className="text-sm font-medium">
                            {exec.amount_in.toLocaleString()} {exec.token_in} → {exec.token_out}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {new Date(exec.timestamp * 1000).toLocaleString()}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-sm font-medium text-green-600">
                            +{exec.savings_pct.toFixed(2)}%
                          </p>
                          <p className="text-xs text-muted-foreground capitalize">{exec.status}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">No recent executions to display.</p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Agent Health</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Status</span>
                    <span className={`text-sm font-medium ${metrics?.agent_status === 'active' ? 'text-green-500' : 'text-muted-foreground'}`}>
                      {metrics?.agent_status === 'active' ? 'Operational' : 'Offline'}
                    </span>
                  </div>
                  {metrics?.success_rate && (
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">Success Rate</span>
                      <span className="text-sm font-medium">{metrics.success_rate.toFixed(1)}%</span>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
