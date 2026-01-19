import { useEffect, useState, useCallback, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { TrendingUp, Zap, PieChart, Activity, Loader2, AlertCircle, ArrowUpRight, ArrowDownRight, ArrowRight, Clock, RefreshCw, Info, Download, Network, Coins } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from '@/components/ui/tooltip';
import { api, ApiClientError } from '@/lib/api';
import { ConnectionStatus } from '@/components/ConnectionStatus';
import { getDashboardMetricsWebSocket, WebSocketState } from '@/lib/websocket';
import { motion, AnimatePresence } from 'framer-motion';
import { ChartContainer, ChartTooltip, ChartTooltipContent } from '@/components/ui/chart';
import { Line, AreaChart, Area, XAxis, YAxis, CartesianGrid } from 'recharts';
import { CronosNetworkStatus } from '@/components/CronosNetworkStatus';
import { useCronosBlockchain } from '@/hooks/useCronosBlockchain';
import { useBalance, useAccount } from 'wagmi';
import { formatUnits } from 'viem';

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
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [metricsHistory, setMetricsHistory] = useState<Array<{ timestamp: number; volume: number; executions: number; savings: number }>>([]);
  const [usingMockData, setUsingMockData] = useState(false);

  // Cronos blockchain data
  const { data: blockchainData, isConnected: isBlockchainConnected } = useCronosBlockchain({
    enabled: true,
    updateInterval: 5000,
    trackBlockTime: true,
  });

  // User CRO balance
  const { address } = useAccount();
  const { data: balanceData } = useBalance({
    address,
  });

  const fetchMetrics = useCallback(async (showRefreshing = false) => {
    try {
      setError(null);
      if (showRefreshing) {
        setIsRefreshing(true);
      } else {
        setLoading(true);
      }
      
      // Try to fetch from API - will automatically fallback to mock data on failure
      const data = await api.getDashboardMetrics();
      
      // Check if this is mock data by checking if backend is actually available
      // Do this check in parallel to avoid delaying the display
      api.health({ timeout: 2000, retries: 0 })
        .then(isAvailable => {
          setUsingMockData(!isAvailable || !data || Object.keys(data).length === 0);
        })
        .catch(() => {
          setUsingMockData(true);
        });
      
      setMetrics(data);
      setLastUpdate(new Date());
      
      // Add to history for chart (keep last 24 data points)
      if (data.total_volume_usd !== undefined && data.total_executions !== undefined && data.avg_savings_pct !== undefined) {
        setMetricsHistory(prev => {
          const newEntry = {
            timestamp: Date.now(),
            volume: data.total_volume_usd || 0,
            executions: data.total_executions || 0,
            savings: data.avg_savings_pct || 0
          };
          const updated = [...prev, newEntry].slice(-24);
          return updated;
        });
      }
    } catch (err) {
      // Even if there's an error, mock data should have been returned by the API client
      // But if it's still null, we have a problem
      const errorMessage = err instanceof ApiClientError 
        ? err.message 
        : 'Failed to load dashboard metrics';
      console.error('Failed to load dashboard metrics:', err);
      setError(errorMessage);
      setUsingMockData(true);
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchMetrics();
    // Refresh every 30 seconds
    const interval = setInterval(() => fetchMetrics(false), 30000);
    return () => clearInterval(interval);
  }, [fetchMetrics]);

  // Keyboard shortcut for refresh (R key)
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      if ((e.key === 'r' || e.key === 'R') && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        fetchMetrics(true);
      }
    };
    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [fetchMetrics]);

  // Export metrics as JSON
  const handleExport = useCallback(() => {
    if (!metrics) return;
    const dataStr = JSON.stringify(metrics, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `dashboard-metrics-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [metrics]);

  const formatCurrency = (value: number) => {
    if (value >= 1000000) {
      return `$${(value / 1000000).toFixed(2)}M`;
    }
    return `$${value.toLocaleString()}`;
  };

  const cardVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: (i: number) => ({
      opacity: 1,
      y: 0,
      transition: { delay: i * 0.1, duration: 0.4 }
    })
  };

  const chartData = useMemo(() => {
    return metricsHistory.map((entry, idx) => ({
      time: new Date(entry.timestamp).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
      volume: entry.volume,
      executions: entry.executions,
      savings: entry.savings,
      index: idx
    }));
  }, [metricsHistory]);

  const chartConfig = useMemo(() => ({
    volume: {
      label: 'Volume (USD)',
      color: 'hsl(var(--primary))',
    },
    executions: {
      label: 'Executions',
      color: 'hsl(var(--secondary))',
    },
    savings: {
      label: 'Avg Savings %',
      color: 'hsl(var(--accent))',
    },
  }), []);

  return (
    <TooltipProvider>
      <div className="space-y-6">
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4"
        >
          <div>
            <h1 className="text-3xl font-bold text-foreground mb-2">Dashboard</h1>
            <p className="text-muted-foreground text-lg">Cross-DEX Liquidity Execution Overview</p>
          </div>
          <div className="flex items-center gap-3">
            {lastUpdate && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <div className={`h-2 w-2 rounded-full ${isRefreshing ? 'animate-pulse bg-primary' : 'bg-green-500'}`} />
                    <span>Last updated: {lastUpdate.toLocaleTimeString()}</span>
                  </div>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Auto-refreshes every 30 seconds</p>
                  <p className="text-xs mt-1">Press Ctrl+R / Cmd+R to refresh</p>
                </TooltipContent>
              </Tooltip>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={() => fetchMetrics(true)}
              disabled={isRefreshing || loading}
              className="gap-2"
            >
              <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
            {metrics && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleExport}
                    className="gap-2"
                  >
                    <Download className="h-4 w-4" />
                    Export
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Export metrics as JSON</p>
                </TooltipContent>
              </Tooltip>
            )}
          </div>
        </motion.div>

      {/* Mock Data Indicator */}
      {usingMockData && !loading && metrics && (
        <Alert className="border-yellow-500/50 bg-yellow-500/10">
          <Info className="h-4 w-4 text-yellow-600 dark:text-yellow-500" />
          <AlertDescription className="flex items-center justify-between">
            <span className="text-sm">
              <strong>Demo Mode:</strong> Backend not connected. Showing simulated data. 
              Start the backend at <code className="text-xs bg-muted px-1 py-0.5 rounded mx-1">cleo_project/backend</code> for live blockchain data.
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => fetchMetrics(true)}
              className="ml-4"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry Connection
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {loading ? (
        <div className="space-y-6">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {[...Array(4)].map((_, i) => (
              <Card key={i}>
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-4 w-4 rounded" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-8 w-32 mb-2" />
                  <Skeleton className="h-3 w-20" />
                </CardContent>
              </Card>
            ))}
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            {[...Array(2)].map((_, i) => (
              <Card key={i}>
                <CardHeader>
                  <Skeleton className="h-6 w-32" />
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {[...Array(3)].map((_, j) => (
                      <Skeleton key={j} className="h-16 w-full" />
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      ) : error ? (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription className="flex items-center justify-between">
            <span>{error}</span>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setError(null);
                setLoading(true);
                fetchMetrics();
              }}
              className="ml-4"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry
            </Button>
          </AlertDescription>
        </Alert>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {/* Cronos Network Status Card */}
            {isBlockchainConnected && blockchainData && (
              <motion.div
                custom={0}
                initial="hidden"
                animate="visible"
                variants={cardVariants}
              >
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Card className="relative overflow-hidden border-border/50 hover:border-primary/30 transition-all duration-300 group cursor-pointer">
                      <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                      <CardHeader className="flex flex-row items-center justify-between pb-2 relative z-10">
                        <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1.5">
                          Cronos Network
                          <Info className="h-3 w-3 opacity-50" />
                        </CardTitle>
                        <div className="p-2 rounded-lg bg-primary/10 group-hover:bg-primary/20 transition-colors">
                          <Network className="h-4 w-4 text-primary" />
                        </div>
                      </CardHeader>
                      <CardContent className="relative z-10">
                        <div className="text-2xl font-bold mb-1">
                          Block #{blockchainData.currentBlock?.toLocaleString() || '0'}
                        </div>
                        <p className="text-xs text-muted-foreground flex items-center gap-1">
                          {blockchainData.blockTime ? (
                            <>
                              <Clock className="h-3 w-3" />
                              {blockchainData.blockTime.toFixed(1)}s avg
                            </>
                          ) : (
                            <>{blockchainData.networkName}</>
                          )}
                        </p>
                      </CardContent>
                    </Card>
                  </TooltipTrigger>
                  <TooltipContent side="top" className="max-w-xs">
                    <p className="font-semibold mb-1">Cronos Blockchain</p>
                    <p className="text-xs mb-1">Network: {blockchainData.networkName}</p>
                    <p className="text-xs mb-1">Current Block: {blockchainData.currentBlock?.toLocaleString()}</p>
                    {blockchainData.gasPriceGwei && (
                      <p className="text-xs">Gas Price: {parseFloat(blockchainData.gasPriceGwei).toFixed(2)} Gwei</p>
                    )}
                  </TooltipContent>
                </Tooltip>
              </motion.div>
            )}

            {/* CRO Balance Card */}
            {address && balanceData && isBlockchainConnected && (
              <motion.div
                custom={isBlockchainConnected && blockchainData ? 1 : 0}
                initial="hidden"
                animate="visible"
                variants={cardVariants}
              >
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Card className="relative overflow-hidden border-border/50 hover:border-accent/30 transition-all duration-300 group cursor-pointer">
                      <div className="absolute inset-0 bg-gradient-to-br from-accent/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                      <CardHeader className="flex flex-row items-center justify-between pb-2 relative z-10">
                        <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1.5">
                          Your Balance
                          <Info className="h-3 w-3 opacity-50" />
                        </CardTitle>
                        <div className="p-2 rounded-lg bg-accent/10 group-hover:bg-accent/20 transition-colors">
                          <Coins className="h-4 w-4 text-accent" />
                        </div>
                      </CardHeader>
                      <CardContent className="relative z-10">
                        <div className="text-2xl font-bold mb-1">
                          {parseFloat(formatUnits(balanceData.value, balanceData.decimals)).toFixed(4)} {balanceData.symbol}
                        </div>
                        <p className="text-xs text-muted-foreground">
                          {blockchainData?.networkName || 'Cronos'}
                        </p>
                      </CardContent>
                    </Card>
                  </TooltipTrigger>
                  <TooltipContent side="top" className="max-w-xs">
                    <p className="font-semibold mb-1">Wallet Balance</p>
                    <p className="text-xs">Your {balanceData.symbol} balance on Cronos network</p>
                  </TooltipContent>
                </Tooltip>
              </motion.div>
            )}

            <motion.div
              custom={isBlockchainConnected && blockchainData ? (address && balanceData ? 2 : 1) : 0}
              initial="hidden"
              animate="visible"
              variants={cardVariants}
            >
              <Tooltip>
                <TooltipTrigger asChild>
                  <Card className="relative overflow-hidden border-border/50 hover:border-primary/30 transition-all duration-300 group cursor-pointer">
                    <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                    <CardHeader className="flex flex-row items-center justify-between pb-2 relative z-10">
                      <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1.5">
                        Total Volume
                        <Info className="h-3 w-3 opacity-50" />
                      </CardTitle>
                      <div className="p-2 rounded-lg bg-primary/10 group-hover:bg-primary/20 transition-colors">
                        <TrendingUp className="h-4 w-4 text-primary" />
                      </div>
                    </CardHeader>
                    <CardContent className="relative z-10">
                      <div className="text-3xl font-bold mb-1 bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
                        {metrics?.total_volume_usd ? formatCurrency(metrics.total_volume_usd) : '$0'}
                      </div>
                      <p className="text-xs text-muted-foreground flex items-center gap-1">
                        <ArrowUpRight className="h-3 w-3 text-green-500" />
                        All-time volume
                      </p>
                    </CardContent>
                  </Card>
                </TooltipTrigger>
                <TooltipContent side="top" className="max-w-xs">
                  <p className="font-semibold mb-1">Total Volume (USD)</p>
                  <p className="text-xs">Cumulative trading volume across all DEX executions processed by the agent.</p>
                </TooltipContent>
              </Tooltip>
            </motion.div>

            <motion.div
              custom={1}
              initial="hidden"
              animate="visible"
              variants={cardVariants}
            >
              <Tooltip>
                <TooltipTrigger asChild>
                  <Card className="relative overflow-hidden border-border/50 hover:border-secondary/30 transition-all duration-300 group cursor-pointer">
                    <div className="absolute inset-0 bg-gradient-to-br from-secondary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                    <CardHeader className="flex flex-row items-center justify-between pb-2 relative z-10">
                      <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1.5">
                        Executions
                        <Info className="h-3 w-3 opacity-50" />
                      </CardTitle>
                      <div className="p-2 rounded-lg bg-secondary/10 group-hover:bg-secondary/20 transition-colors">
                        <Zap className="h-4 w-4 text-secondary" />
                      </div>
                    </CardHeader>
                    <CardContent className="relative z-10">
                      <div className="text-3xl font-bold mb-1">
                        {metrics?.total_executions?.toLocaleString() || '0'}
                      </div>
                      <p className="text-xs text-muted-foreground">Total successful swaps</p>
                    </CardContent>
                  </Card>
                </TooltipTrigger>
                <TooltipContent side="top" className="max-w-xs">
                  <p className="font-semibold mb-1">Total Executions</p>
                  <p className="text-xs">Number of successful multi-DEX swap executions completed by the routing agent.</p>
                </TooltipContent>
              </Tooltip>
            </motion.div>

            <motion.div
              custom={2}
              initial="hidden"
              animate="visible"
              variants={cardVariants}
            >
              <Tooltip>
                <TooltipTrigger asChild>
                  <Card className="relative overflow-hidden border-border/50 hover:border-accent/30 transition-all duration-300 group cursor-pointer">
                    <div className="absolute inset-0 bg-gradient-to-br from-accent/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                    <CardHeader className="flex flex-row items-center justify-between pb-2 relative z-10">
                      <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1.5">
                        Avg Savings
                        <Info className="h-3 w-3 opacity-50" />
                      </CardTitle>
                      <div className="p-2 rounded-lg bg-accent/10 group-hover:bg-accent/20 transition-colors">
                        <PieChart className="h-4 w-4 text-accent" />
                      </div>
                    </CardHeader>
                    <CardContent className="relative z-10">
                      <div className="text-3xl font-bold mb-1 text-green-500 flex items-center gap-2">
                        {metrics?.avg_savings_pct?.toFixed(1) || '0.0'}%
                        <ArrowUpRight className="h-5 w-5" />
                      </div>
                      <p className="text-xs text-muted-foreground">vs single-DEX routing</p>
                    </CardContent>
                  </Card>
                </TooltipTrigger>
                <TooltipContent side="top" className="max-w-xs">
                  <p className="font-semibold mb-1">Average Savings Percentage</p>
                  <p className="text-xs">Average cost savings achieved by multi-DEX routing compared to using a single DEX. This includes better prices and reduced slippage.</p>
                </TooltipContent>
              </Tooltip>
            </motion.div>

            <motion.div
              custom={3}
              initial="hidden"
              animate="visible"
              variants={cardVariants}
            >
              <Tooltip>
                <TooltipTrigger asChild>
                  <Card className="relative overflow-hidden border-border/50 transition-all duration-300 group cursor-pointer">
                    <div className={`absolute inset-0 bg-gradient-to-br ${metrics?.agent_status === 'active' ? 'from-green-500/5' : 'from-muted/5'} to-transparent opacity-0 group-hover:opacity-100 transition-opacity`} />
                    <CardHeader className="flex flex-row items-center justify-between pb-2 relative z-10">
                      <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1.5">
                        Agent Status
                        <Info className="h-3 w-3 opacity-50" />
                      </CardTitle>
                      <div className={`p-2 rounded-lg transition-colors ${metrics?.agent_status === 'active' ? 'bg-green-500/10 group-hover:bg-green-500/20' : 'bg-muted/20'}`}>
                        <Activity className={`h-4 w-4 ${metrics?.agent_status === 'active' ? 'text-green-500 animate-pulse' : 'text-muted-foreground'}`} />
                      </div>
                    </CardHeader>
                    <CardContent className="relative z-10">
                      <div className="flex items-center gap-2 mb-1">
                        <div className={`text-2xl font-bold ${metrics?.agent_status === 'active' ? 'text-green-500' : 'text-muted-foreground'}`}>
                          {metrics?.agent_status === 'active' ? 'Active' : 'Offline'}
                        </div>
                        {metrics?.agent_status === 'active' && (
                          <Badge variant="outline" className="border-green-500/30 text-green-500 text-xs px-2 py-0">
                            Live
                          </Badge>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground">AI routing status</p>
                    </CardContent>
                  </Card>
                </TooltipTrigger>
                <TooltipContent side="top" className="max-w-xs">
                  <p className="font-semibold mb-1">Agent Status</p>
                  <p className="text-xs">Current operational status of the AI routing agent. When active, the agent is monitoring liquidity and optimizing routes in real-time.</p>
                </TooltipContent>
              </Tooltip>
            </motion.div>
          </div>

          {/* Metrics Trend Chart */}
          {chartData.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5, duration: 0.4 }}
            >
              <Card className="border-border/50">
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-center gap-2">
                    <TrendingUp className="h-5 w-5 text-primary" />
                    Metrics Trends
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ChartContainer config={chartConfig} className="h-[300px] w-full">
                    <AreaChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
                      <defs>
                        <linearGradient id="colorVolume" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                          <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                        </linearGradient>
                        <linearGradient id="colorExecutions" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="hsl(var(--secondary))" stopOpacity={0.3} />
                          <stop offset="95%" stopColor="hsl(var(--secondary))" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--muted))" opacity={0.3} />
                      <XAxis 
                        dataKey="time" 
                        tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }}
                        tickLine={{ stroke: 'hsl(var(--muted-foreground))' }}
                      />
                      <YAxis 
                        yAxisId="left"
                        tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }}
                        tickLine={{ stroke: 'hsl(var(--muted-foreground))' }}
                      />
                      <YAxis 
                        yAxisId="right" 
                        orientation="right"
                        tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }}
                        tickLine={{ stroke: 'hsl(var(--muted-foreground))' }}
                      />
                      <ChartTooltip content={<ChartTooltipContent />} />
                      <Area
                        yAxisId="left"
                        type="monotone"
                        dataKey="volume"
                        stroke="hsl(var(--primary))"
                        fill="url(#colorVolume)"
                        strokeWidth={2}
                        name="Volume (USD)"
                      />
                      <Area
                        yAxisId="left"
                        type="monotone"
                        dataKey="executions"
                        stroke="hsl(var(--secondary))"
                        fill="url(#colorExecutions)"
                        strokeWidth={2}
                        name="Executions"
                      />
                      <Line
                        yAxisId="right"
                        type="monotone"
                        dataKey="savings"
                        stroke="hsl(var(--accent))"
                        strokeWidth={2}
                        dot={false}
                        name="Avg Savings %"
                      />
                    </AreaChart>
                  </ChartContainer>
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* Cronos Network Status Section */}
          {isBlockchainConnected && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3, duration: 0.4 }}
            >
              <CronosNetworkStatus />
            </motion.div>
          )}

          <div className="grid gap-4 md:grid-cols-2">
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.4, duration: 0.4 }}
            >
              <Card className="border-border/50">
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-center gap-2">
                    <Activity className="h-5 w-5 text-primary" />
                    Recent Executions
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {metrics?.recent_executions && metrics.recent_executions.length > 0 ? (
                    <div className="space-y-3">
                      <AnimatePresence>
                        {metrics.recent_executions.slice(0, 5).map((exec, idx) => (
                          <motion.div
                            key={exec.id}
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: 10 }}
                            transition={{ delay: 0.5 + idx * 0.05 }}
                            className="flex items-center justify-between p-3 rounded-lg bg-muted/30 hover:bg-muted/50 border border-border/30 transition-all group"
                          >
                          <div className="flex items-center gap-3">
                            <div className="p-2 rounded-lg bg-primary/10 group-hover:bg-primary/20 transition-colors">
                              <Zap className="h-3.5 w-3.5 text-primary" />
                            </div>
                            <div>
                              <p className="text-sm font-medium flex items-center gap-2">
                                <span>{exec.amount_in.toLocaleString()} {exec.token_in}</span>
                                <ArrowRight className="h-3 w-3 text-muted-foreground" />
                                <span>{exec.token_out}</span>
                              </p>
                              <p className="text-xs text-muted-foreground flex items-center gap-1 mt-0.5">
                                <Clock className="h-3 w-3" />
                                {new Date(exec.timestamp * 1000).toLocaleString()}
                              </p>
                            </div>
                          </div>
                          <div className="text-right">
                            <Badge variant="outline" className="border-green-500/30 text-green-500 mb-1">
                              +{exec.savings_pct.toFixed(2)}%
                            </Badge>
                            <p className="text-xs text-muted-foreground capitalize">{exec.status}</p>
                          </div>
                        </motion.div>
                        ))}
                      </AnimatePresence>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center py-8 text-center">
                      <Activity className="h-12 w-12 text-muted-foreground/30 mb-3" />
                      <p className="text-sm text-muted-foreground">No recent executions to display.</p>
                      <p className="text-xs text-muted-foreground/70 mt-1">Start trading to see your execution history</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.4, duration: 0.4 }}
            >
              <Card className="border-border/50">
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-center gap-2">
                    <PieChart className="h-5 w-5 text-secondary" />
                    Agent Health
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between p-3 rounded-lg bg-muted/30 border border-border/30">
                      <span className="text-sm font-medium text-muted-foreground">Status</span>
                      <Badge 
                        variant={metrics?.agent_status === 'active' ? 'default' : 'secondary'}
                        className={metrics?.agent_status === 'active' ? 'bg-green-500/20 text-green-500 border-green-500/30' : ''}
                      >
                        {metrics?.agent_status === 'active' ? 'Operational' : 'Offline'}
                      </Badge>
                    </div>
                    {metrics?.success_rate !== undefined && (
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium text-muted-foreground">Success Rate</span>
                          <span className="text-lg font-bold text-foreground">{metrics.success_rate.toFixed(1)}%</span>
                        </div>
                        <div className="h-2 bg-muted rounded-full overflow-hidden">
                          <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${metrics.success_rate}%` }}
                            transition={{ delay: 0.6, duration: 0.8, ease: "easeOut" }}
                            className="h-full bg-gradient-to-r from-green-500 to-green-400 rounded-full"
                          />
                        </div>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          </div>
        </>
      )}
      </div>
    </TooltipProvider>
  );
}
