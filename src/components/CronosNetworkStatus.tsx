import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { useCronosBlockchain } from '@/hooks/useCronosBlockchain';
import { Network, CheckCircle2, AlertCircle, Clock, Activity, Zap } from 'lucide-react';
import { motion } from 'framer-motion';
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from '@/components/ui/tooltip';
import { ExternalLink } from 'lucide-react';

export function CronosNetworkStatus() {
  const { data, loading, error, isConnected } = useCronosBlockchain({
    enabled: true,
    updateInterval: 5000,
    trackBlockTime: true,
  });

  if (!isConnected && !loading) {
    return (
      <Card className="border-yellow-500/50 bg-yellow-500/5">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-sm">
            <AlertCircle className="h-4 w-4 text-yellow-500" />
            Network Status
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Please connect to Cronos Mainnet or Testnet to view network status.
          </p>
        </CardContent>
      </Card>
    );
  }

  if (loading && !data) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <Skeleton className="h-5 w-32" />
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-2/3" />
          <Skeleton className="h-4 w-1/2" />
        </CardContent>
      </Card>
    );
  }

  if (error || !data) {
    return (
      <Card className="border-red-500/50 bg-red-500/5">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-sm text-red-500">
            <AlertCircle className="h-4 w-4" />
            Network Status
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            {error || 'Failed to load network status'}
          </p>
        </CardContent>
      </Card>
    );
  }

  const blockTimeSeconds = data.blockTime ? data.blockTime.toFixed(1) : null;
  const blockTimeDisplay = blockTimeSeconds ? `${blockTimeSeconds}s` : 'N/A';
  const gasPriceDisplay = data.gasPriceGwei ? `${parseFloat(data.gasPriceGwei).toFixed(2)} Gwei` : 'N/A';

  return (
    <TooltipProvider>
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <Card className="border-border/50">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                <Network className="h-4 w-4 text-primary" />
                Cronos Network
              </div>
              <div className="flex items-center gap-2">
                {data.isMainnet ? (
                  <Badge variant="default" className="bg-green-500/20 text-green-500 border-green-500/30">
                    Mainnet
                  </Badge>
                ) : (
                  <Badge variant="secondary" className="bg-yellow-500/20 text-yellow-500 border-yellow-500/30">
                    Testnet
                  </Badge>
                )}
                <motion.div
                  animate={{ scale: [1, 1.2, 1] }}
                  transition={{ duration: 2, repeat: Infinity, repeatDelay: 2 }}
                >
                  <div className="h-2 w-2 rounded-full bg-green-500" />
                </motion.div>
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {/* Current Block */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Activity className="h-3.5 w-3.5 text-muted-foreground" />
                <span className="text-xs text-muted-foreground">Current Block</span>
              </div>
              <Tooltip>
                <TooltipTrigger asChild>
                  <a
                    href={`${data.explorerUrl}/block/${data.currentBlock}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-sm font-mono font-medium hover:text-primary transition-colors"
                  >
                    {data.currentBlock?.toLocaleString()}
                    <ExternalLink className="h-3 w-3" />
                  </a>
                </TooltipTrigger>
                <TooltipContent>
                  <p>View block on {data.networkName === 'Cronos Mainnet' ? 'Cronoscan' : 'Testnet Cronoscan'}</p>
                </TooltipContent>
              </Tooltip>
            </div>

            {/* Block Time */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Clock className="h-3.5 w-3.5 text-muted-foreground" />
                <span className="text-xs text-muted-foreground">Block Time</span>
              </div>
              <Tooltip>
                <TooltipTrigger asChild>
                  <span className="text-sm font-medium">{blockTimeDisplay}</span>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Average time between blocks</p>
                  {data.lastBlockTime && (
                    <p className="text-xs mt-1">Last block: {(data.lastBlockTime / 1000).toFixed(1)}s ago</p>
                  )}
                </TooltipContent>
              </Tooltip>
            </div>

            {/* Gas Price */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Zap className="h-3.5 w-3.5 text-muted-foreground" />
                <span className="text-xs text-muted-foreground">Gas Price</span>
              </div>
              <Tooltip>
                <TooltipTrigger asChild>
                  <span className="text-sm font-medium">{gasPriceDisplay}</span>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Current network gas price</p>
                  <p className="text-xs mt-1">Recommended for transactions</p>
                </TooltipContent>
              </Tooltip>
            </div>

            {/* Network Status */}
            <div className="flex items-center justify-between pt-2 border-t border-border/50">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />
                <span className="text-xs text-muted-foreground">Status</span>
              </div>
              <Badge variant="outline" className="border-green-500/30 text-green-500 text-xs">
                Operational
              </Badge>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </TooltipProvider>
  );
}


