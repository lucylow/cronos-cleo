import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Cpu, Activity, Clock, CheckCircle, Loader2, AlertCircle, Info, RefreshCw, Brain, TrendingUp } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { api } from '@/lib/api';

interface AIModelStatus {
  is_trained?: boolean;
  version?: string;
  model_name?: string;
}

interface AIModels {
  available?: boolean;
  initialized?: boolean;
  models?: Record<string, AIModelStatus>;
}

interface AgentStatus {
  status?: string;
  available?: boolean;
  decisions_today?: number;
  successful_decisions?: number;
  failed_decisions?: number;
  success_rate?: number;
  avg_response_time_ms?: number;
  ai_predictions_used?: number;
  ai_models?: AIModels;
  recent_decisions?: Array<{
    id: string;
    timestamp: number;
    route: string;
    details: string;
    status: string;
  }>;
}

// Mock data for demo when backend is unavailable
const MOCK_AGENT_STATUS: AgentStatus = {
  status: 'online',
  available: true,
  decisions_today: 1247,
  avg_response_time_ms: 42,
  recent_decisions: [
    {
      id: 'dec_001',
      timestamp: Math.floor(Date.now() / 1000) - 120,
      route: 'VVS 45% → MMF 35% → CronaSwap 20%',
      details: 'Optimized 50,000 CRO → USDC.e swap with 0.18% slippage',
      status: 'success',
    },
    {
      id: 'dec_002',
      timestamp: Math.floor(Date.now() / 1000) - 340,
      route: 'MMF 60% → VVS 40%',
      details: 'Split route for 25,000 USDC → CRO, saved 12 bps vs single DEX',
      status: 'success',
    },
    {
      id: 'dec_003',
      timestamp: Math.floor(Date.now() / 1000) - 890,
      route: 'VVS 100%',
      details: 'Single DEX optimal for 5,000 CRO trade (low liquidity impact)',
      status: 'success',
    },
    {
      id: 'dec_004',
      timestamp: Math.floor(Date.now() / 1000) - 1500,
      route: 'CronaSwap 55% → MMF 45%',
      details: 'MEV-protected execution for 100,000 CRO → WETH',
      status: 'success',
    },
  ],
};

