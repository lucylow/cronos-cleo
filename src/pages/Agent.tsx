import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Cpu, Activity, Clock, CheckCircle, Loader2, AlertCircle } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { api, ApiClientError } from '@/lib/api';

interface AgentStatus {
  status?: string;
  available?: boolean;
  decisions_today?: number;
  avg_response_time_ms?: number;
  recent_decisions?: Array<{
    id: string;
    timestamp: number;
    route: string;
    details: string;
    status: string;
  }>;
}

export default function Agent() {
  const [agentStatus, setAgentStatus] = useState<AgentStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const data = await api.getAgentStatus();
        setAgentStatus(data);
      } catch (error) {
        console.error('Failed to load agent status:', error);
      } finally {
        setLoading(false);
      }
    };

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
      <div>
        <h1 className="text-2xl font-bold text-foreground">AI Agent</h1>
        <p className="text-muted-foreground">Intelligent routing decisions powered by Crypto.com AI Agent SDK</p>
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
          <div className="grid gap-4 md:grid-cols-3">
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
                <p className="text-xs text-muted-foreground">Routing optimizations</p>
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
                <p className="text-sm text-muted-foreground">No recent decisions to display.</p>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
