import { useEffect, useState, useCallback, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { TrendingUp, Zap, PieChart, Activity, Loader2, AlertCircle, ArrowUpRight, ArrowDownRight, ArrowRight, Clock, RefreshCw, Info, Download, Network, Coins, DollarSign, TrendingDown, Wallet, BarChart3, FileSpreadsheet } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from '@/components/ui/tooltip';
import { api, ApiClientError } from '@/lib/api';
import { ConnectionStatus } from '@/components/ConnectionStatus';
import { getDashboardMetricsWebSocket, WebSocketState, WebSocketMessage } from '@/lib/websocket';
import { motion, AnimatePresence } from 'framer-motion';
import { ChartContainer, ChartTooltip, ChartTooltipContent } from '@/components/ui/chart';
import { Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, PieChart as RechartsPieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import { CronosNetworkStatus } from '@/components/CronosNetworkStatus';
import { useCronosBlockchain } from '@/hooks/useCronosBlockchain';
import { useBalance, useAccount } from 'wagmi';
import { formatUnits } from 'viem';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

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
    gas_cost_usd?: number;
    protocol_fee_usd?: number;
    profit_usd?: number;
    dex_distribution?: Record<string, number>;
  }>;
  financial_summary?: {
    total_profit_usd?: number;
    total_costs_usd?: number;
    total_gas_costs_usd?: number;
    total_protocol_fees_usd?: number;
    roi_pct?: number;
    avg_profit_per_execution?: number;
  };
  dex_distribution?: Record<string, { volume: number; count: number; percentage: number }>;
}

