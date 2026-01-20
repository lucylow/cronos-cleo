import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { TrendingUp, TrendingDown, Wallet, ArrowUpRight, ArrowDownRight, RefreshCw, Eye, EyeOff } from 'lucide-react';
import { Progress } from '@/components/ui/progress';
import { useAccount, useBalance } from 'wagmi';
import { formatUnits } from 'viem';

interface Token {
  symbol: string;
  name: string;
  balance: string;
  value: number;
  price: number;
  change24h: number;
  allocation: number;
  address?: string;
}

const mockTokens: Token[] = [
  {
    symbol: 'CRO',
    name: 'Cronos',
    balance: '12,450.50',
    value: 3450.25,
    price: 0.277,
    change24h: 2.5,
    allocation: 45,
  },
  {
    symbol: 'USDT',
    name: 'Tether',
    balance: '5,000.00',
    value: 5000.0,
    price: 1.0,
    change24h: 0.1,
    allocation: 32,
  },
  {
    symbol: 'WBTC',
    name: 'Wrapped Bitcoin',
    balance: '0.125',
    value: 2800.0,
    price: 22400.0,
    change24h: -1.2,
    allocation: 18,
  },
  {
    symbol: 'ETH',
    name: 'Ethereum',
    balance: '2.5',
    value: 1250.0,
    price: 500.0,
    change24h: 3.8,
    allocation: 5,
  },
];

export default function Portfolio() {
  const [hideBalances, setHideBalances] = useState(false);
  const { address } = useAccount();
  const totalValue = mockTokens.reduce((sum, token) => sum + token.value, 0);
  const totalChange24h = 1.8; // Mock change

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Portfolio</h1>
          <p className="text-muted-foreground mt-1">
            Track your token holdings and performance
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="icon"
            onClick={() => setHideBalances(!hideBalances)}
          >
            {hideBalances ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </Button>
          <Button variant="outline" size="icon">
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Portfolio Overview */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Value</CardTitle>
            <Wallet className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {hideBalances ? '••••••' : `$${totalValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
            </div>
            <p className="text-xs text-muted-foreground flex items-center mt-1">
              {totalChange24h > 0 ? (
                <>
                  <TrendingUp className="h-3 w-3 mr-1 text-green-500" />
                  <span className="text-green-500">+{totalChange24h}%</span>
                </>
              ) : (
                <>
                  <TrendingDown className="h-3 w-3 mr-1 text-red-500" />
                  <span className="text-red-500">{totalChange24h}%</span>
                </>
              )}
              <span className="ml-1">24h</span>
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Tokens</CardTitle>
            <Wallet className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mockTokens.length}</div>
            <p className="text-xs text-muted-foreground mt-1">Active holdings</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Address</CardTitle>
            <Wallet className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-sm font-mono truncate">
              {address ? `${address.slice(0, 6)}...${address.slice(-4)}` : 'Not connected'}
            </div>
            <p className="text-xs text-muted-foreground mt-1">Wallet address</p>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="tokens">Tokens</TabsTrigger>
          <TabsTrigger value="allocation">Allocation</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Portfolio Allocation</CardTitle>
              <CardDescription>Distribution of your holdings</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {mockTokens.map((token) => (
                  <div key={token.symbol} className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center font-bold">
                          {token.symbol.slice(0, 2)}
                        </div>
                        <div>
                          <div className="font-medium">{token.name}</div>
                          <div className="text-xs text-muted-foreground">{token.symbol}</div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="font-medium">
                          {hideBalances ? '••••' : `$${token.value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {token.allocation}%
                        </div>
                      </div>
                    </div>
                    <Progress value={token.allocation} className="h-2" />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="tokens" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Token Holdings</CardTitle>
              <CardDescription>Detailed view of your token balances</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {mockTokens.map((token) => (
                  <div
                    key={token.symbol}
                    className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50 transition-colors"
                  >
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-12 rounded-full bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center font-bold text-lg">
                        {token.symbol.slice(0, 2)}
                      </div>
                      <div>
                        <div className="font-semibold">{token.name}</div>
                        <div className="text-sm text-muted-foreground">
                          {hideBalances ? '••••' : `${token.balance} ${token.symbol}`}
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-semibold">
                        {hideBalances ? '••••' : `$${token.value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
                      </div>
                      <div className="text-sm text-muted-foreground">
                        ${token.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 6 })}
                      </div>
                      <div className={`text-xs flex items-center justify-end gap-1 mt-1 ${token.change24h >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                        {token.change24h >= 0 ? (
                          <TrendingUp className="h-3 w-3" />
                        ) : (
                          <TrendingDown className="h-3 w-3" />
                        )}
                        {Math.abs(token.change24h)}% 24h
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="allocation" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Portfolio Metrics</CardTitle>
              <CardDescription>Performance and allocation metrics</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <div className="text-sm font-medium">Top Holding</div>
                  <div className="text-2xl font-bold">{mockTokens[0].symbol}</div>
                  <div className="text-sm text-muted-foreground">
                    {mockTokens[0].allocation}% of portfolio
                  </div>
                </div>
                <div className="space-y-2">
                  <div className="text-sm font-medium">Best Performer (24h)</div>
                  <div className="text-2xl font-bold text-green-500">
                    {mockTokens.reduce((best, token) => (token.change24h > best.change24h ? token : best)).symbol}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    +{mockTokens.reduce((best, token) => (token.change24h > best.change24h ? token : best)).change24h}%
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}


