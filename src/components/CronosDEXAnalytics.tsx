import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { useCronosBlockchain } from '@/hooks/useCronosBlockchain';
import { CRONOS_DEX_ROUTERS, getCronosTokens } from '@/lib/cronosTokens';
import { TrendingUp, TrendingDown, BarChart3, DollarSign, Activity, Users, Zap, ExternalLink, Network } from 'lucide-react';
import { motion } from 'framer-motion';
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from '@/components/ui/tooltip';
import { useChainId } from 'wagmi';
import { useEffect, useState } from 'react';

interface DEXData {
  name: string;
  id: string;
  tvl: number;
  volume24h: number;
  volume7d: number;
  fees24h: number;
  pools: number;
  apy: number;
  priceImpact: number;
  routerAddress: string;
  color: string;
  explorerUrl: string;
}

export function CronosDEXAnalytics() {
  const chainId = useChainId();
  const { data: blockchainData, isConnected } = useCronosBlockchain({
    enabled: true,
    updateInterval: 10000,
  });
  const [dexData, setDexData] = useState<DEXData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isConnected || !blockchainData) return;

    // Simulate fetching DEX data (in real app, this would come from APIs)
    // VVS Finance, CronaSwap, MM Finance subgraphs or APIs
    const fetchDEXData = async () => {
      setLoading(true);
      
      // Mock data - replace with actual API calls to DEX subgraphs
      const mockData: DEXData[] = [
        {
          name: 'VVS Finance',
          id: 'vvs',
          tvl: 125000000,
          volume24h: 8500000,
          volume7d: 62500000,
          fees24h: 25500,
          pools: 342,
          apy: 12.5,
          priceImpact: 0.15,
          routerAddress: CRONOS_DEX_ROUTERS.vvs[chainId === 25 ? 'mainnet' : 'testnet'],
          color: 'bg-blue-500',
          explorerUrl: 'https://vvs.finance',
        },
        {
          name: 'CronaSwap',
          id: 'cronaswap',
          tvl: 89000000,
          volume24h: 5200000,
          volume7d: 38500000,
          fees24h: 15600,
          pools: 278,
          apy: 10.8,
          priceImpact: 0.18,
          routerAddress: CRONOS_DEX_ROUTERS.cronaswap[chainId === 25 ? 'mainnet' : 'testnet'],
          color: 'bg-purple-500',
          explorerUrl: 'https://app.cronaswap.org',
        },
        {
          name: 'MM Finance',
          id: 'mmfinance',
          tvl: 67000000,
          volume24h: 4100000,
          volume7d: 29800000,
          fees24h: 12300,
          pools: 215,
          apy: 14.2,
          priceImpact: 0.22,
          routerAddress: CRONOS_DEX_ROUTERS.mmfinance[chainId === 25 ? 'mainnet' : 'testnet'],
          color: 'bg-green-500',
          explorerUrl: 'https://mm.finance',
        },
      ];

      // Add a small random variation to simulate live data
      const dataWithVariation = mockData.map(dex => ({
        ...dex,
        volume24h: dex.volume24h * (1 + (Math.random() - 0.5) * 0.1),
        fees24h: dex.fees24h * (1 + (Math.random() - 0.5) * 0.1),
        tvl: dex.tvl * (1 + (Math.random() - 0.5) * 0.05),
      }));

      setDexData(dataWithVariation);
      setLoading(false);
    };

    fetchDEXData();
    const interval = setInterval(fetchDEXData, 30000); // Update every 30 seconds

    return () => clearInterval(interval);
  }, [isConnected, blockchainData, chainId]);

  const formatCurrency = (value: number) => {
    if (value >= 1000000) return `$${(value / 1000000).toFixed(2)}M`;
    if (value >= 1000) return `$${(value / 1000).toFixed(2)}K`;
    return `$${value.toFixed(2)}`;
  };

  const formatNumber = (value: number) => {
    return new Intl.NumberFormat('en-US').format(value);
  };

  const totalTVL = dexData.reduce((sum, dex) => sum + dex.tvl, 0);
  const totalVolume24h = dexData.reduce((sum, dex) => sum + dex.volume24h, 0);
  const totalFees24h = dexData.reduce((sum, dex) => sum + dex.fees24h, 0);

  if (!isConnected) {
    return (
      <Card className="border-yellow-500/50 bg-yellow-500/5">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-sm">
            <Network className="h-4 w-4 text-yellow-500" />
            DEX Analytics
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Please connect to Cronos network to view DEX analytics.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <TooltipProvider>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <Card className="border-border/50">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                <BarChart3 className="h-4 w-4 text-primary" />
                Cronos DEX Analytics
              </div>
              <Badge variant="outline" className="text-xs">
                {chainId === 25 ? 'Mainnet' : 'Testnet'}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Summary Stats */}
            <div className="grid grid-cols-3 gap-3 pb-3 border-b">
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">Total TVL</p>
                <p className="text-lg font-bold">{formatCurrency(totalTVL)}</p>
              </div>
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">24h Volume</p>
                <p className="text-lg font-bold">{formatCurrency(totalVolume24h)}</p>
              </div>
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">24h Fees</p>
                <p className="text-lg font-bold">{formatCurrency(totalFees24h)}</p>
              </div>
            </div>

            {/* DEX Cards */}
            {loading ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-32 w-full" />
                ))}
              </div>
            ) : (
              <div className="space-y-3">
                {dexData.map((dex, index) => (
                  <motion.div
                    key={dex.id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.1 }}
                  >
                    <Card className="border-border/30 hover:border-primary/50 transition-colors">
                      <CardContent className="pt-4 space-y-3">
                        {/* DEX Header */}
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <div className={`w-3 h-3 rounded-full ${dex.color}`} />
                            <div>
                              <h4 className="font-semibold text-sm">{dex.name}</h4>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <a
                                    href={dex.explorerUrl}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-xs text-muted-foreground hover:text-primary flex items-center gap-1"
                                  >
                                    {dex.routerAddress.slice(0, 10)}...
                                    <ExternalLink className="h-3 w-3" />
                                  </a>
                                </TooltipTrigger>
                                <TooltipContent>
                                  <p>Router: {dex.routerAddress}</p>
                                  <p className="text-xs mt-1">Click to visit {dex.name}</p>
                                </TooltipContent>
                              </Tooltip>
                            </div>
                          </div>
                          <Badge variant="outline" className="text-xs">
                            APY: {dex.apy.toFixed(1)}%
                          </Badge>
                        </div>

                        {/* Metrics Grid */}
                        <div className="grid grid-cols-4 gap-3 text-xs">
                          <div>
                            <p className="text-muted-foreground mb-1">TVL</p>
                            <p className="font-semibold">{formatCurrency(dex.tvl)}</p>
                          </div>
                          <div>
                            <p className="text-muted-foreground mb-1">24h Vol</p>
                            <p className="font-semibold flex items-center gap-1">
                              {formatCurrency(dex.volume24h)}
                              <TrendingUp className="h-3 w-3 text-green-500" />
                            </p>
                          </div>
                          <div>
                            <p className="text-muted-foreground mb-1">24h Fees</p>
                            <p className="font-semibold">{formatCurrency(dex.fees24h)}</p>
                          </div>
                          <div>
                            <p className="text-muted-foreground mb-1">Pools</p>
                            <p className="font-semibold flex items-center gap-1">
                              {formatNumber(dex.pools)}
                              <Activity className="h-3 w-3 text-blue-500" />
                            </p>
                          </div>
                        </div>

                        {/* TVL Share Bar */}
                        <div className="space-y-1">
                          <div className="flex justify-between text-xs">
                            <span className="text-muted-foreground">TVL Share</span>
                            <span className="font-medium">
                              {((dex.tvl / totalTVL) * 100).toFixed(1)}%
                            </span>
                          </div>
                          <div className="h-2 bg-muted rounded-full overflow-hidden">
                            <div
                              className={`h-full ${dex.color} transition-all`}
                              style={{ width: `${(dex.tvl / totalTVL) * 100}%` }}
                            />
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </motion.div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </motion.div>
    </TooltipProvider>
  );
}
