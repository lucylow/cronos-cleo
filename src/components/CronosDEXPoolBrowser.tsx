import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useCronosBlockchain } from '@/hooks/useCronosBlockchain';
import { getCronosTokens, CRONOS_DEX_ROUTERS } from '@/lib/cronosTokens';
import { Search, TrendingUp, DollarSign, Activity, Network, ArrowLeftRight, Zap, ExternalLink } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from '@/components/ui/tooltip';
import { useChainId } from 'wagmi';
import { useState, useMemo } from 'react';

interface PoolInfo {
  id: string;
  dex: string;
  dexId: string;
  token0: string;
  token1: string;
  token0Symbol: string;
  token1Symbol: string;
  liquidity: number;
  volume24h: number;
  volume7d: number;
  fees24h: number;
  apy: number;
  feeTier: number;
  tvl: number;
  poolAddress: string;
}

const DEX_OPTIONS = [
  { value: 'all', label: 'All DEXs' },
  { value: 'vvs', label: 'VVS Finance' },
  { value: 'cronaswap', label: 'CronaSwap' },
  { value: 'mmfinance', label: 'MM Finance' },
];

export function CronosDEXPoolBrowser() {
  const chainId = useChainId();
  const { data: blockchainData, isConnected } = useCronosBlockchain({
    enabled: true,
  });
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDEX, setSelectedDEX] = useState('all');
  const [sortBy, setSortBy] = useState<'tvl' | 'volume24h' | 'apy'>('tvl');

  // Mock pool data - in production, fetch from DEX subgraphs
  const allPools = useMemo<PoolInfo[]>(() => {
    const tokens = getCronosTokens(chainId);
    const popularPairs = [
      ['CRO', 'USDC'],
      ['CRO', 'USDT'],
      ['WCRO', 'CRO'],
      ['VVS', 'CRO'],
      ['MMF', 'CRO'],
      ['CRONA', 'CRO'],
      ['WBTC', 'USDC'],
      ['WETH', 'USDC'],
      ['USDC', 'USDT'],
      ['LINK', 'USDC'],
      ['AAVE', 'USDC'],
      ['ATOM', 'CRO'],
    ];

    const dexes = [
      { id: 'vvs', name: 'VVS Finance', color: 'blue' },
      { id: 'cronaswap', name: 'CronaSwap', color: 'purple' },
      { id: 'mmfinance', name: 'MM Finance', color: 'green' },
    ];

    const pools: PoolInfo[] = [];

    dexes.forEach((dex) => {
      popularPairs.forEach((pair, idx) => {
        const [token0Sym, token1Sym] = pair;
        const token0 = tokens.find((t) => t.symbol === token0Sym);
        const token1 = tokens.find((t) => t.symbol === token1Sym);

        if (token0 && token1) {
          const baseLiquidity = (Math.random() * 5000000 + 100000) * (idx % 3 + 1);
          pools.push({
            id: `${dex.id}-${pair.join('-')}`,
            dex: dex.name,
            dexId: dex.id,
            token0: token0.address,
            token1: token1.address,
            token0Symbol: token0.symbol,
            token1Symbol: token1.symbol,
            liquidity: baseLiquidity,
            volume24h: baseLiquidity * 0.1 * (0.5 + Math.random()),
            volume7d: baseLiquidity * 0.7 * (0.5 + Math.random()),
            fees24h: baseLiquidity * 0.003 * 0.1 * (0.5 + Math.random()),
            apy: 5 + Math.random() * 50,
            feeTier: 30, // 0.3%
            tvl: baseLiquidity,
            poolAddress: `0x${Math.random().toString(16).substring(2, 42)}`,
          });
        }
      });
    });

    return pools;
  }, [chainId]);

  // Filter and sort pools
  const filteredPools = useMemo(() => {
    let filtered = allPools;

    // Filter by DEX
    if (selectedDEX !== 'all') {
      filtered = filtered.filter((pool) => pool.dexId === selectedDEX);
    }

    // Filter by search
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (pool) =>
          pool.token0Symbol.toLowerCase().includes(query) ||
          pool.token1Symbol.toLowerCase().includes(query) ||
          pool.dex.toLowerCase().includes(query)
      );
    }

    // Sort
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'tvl':
          return b.tvl - a.tvl;
        case 'volume24h':
          return b.volume24h - a.volume24h;
        case 'apy':
          return b.apy - a.apy;
        default:
          return 0;
      }
    });

    return filtered;
  }, [allPools, selectedDEX, searchQuery, sortBy]);

  const formatCurrency = (value: number) => {
    if (value >= 1000000) return `$${(value / 1000000).toFixed(2)}M`;
    if (value >= 1000) return `$${(value / 1000).toFixed(2)}K`;
    return `$${value.toFixed(2)}`;
  };

  const explorerUrl = chainId === 25 
    ? 'https://cronoscan.com/address/' 
    : 'https://testnet.cronoscan.com/address/';

  if (!isConnected) {
    return (
      <Card className="border-yellow-500/50 bg-yellow-500/5">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-sm">
            <Network className="h-4 w-4 text-yellow-500" />
            DEX Pool Browser
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Please connect to Cronos network to browse pools.
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
                <Activity className="h-4 w-4 text-primary" />
                DEX Pool Browser
              </div>
              <Badge variant="outline" className="text-xs">
                {filteredPools.length} pools
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Filters */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search pools..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9"
                />
              </div>

              <Select value={selectedDEX} onValueChange={setSelectedDEX}>
                <SelectTrigger>
                  <SelectValue placeholder="Select DEX" />
                </SelectTrigger>
                <SelectContent>
                  {DEX_OPTIONS.map((dex) => (
                    <SelectItem key={dex.value} value={dex.value}>
                      {dex.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select value={sortBy} onValueChange={(v) => setSortBy(v as typeof sortBy)}>
                <SelectTrigger>
                  <SelectValue placeholder="Sort by" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="tvl">Sort by TVL</SelectItem>
                  <SelectItem value="volume24h">Sort by Volume</SelectItem>
                  <SelectItem value="apy">Sort by APY</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Pool List */}
            <div className="space-y-2 max-h-96 overflow-y-auto">
              <AnimatePresence mode="popLayout">
                {filteredPools.length === 0 ? (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="text-center py-8 text-sm text-muted-foreground"
                  >
                    No pools found matching your criteria.
                  </motion.div>
                ) : (
                  filteredPools.map((pool, index) => (
                    <motion.div
                      key={pool.id}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: 20 }}
                      transition={{ delay: index * 0.02 }}
                    >
                      <Card className="border-border/30 hover:border-primary/50 transition-colors">
                        <CardContent className="pt-4">
                          <div className="flex items-center justify-between gap-4">
                            {/* Pool Pair */}
                            <div className="flex items-center gap-3 flex-1 min-w-0">
                              <div className="flex-shrink-0 w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                                <ArrowLeftRight className="h-5 w-5 text-primary" />
                              </div>
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2">
                                  <h4 className="font-semibold text-sm">
                                    {pool.token0Symbol} / {pool.token1Symbol}
                                  </h4>
                                  <Badge variant="outline" className="text-xs">
                                    {pool.dex}
                                  </Badge>
                                  <Badge variant="secondary" className="text-xs">
                                    {(pool.feeTier / 10000).toFixed(2)}%
                                  </Badge>
                                </div>
                                <p className="text-xs text-muted-foreground">
                                  TVL: {formatCurrency(pool.tvl)}
                                </p>
                              </div>
                            </div>

                            {/* Metrics */}
                            <div className="flex items-center gap-4 text-right flex-shrink-0">
                              <div className="space-y-1">
                                <div className="flex items-center gap-1">
                                  <TrendingUp className="h-3 w-3 text-green-500" />
                                  <p className="text-sm font-semibold text-green-500">
                                    {pool.apy.toFixed(1)}% APY
                                  </p>
                                </div>
                                <p className="text-xs text-muted-foreground">
                                  24h: {formatCurrency(pool.volume24h)}
                                </p>
                              </div>
                              
                              {/* Actions */}
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <a
                                    href={`${explorerUrl}${pool.poolAddress}`}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-muted-foreground hover:text-primary transition-colors"
                                  >
                                    <ExternalLink className="h-4 w-4" />
                                  </a>
                                </TooltipTrigger>
                                <TooltipContent>
                                  <p>View pool on Cronoscan</p>
                                </TooltipContent>
                              </Tooltip>
                            </div>
                          </div>

                          {/* Additional Metrics */}
                          <div className="grid grid-cols-3 gap-3 mt-3 pt-3 border-t border-border/30 text-xs">
                            <div>
                              <p className="text-muted-foreground mb-1">24h Volume</p>
                              <p className="font-medium">{formatCurrency(pool.volume24h)}</p>
                            </div>
                            <div>
                              <p className="text-muted-foreground mb-1">7d Volume</p>
                              <p className="font-medium">{formatCurrency(pool.volume7d)}</p>
                            </div>
                            <div>
                              <p className="text-muted-foreground mb-1">24h Fees</p>
                              <p className="font-medium">{formatCurrency(pool.fees24h)}</p>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    </motion.div>
                  ))
                )}
              </AnimatePresence>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </TooltipProvider>
  );
}