export default function Dashboard() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [metricsHistory, setMetricsHistory] = useState<Array<{ timestamp: number; volume: number; executions: number; savings: number; profit: number; costs: number }>>([]);
  const [usingMockData, setUsingMockData] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');

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
      let data: DashboardMetrics | null = null;
      try {
        data = await api.getDashboardMetrics();
        
        // Validate data structure
        if (!data || typeof data !== 'object') {
          throw new Error('Invalid response data format');
        }
      } catch (fetchErr) {
        console.error('API fetch error:', fetchErr);
        // If API client didn't provide fallback mock data, use empty metrics
        data = {
          total_volume_usd: 0,
          total_executions: 0,
          avg_savings_pct: 0,
          agent_status: 'offline',
          success_rate: 0,
          recent_executions: [],
        };
      }
      
      // Check if this is mock data by checking if backend is actually available
      // Do this check in parallel to avoid delaying the display
      api.health({ timeout: 2000, retries: 0 })
        .then(isAvailable => {
          setUsingMockData(!isAvailable || !data || Object.keys(data).length === 0);
        })
        .catch((healthErr) => {
          console.warn('Health check failed:', healthErr);
          setUsingMockData(true);
        });
      
      setMetrics(data);
      setLastUpdate(new Date());
      
      // Add to history for chart (keep last 24 data points)
      try {
        if (data && 
            typeof data.total_volume_usd === 'number' && 
            typeof data.total_executions === 'number' && 
            typeof data.avg_savings_pct === 'number' &&
            !isNaN(data.total_volume_usd) &&
            !isNaN(data.total_executions) &&
            !isNaN(data.avg_savings_pct)) {
        setMetricsHistory(prev => {
            try {
              const financialSummary = data?.financial_summary || {};
          const newEntry = {
            timestamp: Date.now(),
            volume: data.total_volume_usd || 0,
            executions: data.total_executions || 0,
            savings: data.avg_savings_pct || 0,
                profit: typeof financialSummary.total_profit_usd === 'number' && !isNaN(financialSummary.total_profit_usd) 
                  ? financialSummary.total_profit_usd 
                  : 0,
                costs: typeof financialSummary.total_costs_usd === 'number' && !isNaN(financialSummary.total_costs_usd)
                  ? financialSummary.total_costs_usd
                  : 0
          };
          const updated = [...prev, newEntry].slice(-24);
          return updated;
            } catch (historyErr) {
              console.error('Error updating metrics history:', historyErr);
              return prev;
            }
        });
        }
      } catch (historyErr) {
        console.error('Error processing metrics history:', historyErr);
      }
    } catch (err) {
      // Comprehensive error handling
      let errorMessage = 'Failed to load dashboard metrics';
      
      if (err instanceof ApiClientError) {
        errorMessage = err.message || errorMessage;
        if (err.status === 404) {
          errorMessage = 'Dashboard metrics endpoint not found';
        } else if (err.status === 500) {
          errorMessage = 'Server error while loading metrics';
        } else if (err.status === 503) {
          errorMessage = 'Service temporarily unavailable';
        } else if (err.status) {
          errorMessage = `Error ${err.status}: ${err.message}`;
        }
      } else if (err instanceof Error) {
        errorMessage = err.message || errorMessage;
      } else if (typeof err === 'string') {
        errorMessage = err;
      }
      
      console.error('Failed to load dashboard metrics:', err);
      setError(errorMessage);
      setUsingMockData(true);
      
      // Set minimal metrics structure to prevent rendering errors
      setMetrics({
        total_volume_usd: 0,
        total_executions: 0,
        avg_savings_pct: 0,
        agent_status: 'offline',
        success_rate: 0,
        recent_executions: [],
      });
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

  // WebSocket connection for real-time updates
  useEffect(() => {
    let wsManager: ReturnType<typeof getDashboardMetricsWebSocket> | null = null;

    try {
      wsManager = getDashboardMetricsWebSocket();
      
      const handleOpen = () => {
        try {
        setWsConnected(true);
        } catch (err) {
          console.error('Error handling WebSocket open:', err);
        }
      };

      const handleClose = () => {
        try {
          setWsConnected(false);
        } catch (err) {
          console.error('Error handling WebSocket close:', err);
        }
      };

      const handleError = (error: Error | Event) => {
        console.error('WebSocket error:', error);
        setWsConnected(false);
      };

      const handleMessage = (message: WebSocketMessage) => {
        try {
          if (!message || typeof message !== 'object') {
            console.warn('Invalid WebSocket message format:', message);
            return;
          }

        if (message.type === 'metrics_update' && message.data) {
            try {
              const data = message.data as DashboardMetrics;
              
              // Validate data structure
              if (!data || typeof data !== 'object') {
                console.warn('Invalid metrics data in WebSocket message');
                return;
              }

              setMetrics(data);
          setLastUpdate(new Date());
          
              // Add to history with validation
              if (typeof data.total_volume_usd === 'number' && 
                  typeof data.total_executions === 'number' && 
                  typeof data.avg_savings_pct === 'number' &&
                  !isNaN(data.total_volume_usd) &&
                  !isNaN(data.total_executions) &&
                  !isNaN(data.avg_savings_pct)) {
            setMetricsHistory(prev => {
                  try {
              const financialSummary = data.financial_summary || {};
              const newEntry = {
                timestamp: Date.now(),
                volume: data.total_volume_usd || 0,
                executions: data.total_executions || 0,
                savings: data.avg_savings_pct || 0,
                      profit: typeof financialSummary.total_profit_usd === 'number' && !isNaN(financialSummary.total_profit_usd)
                        ? financialSummary.total_profit_usd
                        : 0,
                      costs: typeof financialSummary.total_costs_usd === 'number' && !isNaN(financialSummary.total_costs_usd)
                        ? financialSummary.total_costs_usd
                        : 0
              };
              return [...prev, newEntry].slice(-24);
                  } catch (historyErr) {
                    console.error('Error updating history from WebSocket:', historyErr);
                    return prev;
                  }
                });
              }
            } catch (dataErr) {
              console.error('Error processing WebSocket metrics data:', dataErr);
            }
          }
        } catch (messageErr) {
          console.error('Error handling WebSocket message:', messageErr);
        }
      };

      const handleStateChange = (state: { state: WebSocketState }) => {
        try {
          if (state && typeof state.state === 'number') {
        setWsConnected(state.state === WebSocketState.CONNECTED);
          }
        } catch (err) {
          console.error('Error handling WebSocket state change:', err);
        }
      };

      wsManager.on('open', handleOpen);
      wsManager.on('close', handleClose);
      wsManager.on('error', handleError);
      wsManager.on('message', handleMessage);
      wsManager.on('statechange', handleStateChange);

      // Connect if not already connected
      try {
      if (wsManager.getState() === WebSocketState.DISCONNECTED) {
        wsManager.connect();
      } else {
        setWsConnected(wsManager.isConnected());
        }
      } catch (connectErr) {
        console.error('Error connecting WebSocket:', connectErr);
        setWsConnected(false);
      }

      return () => {
        try {
        if (wsManager) {
          wsManager.off('open', handleOpen);
          wsManager.off('close', handleClose);
            wsManager.off('error', handleError);
          wsManager.off('message', handleMessage);
          wsManager.off('statechange', handleStateChange);
          // Don't disconnect, let it stay connected for other components
          }
        } catch (cleanupErr) {
          console.error('Error cleaning up WebSocket:', cleanupErr);
        }
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error('WebSocket setup failed:', errorMessage, error);
      setWsConnected(false);
    }
  }, []);

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

  // Calculate financial metrics
  const financialMetrics = useMemo(() => {
    try {
    const summary = metrics?.financial_summary || {};
      
      // Safely extract and validate numeric values
      const totalVolume = typeof metrics?.total_volume_usd === 'number' && !isNaN(metrics.total_volume_usd)
        ? Math.max(0, metrics.total_volume_usd)
        : 0;
      const totalExecutions = typeof metrics?.total_executions === 'number' && !isNaN(metrics.total_executions)
        ? Math.max(0, metrics.total_executions)
        : 0;
      
      const totalGas = typeof summary.total_gas_costs_usd === 'number' && !isNaN(summary.total_gas_costs_usd)
        ? Math.max(0, summary.total_gas_costs_usd)
        : 0;
      const totalFees = typeof summary.total_protocol_fees_usd === 'number' && !isNaN(summary.total_protocol_fees_usd)
        ? Math.max(0, summary.total_protocol_fees_usd)
        : 0;
      
      const totalCostsFromSummary = typeof summary.total_costs_usd === 'number' && !isNaN(summary.total_costs_usd)
        ? Math.max(0, summary.total_costs_usd)
        : null;
      
      const totalCosts = totalCostsFromSummary !== null ? totalCostsFromSummary : (totalGas + totalFees);
      const totalProfit = typeof summary.total_profit_usd === 'number' && !isNaN(summary.total_profit_usd)
        ? summary.total_profit_usd
        : 0;
      
    const netProfit = totalProfit - totalCosts;
      
      // Safe division with validation
      const roi = totalVolume > 0 && isFinite(totalVolume) && isFinite(netProfit)
        ? ((netProfit / totalVolume) * 100)
        : 0;
      
      const avgProfitPerExecution = totalExecutions > 0 && isFinite(totalExecutions) && isFinite(netProfit)
        ? (netProfit / totalExecutions)
        : 0;
      
      const avgCostPerExecution = totalExecutions > 0 && isFinite(totalExecutions) && isFinite(totalCosts)
        ? (totalCosts / totalExecutions)
        : 0;

    return {
      totalProfit,
      totalCosts,
      totalGas,
      totalFees,
      netProfit,
        roi: isFinite(roi) ? roi : 0,
        avgProfitPerExecution: isFinite(avgProfitPerExecution) ? avgProfitPerExecution : 0,
        avgCostPerExecution: isFinite(avgCostPerExecution) ? avgCostPerExecution : 0,
      };
    } catch (err) {
      console.error('Error calculating financial metrics:', err);
      // Return safe defaults
      return {
        totalProfit: 0,
        totalCosts: 0,
        totalGas: 0,
        totalFees: 0,
        netProfit: 0,
        roi: 0,
        avgProfitPerExecution: 0,
        avgCostPerExecution: 0,
      };
    }
  }, [metrics]);

  // DEX distribution data for pie chart
  const dexDistributionData = useMemo(() => {
    try {
    if (!metrics?.dex_distribution) {
      // Generate mock distribution from recent executions if not available
      const mockDexes: Record<string, number> = {};
        try {
      metrics?.recent_executions?.forEach(exec => {
            if (exec && exec.dex_distribution && typeof exec.dex_distribution === 'object') {
          Object.entries(exec.dex_distribution).forEach(([dex, amount]) => {
                if (typeof amount === 'number' && !isNaN(amount) && isFinite(amount)) {
                  mockDexes[dex] = (mockDexes[dex] || 0) + Math.max(0, amount);
                }
          });
        }
      });
        } catch (mockErr) {
          console.error('Error generating mock DEX distribution:', mockErr);
        }
        
      if (Object.keys(mockDexes).length === 0) {
        return [
          { name: 'VVS Finance', value: 45, color: 'hsl(var(--primary))', volume: 0 },
          { name: 'CronaSwap', value: 30, color: 'hsl(var(--secondary))', volume: 0 },
          { name: 'MM Finance', value: 25, color: 'hsl(var(--accent))', volume: 0 },
        ];
      }
        
        try {
      const total = Object.values(mockDexes).reduce((a, b) => a + b, 0);
          if (total <= 0 || !isFinite(total)) {
            return [
              { name: 'VVS Finance', value: 45, color: 'hsl(var(--primary))', volume: 0 },
              { name: 'CronaSwap', value: 30, color: 'hsl(var(--secondary))', volume: 0 },
              { name: 'MM Finance', value: 25, color: 'hsl(var(--accent))', volume: 0 },
            ];
          }
          
          return Object.entries(mockDexes).map(([name, value]) => {
            const percentage = (value / total) * 100;
            return {
              name: name || 'Unknown',
              value: isFinite(percentage) ? percentage : 0,
        volume: value,
        color: name.includes('VVS') ? 'hsl(var(--primary))' : name.includes('Crona') ? 'hsl(var(--secondary))' : 'hsl(var(--accent))',
            };
          });
        } catch (calcErr) {
          console.error('Error calculating mock DEX distribution:', calcErr);
          return [
            { name: 'VVS Finance', value: 45, color: 'hsl(var(--primary))', volume: 0 },
            { name: 'CronaSwap', value: 30, color: 'hsl(var(--secondary))', volume: 0 },
            { name: 'MM Finance', value: 25, color: 'hsl(var(--accent))', volume: 0 },
          ];
        }
      }
      
      try {
        return Object.entries(metrics.dex_distribution).map(([dex, data]) => {
          const percentage = typeof data === 'object' && data !== null && typeof data.percentage === 'number'
            ? (isFinite(data.percentage) ? Math.max(0, data.percentage) : 0)
            : 0;
          const volume = typeof data === 'object' && data !== null && typeof data.volume === 'number'
            ? (isFinite(data.volume) ? Math.max(0, data.volume) : 0)
            : 0;
          
          return {
            name: dex || 'Unknown',
            value: percentage,
            volume,
            count: typeof data === 'object' && data !== null && typeof data.count === 'number' ? data.count : 0,
      color: dex.includes('VVS') ? 'hsl(var(--primary))' : dex.includes('Crona') ? 'hsl(var(--secondary))' : 'hsl(var(--accent))',
          };
        }).filter(item => item.value > 0 || item.volume > 0); // Filter out invalid entries
      } catch (distributionErr) {
        console.error('Error processing DEX distribution:', distributionErr);
        return [
          { name: 'VVS Finance', value: 45, color: 'hsl(var(--primary))', volume: 0 },
          { name: 'CronaSwap', value: 30, color: 'hsl(var(--secondary))', volume: 0 },
          { name: 'MM Finance', value: 25, color: 'hsl(var(--accent))', volume: 0 },
        ];
      }
    } catch (err) {
      console.error('Error calculating DEX distribution data:', err);
      return [
        { name: 'VVS Finance', value: 45, color: 'hsl(var(--primary))', volume: 0 },
        { name: 'CronaSwap', value: 30, color: 'hsl(var(--secondary))', volume: 0 },
        { name: 'MM Finance', value: 25, color: 'hsl(var(--accent))', volume: 0 },
      ];
    }
  }, [metrics]);

  // Export metrics as JSON
  const handleExport = useCallback(() => {
    try {
      if (!metrics) {
        console.warn('No metrics to export');
        setError('No data available to export');
        return;
      }

      let dataStr: string;
      try {
        dataStr = JSON.stringify(metrics, null, 2);
      } catch (stringifyErr) {
        console.error('Error stringifying metrics:', stringifyErr);
        setError('Failed to format data for export');
        return;
      }

      let dataBlob: Blob;
      try {
        dataBlob = new Blob([dataStr], { type: 'application/json' });
      } catch (blobErr) {
        console.error('Error creating blob:', blobErr);
        setError('Failed to create export file');
        return;
      }

      let url: string;
      try {
        url = URL.createObjectURL(dataBlob);
      } catch (urlErr) {
        console.error('Error creating object URL:', urlErr);
        setError('Failed to generate download link');
        return;
      }

      try {
    const link = document.createElement('a');
    link.href = url;
        
        try {
          const dateStr = new Date().toISOString().split('T')[0];
          link.download = `dashboard-metrics-${dateStr}.json`;
        } catch (dateErr) {
          console.warn('Error formatting date for filename:', dateErr);
          link.download = `dashboard-metrics-${Date.now()}.json`;
        }
        
    document.body.appendChild(link);
    link.click();
        
        // Cleanup with error handling
        setTimeout(() => {
          try {
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
          } catch (cleanupErr) {
            console.error('Error cleaning up export:', cleanupErr);
          }
        }, 100);
      } catch (downloadErr) {
        console.error('Error triggering download:', downloadErr);
        URL.revokeObjectURL(url);
        setError('Failed to initiate download');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error during export';
      console.error('Export error:', errorMessage, err);
      setError(`Export failed: ${errorMessage}`);
    }
  }, [metrics]);

  // Export financial data as CSV
  const handleExportCSV = useCallback(() => {
    try {
      if (!metrics?.recent_executions || !Array.isArray(metrics.recent_executions) || metrics.recent_executions.length === 0) {
        console.warn('No execution data to export');
        setError('No execution data available to export');
        return;
      }
    
    const headers = ['Date', 'Token In', 'Token Out', 'Amount In', 'Amount Out', 'Savings %', 'Gas Cost (USD)', 'Protocol Fee (USD)', 'Profit (USD)', 'Status'];
      
      const rows = metrics.recent_executions.map((exec, index) => {
        try {
          // Validate execution data
          if (!exec || typeof exec !== 'object') {
            console.warn(`Invalid execution data at index ${index}`);
            return null;
          }

          // Safe date formatting
          let dateStr: string;
          try {
            if (typeof exec.timestamp === 'number' && !isNaN(exec.timestamp) && isFinite(exec.timestamp)) {
              const date = new Date(exec.timestamp * 1000);
              if (!isNaN(date.getTime())) {
                dateStr = date.toLocaleString();
              } else {
                dateStr = 'Invalid Date';
              }
            } else {
              dateStr = 'Unknown';
            }
          } catch (dateErr) {
            console.warn('Error formatting date:', dateErr);
            dateStr = 'Unknown';
          }

          // Safe number formatting
          const formatNumber = (value: any, decimals: number = 2): string => {
            if (typeof value === 'number' && !isNaN(value) && isFinite(value)) {
              return value.toFixed(decimals);
            }
            return '0.00';
          };

          const formatLargeNumber = (value: any): string => {
            if (typeof value === 'number' && !isNaN(value) && isFinite(value)) {
              return value.toLocaleString();
            }
            return '0';
          };

          return [
            dateStr,
            exec.token_in || 'Unknown',
            exec.token_out || 'Unknown',
            formatLargeNumber(exec.amount_in),
            formatLargeNumber(exec.amount_out),
            formatNumber(exec.savings_pct || 0),
            formatNumber(exec.gas_cost_usd || 0),
            formatNumber(exec.protocol_fee_usd || 0),
            formatNumber(exec.profit_usd || 0),
            exec.status || 'Unknown',
          ];
        } catch (rowErr) {
          console.error(`Error processing execution at index ${index}:`, rowErr);
          return null;
        }
      }).filter((row): row is string[] => row !== null); // Filter out null rows

      if (rows.length === 0) {
        setError('No valid execution data to export');
        return;
      }

      // Escape CSV values and join
      const escapeCSV = (value: string): string => {
        if (typeof value !== 'string') {
          value = String(value);
        }
        // Escape quotes and wrap in quotes if contains comma, quote, or newline
        if (value.includes(',') || value.includes('"') || value.includes('\n')) {
          return `"${value.replace(/"/g, '""')}"`;
        }
        return value;
      };

      let csvContent: string;
      try {
        csvContent = [
          headers.map(escapeCSV).join(','),
          ...rows.map(row => row.map(escapeCSV).join(','))
    ].join('\n');
      } catch (csvErr) {
        console.error('Error generating CSV content:', csvErr);
        setError('Failed to format CSV data');
        return;
      }

      let dataBlob: Blob;
      try {
        dataBlob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      } catch (blobErr) {
        console.error('Error creating CSV blob:', blobErr);
        setError('Failed to create CSV file');
        return;
      }

      let url: string;
      try {
        url = URL.createObjectURL(dataBlob);
      } catch (urlErr) {
        console.error('Error creating object URL:', urlErr);
        setError('Failed to generate download link');
        return;
      }

      try {
    const link = document.createElement('a');
    link.href = url;
        
        try {
          const dateStr = new Date().toISOString().split('T')[0];
          link.download = `financial-report-${dateStr}.csv`;
        } catch (dateErr) {
          console.warn('Error formatting date for filename:', dateErr);
          link.download = `financial-report-${Date.now()}.csv`;
        }
        
    document.body.appendChild(link);
    link.click();
        
        // Cleanup with error handling
        setTimeout(() => {
          try {
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
          } catch (cleanupErr) {
            console.error('Error cleaning up CSV export:', cleanupErr);
          }
        }, 100);
      } catch (downloadErr) {
        console.error('Error triggering CSV download:', downloadErr);
        URL.revokeObjectURL(url);
        setError('Failed to initiate download');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error during CSV export';
      console.error('CSV export error:', errorMessage, err);
      setError(`CSV export failed: ${errorMessage}`);
    }
  }, [metrics]);

  const formatCurrency = useCallback((value: number | undefined | null): string => {
    try {
      // Handle invalid inputs
      if (value === null || value === undefined || typeof value !== 'number' || isNaN(value) || !isFinite(value)) {
        return '$0.00';
      }

      // Handle negative values
      const absValue = Math.abs(value);
      const sign = value < 0 ? '-' : '';

      if (absValue >= 1000000) {
        return `${sign}$${(absValue / 1000000).toFixed(2)}M`;
      }
      return `${sign}$${absValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    } catch (err) {
      console.error('Error formatting currency:', err);
      return '$0.00';
    }
  }, []);

  const cardVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: (i: number) => ({
      opacity: 1,
      y: 0,
      transition: { delay: i * 0.1, duration: 0.4 }
    })
  };

  const chartData = useMemo(() => {
    try {
      if (!Array.isArray(metricsHistory)) {
        return [];
      }

      return metricsHistory
        .map((entry, idx) => {
          try {
            if (!entry || typeof entry !== 'object') {
              return null;
            }

            // Validate timestamp
            const timestamp = typeof entry.timestamp === 'number' && !isNaN(entry.timestamp) && isFinite(entry.timestamp)
              ? entry.timestamp
              : Date.now();

            let timeStr: string;
            try {
              const date = new Date(timestamp);
              if (!isNaN(date.getTime())) {
                timeStr = date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
              } else {
                timeStr = 'Invalid';
              }
            } catch (dateErr) {
              console.warn('Error formatting chart time:', dateErr);
              timeStr = 'Invalid';
            }

            // Validate numeric values
            const volume = typeof entry.volume === 'number' && !isNaN(entry.volume) && isFinite(entry.volume)
              ? Math.max(0, entry.volume)
              : 0;
            const executions = typeof entry.executions === 'number' && !isNaN(entry.executions) && isFinite(entry.executions)
              ? Math.max(0, entry.executions)
              : 0;
            const savings = typeof entry.savings === 'number' && !isNaN(entry.savings) && isFinite(entry.savings)
              ? entry.savings
              : 0;
            const profit = typeof entry.profit === 'number' && !isNaN(entry.profit) && isFinite(entry.profit)
              ? entry.profit
              : 0;
            const costs = typeof entry.costs === 'number' && !isNaN(entry.costs) && isFinite(entry.costs)
              ? Math.max(0, entry.costs)
              : 0;
            const netProfit = profit - costs;

            return {
              time: timeStr,
              volume,
              executions,
              savings,
              profit,
              costs,
              netProfit: isFinite(netProfit) ? netProfit : 0,
      index: idx
            };
          } catch (entryErr) {
            console.error(`Error processing chart entry at index ${idx}:`, entryErr);
            return null;
          }
        })
        .filter((item): item is NonNullable<typeof item> => item !== null);
    } catch (err) {
      console.error('Error generating chart data:', err);
      return [];
    }
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
    profit: {
      label: 'Profit (USD)',
      color: 'hsl(142, 76%, 36%)',
    },
    costs: {
      label: 'Costs (USD)',
      color: 'hsl(0, 84%, 60%)',
    },
    netProfit: {
      label: 'Net Profit (USD)',
      color: 'hsl(142, 76%, 36%)',
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
            <ConnectionStatus showLabel={false} size="sm" />
            {lastUpdate && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <div className={`h-2 w-2 rounded-full ${isRefreshing ? 'animate-pulse bg-primary' : wsConnected ? 'bg-green-500' : 'bg-blue-500'}`} />
                    <span>Last updated: {lastUpdate.toLocaleTimeString()}</span>
                  </div>
                </TooltipTrigger>
                <TooltipContent>
                  <p>{wsConnected ? 'Real-time updates via WebSocket' : 'Auto-refreshes every 30 seconds'}</p>
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
              <>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleExportCSV}
                      className="gap-2"
                    >
                      <FileSpreadsheet className="h-4 w-4" />
                      CSV
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Export financial data as CSV</p>
                  </TooltipContent>
                </Tooltip>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleExport}
                      className="gap-2"
                    >
                      <Download className="h-4 w-4" />
                      JSON
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Export metrics as JSON</p>
                  </TooltipContent>
                </Tooltip>
              </>
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
          <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
            <TabsList className="grid w-full max-w-md grid-cols-2">
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="financials">Financials</TabsTrigger>
            </TabsList>

            <TabsContent value="overview" className="space-y-6">
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
                          Block #{(() => {
                            try {
                              const block = blockchainData.currentBlock;
                              if (typeof block === 'number' && !isNaN(block) && isFinite(block)) {
                                return block.toLocaleString();
                              }
                              return '0';
                            } catch {
                              return '0';
                            }
                          })()}
                        </div>
                        <p className="text-xs text-muted-foreground flex items-center gap-1">
                          {(() => {
                            try {
                              const blockTime = blockchainData.blockTime;
                              if (typeof blockTime === 'number' && !isNaN(blockTime) && isFinite(blockTime) && blockTime > 0) {
                                return (
                            <>
                              <Clock className="h-3 w-3" />
                                    {blockTime.toFixed(1)}s avg
                                  </>
                                );
                              }
                              return <>{blockchainData.networkName || 'Cronos'}</>;
                            } catch {
                              return <>{blockchainData.networkName || 'Cronos'}</>;
                            }
                          })()}
                        </p>
                      </CardContent>
                    </Card>
                  </TooltipTrigger>
                  <TooltipContent side="top" className="max-w-xs">
                    <p className="font-semibold mb-1">Cronos Blockchain</p>
                    <p className="text-xs mb-1">Network: {blockchainData.networkName || 'Unknown'}</p>
                    <p className="text-xs mb-1">
                      Current Block: {(() => {
                        try {
                          const block = blockchainData.currentBlock;
                          if (typeof block === 'number' && !isNaN(block) && isFinite(block)) {
                            return block.toLocaleString();
                          }
                          return '0';
                        } catch {
                          return '0';
                        }
                      })()}
                    </p>
                    {(() => {
                      try {
                        const gasPrice = blockchainData.gasPriceGwei;
                        if (gasPrice && typeof gasPrice === 'string') {
                          const parsed = parseFloat(gasPrice);
                          if (!isNaN(parsed) && isFinite(parsed) && parsed > 0) {
                            return <p className="text-xs">Gas Price: {parsed.toFixed(2)} Gwei</p>;
                          }
                        }
                        return null;
                      } catch {
                        return null;
                      }
                    })()}
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
                          {(() => {
                            try {
                              if (balanceData && typeof balanceData.value === 'bigint' && typeof balanceData.decimals === 'number') {
                                const formatted = parseFloat(formatUnits(balanceData.value, balanceData.decimals));
                                if (!isNaN(formatted) && isFinite(formatted)) {
                                  return `${formatted.toFixed(4)} ${balanceData.symbol || 'CRO'}`;
                                }
                              }
                              return '0.0000 CRO';
                            } catch {
                              return '0.0000 CRO';
                            }
                          })()}
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
                        {(() => {
                          try {
                            const executions = metrics?.total_executions;
                            if (typeof executions === 'number' && !isNaN(executions) && isFinite(executions)) {
                              return executions.toLocaleString();
                            }
                            return '0';
                          } catch {
                            return '0';
                          }
                        })()}
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
                        {(() => {
                          try {
                            const savings = metrics?.avg_savings_pct;
                            if (typeof savings === 'number' && !isNaN(savings) && isFinite(savings)) {
                              return `${savings.toFixed(1)}%`;
                            }
                            return '0.0%';
                          } catch {
                            return '0.0%';
                          }
                        })()}
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
                                <span>
                                  {(() => {
                                    try {
                                      const amount = typeof exec.amount_in === 'number' && !isNaN(exec.amount_in) && isFinite(exec.amount_in)
                                        ? exec.amount_in.toLocaleString()
                                        : '0';
                                      return `${amount} ${exec.token_in || 'Unknown'}`;
                                    } catch {
                                      return `0 ${exec.token_in || 'Unknown'}`;
                                    }
                                  })()}
                                </span>
                                <ArrowRight className="h-3 w-3 text-muted-foreground" />
                                <span>{exec.token_out || 'Unknown'}</span>
                              </p>
                              <p className="text-xs text-muted-foreground flex items-center gap-1 mt-0.5">
                                <Clock className="h-3 w-3" />
                                {(() => {
                                  try {
                                    if (typeof exec.timestamp === 'number' && !isNaN(exec.timestamp) && isFinite(exec.timestamp)) {
                                      const date = new Date(exec.timestamp * 1000);
                                      if (!isNaN(date.getTime())) {
                                        return date.toLocaleString();
                                      }
                                    }
                                    return 'Invalid Date';
                                  } catch {
                                    return 'Invalid Date';
                                  }
                                })()}
                              </p>
                            </div>
                          </div>
                          <div className="text-right">
                            <Badge variant="outline" className="border-green-500/30 text-green-500 mb-1">
                              +{(() => {
                                try {
                                  const savings = typeof exec.savings_pct === 'number' && !isNaN(exec.savings_pct) && isFinite(exec.savings_pct)
                                    ? exec.savings_pct.toFixed(2)
                                    : '0.00';
                                  return `${savings}%`;
                                } catch {
                                  return '0.00%';
                                }
                              })()}
                            </Badge>
                            <p className="text-xs text-muted-foreground capitalize">{exec.status || 'Unknown'}</p>
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
                    {(() => {
                      try {
                        const successRate = metrics?.success_rate;
                        if (typeof successRate === 'number' && !isNaN(successRate) && isFinite(successRate) && successRate >= 0 && successRate <= 100) {
                          return (
                            <div className="space-y-2">
                              <div className="flex items-center justify-between">
                                <span className="text-sm font-medium text-muted-foreground">Success Rate</span>
                                <span className="text-lg font-bold text-foreground">{successRate.toFixed(1)}%</span>
                              </div>
                              <div className="h-2 bg-muted rounded-full overflow-hidden">
                                <motion.div
                                  initial={{ width: 0 }}
                                  animate={{ width: `${Math.max(0, Math.min(100, successRate))}%` }}
                                  transition={{ delay: 0.6, duration: 0.8, ease: "easeOut" }}
                                  className="h-full bg-gradient-to-r from-green-500 to-green-400 rounded-full"
                                />
                              </div>
                            </div>
                          );
                        }
                        return null;
                      } catch {
                        return null;
                      }
                    })()}
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          </div>
          </TabsContent>

          <TabsContent value="financials" className="space-y-6">
            {/* Financial Summary Cards */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
              >
                <Card className="border-border/50 hover:border-green-500/30 transition-all duration-300">
                  <CardHeader className="flex flex-row items-center justify-between pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1.5">
                      Net Profit
                      <Info className="h-3 w-3 opacity-50" />
                    </CardTitle>
                    <div className="p-2 rounded-lg bg-green-500/10">
                      <DollarSign className="h-4 w-4 text-green-500" />
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className={`text-3xl font-bold mb-1 ${financialMetrics.netProfit >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                      {financialMetrics.netProfit >= 0 ? '+' : ''}{formatCurrency(financialMetrics.netProfit)}
                    </div>
                    <p className="text-xs text-muted-foreground flex items-center gap-1">
                      {financialMetrics.netProfit >= 0 ? <ArrowUpRight className="h-3 w-3 text-green-500" /> : <ArrowDownRight className="h-3 w-3 text-red-500" />}
                      Total after costs
                    </p>
                  </CardContent>
                </Card>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
              >
                <Card className="border-border/50 hover:border-blue-500/30 transition-all duration-300">
                  <CardHeader className="flex flex-row items-center justify-between pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1.5">
                      ROI
                      <Info className="h-3 w-3 opacity-50" />
                    </CardTitle>
                    <div className="p-2 rounded-lg bg-blue-500/10">
                      <TrendingUp className="h-4 w-4 text-blue-500" />
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className={`text-3xl font-bold mb-1 ${financialMetrics.roi >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                      {financialMetrics.roi >= 0 ? '+' : ''}{financialMetrics.roi.toFixed(2)}%
                    </div>
                    <p className="text-xs text-muted-foreground">Return on volume</p>
                  </CardContent>
                </Card>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
              >
                <Card className="border-border/50 hover:border-orange-500/30 transition-all duration-300">
                  <CardHeader className="flex flex-row items-center justify-between pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1.5">
                      Total Costs
                      <Info className="h-3 w-3 opacity-50" />
                    </CardTitle>
                    <div className="p-2 rounded-lg bg-orange-500/10">
                      <Wallet className="h-4 w-4 text-orange-500" />
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-bold mb-1 text-orange-500">
                      {formatCurrency(financialMetrics.totalCosts)}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Gas: {formatCurrency(financialMetrics.totalGas)} | Fees: {formatCurrency(financialMetrics.totalFees)}
                    </p>
                  </CardContent>
                </Card>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
              >
                <Card className="border-border/50 hover:border-purple-500/30 transition-all duration-300">
                  <CardHeader className="flex flex-row items-center justify-between pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1.5">
                      Avg Profit/Trade
                      <Info className="h-3 w-3 opacity-50" />
                    </CardTitle>
                    <div className="p-2 rounded-lg bg-purple-500/10">
                      <BarChart3 className="h-4 w-4 text-purple-500" />
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className={`text-3xl font-bold mb-1 ${financialMetrics.avgProfitPerExecution >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                      {financialMetrics.avgProfitPerExecution >= 0 ? '+' : ''}{formatCurrency(financialMetrics.avgProfitPerExecution)}
                    </div>
                    <p className="text-xs text-muted-foreground">Per execution</p>
                  </CardContent>
                </Card>
              </motion.div>
            </div>

            {/* Financial Charts Row */}
            <div className="grid gap-4 md:grid-cols-2">
              {/* Profit vs Costs Chart */}
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.5 }}
              >
                <Card className="border-border/50">
                  <CardHeader className="pb-3">
                    <CardTitle className="flex items-center gap-2">
                      <TrendingUp className="h-5 w-5 text-green-500" />
                      Profit & Costs Trend
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ChartContainer config={chartConfig} className="h-[300px] w-full">
                      <AreaChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
                        <defs>
                          <linearGradient id="colorProfit" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="hsl(142, 76%, 36%)" stopOpacity={0.3} />
                            <stop offset="95%" stopColor="hsl(142, 76%, 36%)" stopOpacity={0} />
                          </linearGradient>
                          <linearGradient id="colorCosts" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="hsl(0, 84%, 60%)" stopOpacity={0.3} />
                            <stop offset="95%" stopColor="hsl(0, 84%, 60%)" stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--muted))" opacity={0.3} />
                        <XAxis 
                          dataKey="time" 
                          tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }}
                          tickLine={{ stroke: 'hsl(var(--muted-foreground))' }}
                        />
                        <YAxis 
                          tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }}
                          tickLine={{ stroke: 'hsl(var(--muted-foreground))' }}
                        />
                        <ChartTooltip content={<ChartTooltipContent />} />
                        <Area
                          type="monotone"
                          dataKey="profit"
                          stroke="hsl(142, 76%, 36%)"
                          fill="url(#colorProfit)"
                          strokeWidth={2}
                          name="Profit (USD)"
                        />
                        <Area
                          type="monotone"
                          dataKey="costs"
                          stroke="hsl(0, 84%, 60%)"
                          fill="url(#colorCosts)"
                          strokeWidth={2}
                          name="Costs (USD)"
                        />
                        <Line
                          type="monotone"
                          dataKey="netProfit"
                          stroke="hsl(142, 76%, 46%)"
                          strokeWidth={2}
                          dot={false}
                          name="Net Profit (USD)"
                        />
                      </AreaChart>
                    </ChartContainer>
                  </CardContent>
                </Card>
              </motion.div>

              {/* DEX Distribution Pie Chart */}
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.6 }}
              >
                <Card className="border-border/50">
                  <CardHeader className="pb-3">
                    <CardTitle className="flex items-center gap-2">
                      <PieChart className="h-5 w-5 text-secondary" />
                      DEX Volume Distribution
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ChartContainer config={chartConfig} className="h-[300px] w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <RechartsPieChart>
                          <ChartTooltip content={<ChartTooltipContent />} />
                          <Pie 
                            data={dexDistributionData} 
                            cx="50%" 
                            cy="50%" 
                            outerRadius={80} 
                            dataKey="value" 
                            label={({ name, value }) => `${name}: ${value.toFixed(1)}%`}
                          >
                            {dexDistributionData.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={entry.color} />
                            ))}
                          </Pie>
                        </RechartsPieChart>
                      </ResponsiveContainer>
                    </ChartContainer>
                    <div className="mt-4 space-y-2">
                      {dexDistributionData.map((dex, idx) => (
                        <div key={idx} className="flex items-center justify-between text-sm">
                          <div className="flex items-center gap-2">
                            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: dex.color }} />
                            <span className="text-muted-foreground">{dex.name}</span>
                          </div>
                          <div className="text-right">
                            <span className="font-medium">{dex.value.toFixed(1)}%</span>
                            {dex.volume && (
                              <span className="text-xs text-muted-foreground ml-2">({formatCurrency(dex.volume)})</span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            </div>

            {/* Cost Breakdown */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.7 }}
            >
              <Card className="border-border/50">
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-center gap-2">
                    <BarChart3 className="h-5 w-5 text-primary" />
                    Cost Breakdown
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between p-4 rounded-lg bg-muted/30 border border-border/30">
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-blue-500/10">
                          <Zap className="h-4 w-4 text-blue-500" />
                        </div>
                        <div>
                          <p className="text-sm font-medium">Gas Costs</p>
                          <p className="text-xs text-muted-foreground">Transaction fees</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-lg font-bold">{formatCurrency(financialMetrics.totalGas)}</p>
                        <p className="text-xs text-muted-foreground">
                          {metrics?.total_executions ? `$${(financialMetrics.totalGas / metrics.total_executions).toFixed(2)} per execution` : ''}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center justify-between p-4 rounded-lg bg-muted/30 border border-border/30">
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-purple-500/10">
                          <DollarSign className="h-4 w-4 text-purple-500" />
                        </div>
                        <div>
                          <p className="text-sm font-medium">Protocol Fees</p>
                          <p className="text-xs text-muted-foreground">Service charges</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-lg font-bold">{formatCurrency(financialMetrics.totalFees)}</p>
                        <p className="text-xs text-muted-foreground">
                          {metrics?.total_volume_usd ? `${((financialMetrics.totalFees / metrics.total_volume_usd) * 100).toFixed(3)}% of volume` : ''}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center justify-between p-4 rounded-lg bg-green-500/10 border border-green-500/30">
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-green-500/20">
                          <TrendingUp className="h-4 w-4 text-green-500" />
                        </div>
                        <div>
                          <p className="text-sm font-medium text-green-500">Total Costs</p>
                          <p className="text-xs text-muted-foreground">Gas + Fees</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-lg font-bold text-green-500">{formatCurrency(financialMetrics.totalCosts)}</p>
                        <p className="text-xs text-muted-foreground">
                          {metrics?.total_executions ? `$${(financialMetrics.avgCostPerExecution).toFixed(2)} avg per execution` : ''}
                        </p>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>

            {/* Financial Executions Table */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.8 }}
            >
              <Card className="border-border/50">
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-center gap-2">
                    <Activity className="h-5 w-5 text-primary" />
                    Recent Executions (Financial Details)
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {metrics?.recent_executions && metrics.recent_executions.length > 0 ? (
                    <div className="space-y-3">
                      <AnimatePresence>
                        {metrics.recent_executions.slice(0, 10).map((exec, idx) => {
                          try {
                            const gasCost = typeof exec.gas_cost_usd === 'number' && !isNaN(exec.gas_cost_usd) && isFinite(exec.gas_cost_usd)
                              ? Math.max(0, exec.gas_cost_usd)
                              : 0;
                            const protocolFee = typeof exec.protocol_fee_usd === 'number' && !isNaN(exec.protocol_fee_usd) && isFinite(exec.protocol_fee_usd)
                              ? Math.max(0, exec.protocol_fee_usd)
                              : 0;
                            const profit = typeof exec.profit_usd === 'number' && !isNaN(exec.profit_usd) && isFinite(exec.profit_usd)
                              ? exec.profit_usd
                              : 0;
                            const netProfit = isFinite(profit - gasCost - protocolFee)
                              ? profit - gasCost - protocolFee
                              : 0;
                          return (
                            <motion.div
                              key={exec.id}
                              initial={{ opacity: 0, x: -10 }}
                              animate={{ opacity: 1, x: 0 }}
                              exit={{ opacity: 0, x: 10 }}
                              transition={{ delay: idx * 0.05 }}
                              className="p-4 rounded-lg bg-muted/30 hover:bg-muted/50 border border-border/30 transition-all"
                            >
                              <div className="flex items-start justify-between mb-3">
                                <div className="flex-1">
                                  <p className="text-sm font-medium flex items-center gap-2 mb-1">
                                    <span>
                                      {(() => {
                                        try {
                                          const amount = typeof exec.amount_in === 'number' && !isNaN(exec.amount_in) && isFinite(exec.amount_in)
                                            ? exec.amount_in.toLocaleString()
                                            : '0';
                                          return `${amount} ${exec.token_in || 'Unknown'}`;
                                        } catch {
                                          return `0 ${exec.token_in || 'Unknown'}`;
                                        }
                                      })()}
                                    </span>
                                    <ArrowRight className="h-3 w-3 text-muted-foreground" />
                                    <span>{exec.token_out || 'Unknown'}</span>
                                  </p>
                                  <p className="text-xs text-muted-foreground flex items-center gap-1">
                                    <Clock className="h-3 w-3" />
                                {(() => {
                                  try {
                                    if (typeof exec.timestamp === 'number' && !isNaN(exec.timestamp) && isFinite(exec.timestamp)) {
                                      const date = new Date(exec.timestamp * 1000);
                                      if (!isNaN(date.getTime())) {
                                        return date.toLocaleString();
                                      }
                                    }
                                    return 'Invalid Date';
                                  } catch {
                                    return 'Invalid Date';
                                  }
                                })()}
                                  </p>
                                </div>
                                <Badge variant="outline" className={`${netProfit >= 0 ? 'border-green-500/30 text-green-500' : 'border-red-500/30 text-red-500'}`}>
                                  {netProfit >= 0 ? '+' : ''}{formatCurrency(netProfit)}
                                </Badge>
                              </div>
                              <div className="grid grid-cols-4 gap-2 text-xs">
                                <div>
                                  <p className="text-muted-foreground">Gas</p>
                                  <p className="font-medium">-{formatCurrency(gasCost)}</p>
                                </div>
                                <div>
                                  <p className="text-muted-foreground">Fee</p>
                                  <p className="font-medium">-{formatCurrency(protocolFee)}</p>
                                </div>
                                <div>
                                  <p className="text-muted-foreground">Profit</p>
                                  <p className="font-medium text-green-500">+{formatCurrency(profit)}</p>
                                </div>
                                <div>
                                  <p className="text-muted-foreground">Savings</p>
                                  <p className="font-medium text-green-500">
                                    +{(() => {
                                      try {
                                        const savings = typeof exec.savings_pct === 'number' && !isNaN(exec.savings_pct) && isFinite(exec.savings_pct)
                                          ? exec.savings_pct.toFixed(2)
                                          : '0.00';
                                        return `${savings}%`;
                                      } catch {
                                        return '0.00%';
                                      }
                                    })()}
                                  </p>
                                </div>
                              </div>
                            </motion.div>
                          );
                          } catch (execErr) {
                            console.error(`Error rendering execution at index ${idx}:`, execErr);
                            return null;
                          }
                        }).filter(Boolean)}
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
          </TabsContent>
        </Tabs>
        </>
      )}
      </div>
    </TooltipProvider>
  );
}