export default function Agent() {
  const [agentStatus, setAgentStatus] = useState<AgentStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [usingMockData, setUsingMockData] = useState(false);

  const fetchStatus = async () => {
    try {
      setLoading(true);
      // Try to fetch from API - will automatically fallback to mock data on failure
      const data = await api.getAgentStatus();
      
      // Check if this is mock data by checking if backend is actually available
      // Do this check in parallel to avoid delaying the display
      api.health({ timeout: 2000, retries: 0 })
        .then(isAvailable => {
          setUsingMockData(!isAvailable || !data || Object.keys(data).length === 0);
        })
        .catch(() => {
          setUsingMockData(true);
        });
      
      setAgentStatus(data);
    } catch (err) {
      // Even if there's an error, mock data should have been returned by the API client
      console.error('Failed to load agent status:', err);
      setUsingMockData(true);
      // API client should have returned mock data automatically, but ensure we have something
      setAgentStatus((prev) => prev || MOCK_AGENT_STATUS);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    // Refresh every 10 seconds
    const interval = setInterval(fetchStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  const formatTimeAgo = (timestamp: number) => {
    const seconds = Math.floor((Date.now() / 1000) - timestamp);
    if (seconds < 60) return `${seconds}s ago`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    return `${hours}h ago`;
  };

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-foreground">AI Agent</h1>
        <p className="text-muted-foreground">Intelligent routing decisions powered by Crypto.com AI Agent SDK</p>
      </header>

      {loading ? (
        <div className="space-y-6">
          <div className="grid gap-4 md:grid-cols-3">
            {[...Array(3)].map((_, i) => (
              <Card key={i}>
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-4 w-4 rounded" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-7 w-28 mb-2" />
                  <Skeleton className="h-3 w-32" />
                </CardContent>
              </Card>
            ))}
          </div>
          <Card>
            <CardHeader>
              <Skeleton className="h-6 w-32" />
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {[...Array(4)].map((_, i) => (
                  <Skeleton key={i} className="h-20 w-full" />
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      ) : (
        <>
          {usingMockData && (
            <Alert>
              <Info className="h-4 w-4" />
              <AlertDescription className="flex items-center justify-between">
                <span>
                  Backend not connected. Showing demo data. Start the backend at <code className="text-xs bg-muted px-1 py-0.5 rounded">cleo_project/backend</code> for live data.
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={fetchStatus}
                  className="ml-4"
                >
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Retry
                </Button>
              </AlertDescription>
            </Alert>
          )}

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Status</CardTitle>
                <Cpu className={`h-4 w-4 ${agentStatus?.status === 'online' ? 'text-green-500' : 'text-muted-foreground'}`} />
              </CardHeader>
              <CardContent>
                <div className={`text-xl font-bold ${agentStatus?.status === 'online' ? 'text-green-500' : 'text-muted-foreground'}`}>
                  {agentStatus?.status === 'online' ? 'Online' : 'Offline'}
                </div>
                <p className="text-xs text-muted-foreground">
                  {agentStatus?.available ? 'Agent ready for decisions' : 'Agent not available'}
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Decisions Today</CardTitle>
                <Activity className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-xl font-bold">
                  {agentStatus?.decisions_today?.toLocaleString() || '0'}
                </div>
                <p className="text-xs text-muted-foreground">
                  {agentStatus?.success_rate !== undefined 
                    ? `Success: ${agentStatus.success_rate.toFixed(1)}%`
                    : 'Routing optimizations'}
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">AI Predictions</CardTitle>
                <Brain className={`h-4 w-4 ${agentStatus?.ai_models?.initialized ? 'text-blue-500' : 'text-muted-foreground'}`} />
              </CardHeader>
              <CardContent>
                <div className="text-xl font-bold">
                  {agentStatus?.ai_predictions_used?.toLocaleString() || '0'}
                </div>
                <p className="text-xs text-muted-foreground">
                  {agentStatus?.ai_models?.initialized 
                    ? 'ML models active'
                    : 'AI models offline'}
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Avg Response</CardTitle>
                <Clock className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-xl font-bold">
                  {agentStatus?.avg_response_time_ms || 0}ms
                </div>
                <p className="text-xs text-muted-foreground">Decision latency</p>
              </CardContent>
            </Card>
          </div>

          {/* AI Models Status */}
          {agentStatus?.ai_models && (
            <Card className="border-blue-200 dark:border-blue-800">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Brain className="h-5 w-5 text-blue-500" />
                  AI Models Status
                  {agentStatus.ai_models.initialized && (
                    <Badge variant="outline" className="ml-2 border-green-500 text-green-500">
                      Active
                    </Badge>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent>
                {agentStatus.ai_models.available && agentStatus.ai_models.models ? (
                  <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                    {Object.entries(agentStatus.ai_models.models).map(([name, model]) => (
                      <div
                        key={name}
                        className="flex items-center justify-between p-3 rounded-lg bg-muted/50 border border-border/30"
                      >
                        <div className="flex-1">
                          <p className="text-sm font-medium capitalize">
                            {name.replace('_', ' ')}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {model.is_trained ? `v${model.version || '1.0'}` : 'Not trained'}
                          </p>
                        </div>
                        <Badge
                          variant={model.is_trained ? 'default' : 'secondary'}
                          className={model.is_trained ? 'bg-green-500/20 text-green-500 border-green-500/30' : ''}
                        >
                          {model.is_trained ? 'Trained' : 'Pending'}
                        </Badge>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-4">
                    <Brain className="h-8 w-8 mx-auto text-muted-foreground/30 mb-2" />
                    <p className="text-sm text-muted-foreground">
                      AI models not available
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <CardTitle>Recent Decisions</CardTitle>
            </CardHeader>
            <CardContent>
              {agentStatus?.recent_decisions && agentStatus.recent_decisions.length > 0 ? (
                <div className="space-y-3">
                  {agentStatus.recent_decisions.map((decision) => (
                    <div key={decision.id} className="flex items-center gap-3 p-3 rounded-lg bg-muted/50">
                      <CheckCircle className={`h-4 w-4 ${decision.status === 'success' ? 'text-green-500' : 'text-muted-foreground'}`} />
                      <div className="flex-1">
                        <p className="text-sm font-medium">Split route: {decision.route}</p>
                        <p className="text-xs text-muted-foreground">{decision.details}</p>
                      </div>
                      <span className="text-xs text-muted-foreground">
                        {formatTimeAgo(decision.timestamp)}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <Cpu className="h-12 w-12 mx-auto text-muted-foreground/30 mb-3" />
                  <p className="text-sm font-medium text-muted-foreground mb-1">No recent decisions</p>
                  <p className="text-xs text-muted-foreground">AI agent decisions will appear here</p>
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}