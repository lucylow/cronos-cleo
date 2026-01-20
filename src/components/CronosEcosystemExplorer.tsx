import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { useCronosBlockchain } from '@/hooks/useCronosBlockchain';
import { getCronosTokens, CRONOS_MAINNET_TOKENS, type CronosToken } from '@/lib/cronosTokens';
import { Search, Coins, TrendingUp, DollarSign, Shield, ExternalLink, Network, Zap } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from '@/components/ui/tooltip';
import { useChainId } from 'wagmi';
import { useState, useMemo } from 'react';
import { usePublicClient } from 'wagmi';
import { formatUnits } from 'viem';

interface TokenInfo extends CronosToken {
  price?: number;
  priceChange24h?: number;
  volume24h?: number;
  liquidity?: number;
  marketCap?: number;
}

export function CronosEcosystemExplorer() {
  const chainId = useChainId();
  const publicClient = usePublicClient();
  const { data: blockchainData, isConnected } = useCronosBlockchain({
    enabled: true,
  });
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTag, setSelectedTag] = useState<string | null>(null);

  // Get tokens for current chain
  const allTokens = useMemo(() => {
    const tokens = getCronosTokens(chainId);
    
    // Enhance with mock data (in real app, fetch from price APIs)
    return tokens.map((token): TokenInfo => {
      const basePrice = token.isStablecoin ? 1 : 0.1 + Math.random() * 10;
      const priceChange = (Math.random() - 0.5) * 10;
      
      return {
        ...token,
        price: basePrice,
        priceChange24h: priceChange,
        volume24h: Math.random() * 10000000,
        liquidity: Math.random() * 50000000,
        marketCap: basePrice * (Math.random() * 100000000),
      };
    });
  }, [chainId]);

  // Filter tokens
  const filteredTokens = useMemo(() => {
    let filtered = allTokens;

    // Filter by search
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (token) =>
          token.symbol.toLowerCase().includes(query) ||
          token.name.toLowerCase().includes(query) ||
          token.address.toLowerCase().includes(query)
      );
    }

    // Filter by tag
    if (selectedTag) {
      filtered = filtered.filter((token) => token.tags?.includes(selectedTag));
    }

    return filtered;
  }, [allTokens, searchQuery, selectedTag]);

  // Get unique tags
  const allTags = useMemo(() => {
    const tags = new Set<string>();
    allTokens.forEach((token) => {
      token.tags?.forEach((tag) => tags.add(tag));
    });
    return Array.from(tags).sort();
  }, [allTokens]);

  const formatCurrency = (value: number) => {
    if (value >= 1000000) return `$${(value / 1000000).toFixed(2)}M`;
    if (value >= 1000) return `$${(value / 1000).toFixed(2)}K`;
    return `$${value.toFixed(2)}`;
  };

  const explorerUrl = chainId === 25 
    ? 'https://cronoscan.com/token/' 
    : 'https://testnet.cronoscan.com/token/';

  if (!isConnected) {
    return (
      <Card className="border-yellow-500/50 bg-yellow-500/5">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-sm">
            <Network className="h-4 w-4 text-yellow-500" />
            Ecosystem Explorer
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Please connect to Cronos network to explore tokens.
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
                <Coins className="h-4 w-4 text-primary" />
                Cronos Ecosystem Explorer
              </div>
              <Badge variant="outline" className="text-xs">
                {filteredTokens.length} tokens
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Search and Filters */}
            <div className="space-y-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search tokens by name, symbol, or address..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9"
                />
              </div>

              {/* Tag Filters */}
              <div className="flex flex-wrap gap-2">
                <Badge
                  variant={selectedTag === null ? 'default' : 'outline'}
                  className="cursor-pointer"
                  onClick={() => setSelectedTag(null)}
                >
                  All
                </Badge>
                {allTags.map((tag) => (
                  <Badge
                    key={tag}
                    variant={selectedTag === tag ? 'default' : 'outline'}
                    className="cursor-pointer capitalize"
                    onClick={() => setSelectedTag(selectedTag === tag ? null : tag)}
                  >
                    {tag}
                  </Badge>
                ))}
              </div>
            </div>

            {/* Token List */}
            <div className="space-y-2 max-h-96 overflow-y-auto">
              <AnimatePresence mode="popLayout">
                {filteredTokens.length === 0 ? (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="text-center py-8 text-sm text-muted-foreground"
                  >
                    No tokens found matching your search.
                  </motion.div>
                ) : (
                  filteredTokens.map((token, index) => (
                    <motion.div
                      key={token.address}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: 20 }}
                      transition={{ delay: index * 0.02 }}
                    >
                      <Card className="border-border/30 hover:border-primary/50 transition-colors">
                        <CardContent className="pt-4">
                          <div className="flex items-center justify-between gap-4">
                            {/* Token Info */}
                            <div className="flex items-center gap-3 flex-1 min-w-0">
                              <div className="flex-shrink-0 w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                                <Coins className="h-5 w-5 text-primary" />
                              </div>
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2">
                                  <h4 className="font-semibold text-sm">{token.symbol}</h4>
                                  {token.isNative && (
                                    <Badge variant="secondary" className="text-xs">
                                      Native
                                    </Badge>
                                  )}
                                  {token.isStablecoin && (
                                    <Badge variant="outline" className="text-xs border-green-500/30 text-green-500">
                                      Stable
                                    </Badge>
                                  )}
                                </div>
                                <p className="text-xs text-muted-foreground truncate">
                                  {token.name}
                                </p>
                              </div>
                            </div>

                            {/* Price Info */}
                            <div className="flex items-center gap-4 text-right flex-shrink-0">
                              <div>
                                <p className="text-sm font-semibold">
                                  {token.price ? `$${token.price.toFixed(4)}` : 'N/A'}
                                </p>
                                {token.priceChange24h !== undefined && (
                                  <p
                                    className={`text-xs flex items-center justify-end gap-1 ${
                                      token.priceChange24h >= 0
                                        ? 'text-green-500'
                                        : 'text-red-500'
                                    }`}
                                  >
                                    <TrendingUp
                                      className={`h-3 w-3 ${
                                        token.priceChange24h < 0 ? 'rotate-180' : ''
                                      }`}
                                    />
                                    {Math.abs(token.priceChange24h).toFixed(2)}%
                                  </p>
                                )}
                              </div>
                              
                              {/* Actions */}
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <a
                                    href={`${explorerUrl}${token.address}`}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-muted-foreground hover:text-primary transition-colors"
                                  >
                                    <ExternalLink className="h-4 w-4" />
                                  </a>
                                </TooltipTrigger>
                                <TooltipContent>
                                  <p>View on Cronoscan</p>
                                </TooltipContent>
                              </Tooltip>
                            </div>
                          </div>

                          {/* Additional Metrics */}
                          {(token.volume24h || token.liquidity || token.marketCap) && (
                            <div className="grid grid-cols-3 gap-3 mt-3 pt-3 border-t border-border/30 text-xs">
                              {token.volume24h && (
                                <div>
                                  <p className="text-muted-foreground mb-1">24h Vol</p>
                                  <p className="font-medium">{formatCurrency(token.volume24h)}</p>
                                </div>
                              )}
                              {token.liquidity && (
                                <div>
                                  <p className="text-muted-foreground mb-1">Liquidity</p>
                                  <p className="font-medium">{formatCurrency(token.liquidity)}</p>
                                </div>
                              )}
                              {token.marketCap && (
                                <div>
                                  <p className="text-muted-foreground mb-1">Market Cap</p>
                                  <p className="font-medium">{formatCurrency(token.marketCap)}</p>
                                </div>
                              )}
                            </div>
                          )}

                          {/* Tags */}
                          {token.tags && token.tags.length > 0 && (
                            <div className="flex flex-wrap gap-1 mt-2">
                              {token.tags.map((tag) => (
                                <Badge
                                  key={tag}
                                  variant="outline"
                                  className="text-xs capitalize"
                                >
                                  {tag}
                                </Badge>
                              ))}
                            </div>
                          )}
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
