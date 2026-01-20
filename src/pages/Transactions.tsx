import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { CheckCircle2, XCircle, Clock, ArrowUpRight, ArrowDownRight, Search, Filter, Download, ExternalLink } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

interface Transaction {
  id: string;
  timestamp: string;
  type: 'swap' | 'payment' | 'settlement';
  status: 'completed' | 'pending' | 'failed';
  tokenIn: string;
  tokenOut: string;
  amountIn: string;
  amountOut: string;
  dex: string;
  savings: number;
  gasCost: string;
  txHash: string;
}

const mockTransactions: Transaction[] = [
  {
    id: '1',
    timestamp: '2024-01-15 14:23:45',
    type: 'swap',
    status: 'completed',
    tokenIn: 'CRO',
    tokenOut: 'USDT',
    amountIn: '1,000',
    amountOut: '950',
    dex: 'VVS Finance',
    savings: 4.2,
    gasCost: '$0.12',
    txHash: '0x1234...5678',
  },
  {
    id: '2',
    timestamp: '2024-01-15 13:15:22',
    type: 'payment',
    status: 'completed',
    tokenIn: 'USDT',
    tokenOut: 'DAI',
    amountIn: '500',
    amountOut: '498',
    dex: 'Cronaswap',
    savings: 3.8,
    gasCost: '$0.10',
    txHash: '0xabcd...efgh',
  },
  {
    id: '3',
    timestamp: '2024-01-15 12:08:11',
    type: 'settlement',
    status: 'pending',
    tokenIn: 'WBTC',
    tokenOut: 'ETH',
    amountIn: '0.5',
    amountOut: '8.2',
    dex: 'MM Finance',
    savings: 5.1,
    gasCost: '$0.15',
    txHash: '0x9876...4321',
  },
  {
    id: '4',
    timestamp: '2024-01-15 11:45:33',
    type: 'swap',
    status: 'failed',
    tokenIn: 'USDC',
    tokenOut: 'CRO',
    amountIn: '2,000',
    amountOut: '0',
    dex: 'Tectonic',
    savings: 0,
    gasCost: '$0.08',
    txHash: '0xfedc...ba98',
  },
];

const statusConfig = {
  completed: { label: 'Completed', icon: CheckCircle2, variant: 'default' as const, color: 'text-green-500' },
  pending: { label: 'Pending', icon: Clock, variant: 'secondary' as const, color: 'text-yellow-500' },
  failed: { label: 'Failed', icon: XCircle, variant: 'destructive' as const, color: 'text-red-500' },
};

const typeConfig = {
  swap: { label: 'Swap', color: 'bg-blue-500/10 text-blue-500' },
  payment: { label: 'Payment', color: 'bg-green-500/10 text-green-500' },
  settlement: { label: 'Settlement', color: 'bg-purple-500/10 text-purple-500' },
};

export default function Transactions() {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [typeFilter, setTypeFilter] = useState<string>('all');

  const filteredTransactions = mockTransactions.filter((tx) => {
    const matchesSearch =
      tx.id.includes(searchQuery) ||
      tx.tokenIn.toLowerCase().includes(searchQuery.toLowerCase()) ||
      tx.tokenOut.toLowerCase().includes(searchQuery.toLowerCase()) ||
      tx.txHash.includes(searchQuery);
    const matchesStatus = statusFilter === 'all' || tx.status === statusFilter;
    const matchesType = typeFilter === 'all' || tx.type === typeFilter;
    return matchesSearch && matchesStatus && matchesType;
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Transactions</h1>
          <p className="text-muted-foreground mt-1">
            View and manage your transaction history
          </p>
        </div>
        <Button variant="outline">
          <Download className="h-4 w-4 mr-2" />
          Export
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Transaction History</CardTitle>
          <CardDescription>All your transactions in one place</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-4 mb-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search by ID, token, or hash..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-full sm:w-[180px]">
                <SelectValue placeholder="Filter by status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="failed">Failed</SelectItem>
              </SelectContent>
            </Select>
            <Select value={typeFilter} onValueChange={setTypeFilter}>
              <SelectTrigger className="w-full sm:w-[180px]">
                <SelectValue placeholder="Filter by type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                <SelectItem value="swap">Swap</SelectItem>
                <SelectItem value="payment">Payment</SelectItem>
                <SelectItem value="settlement">Settlement</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <Tabs defaultValue="all" className="w-full">
            <TabsList>
              <TabsTrigger value="all">All ({mockTransactions.length})</TabsTrigger>
              <TabsTrigger value="completed">
                Completed ({mockTransactions.filter((t) => t.status === 'completed').length})
              </TabsTrigger>
              <TabsTrigger value="pending">
                Pending ({mockTransactions.filter((t) => t.status === 'pending').length})
              </TabsTrigger>
              <TabsTrigger value="failed">
                Failed ({mockTransactions.filter((t) => t.status === 'failed').length})
              </TabsTrigger>
            </TabsList>

            <TabsContent value="all" className="mt-4">
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Time</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Transaction</TableHead>
                      <TableHead>DEX</TableHead>
                      <TableHead>Savings</TableHead>
                      <TableHead>Gas Cost</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredTransactions.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={8} className="text-center text-muted-foreground py-8">
                          No transactions found
                        </TableCell>
                      </TableRow>
                    ) : (
                      filteredTransactions.map((tx) => {
                        const StatusIcon = statusConfig[tx.status].icon;
                        const typeInfo = typeConfig[tx.type];
                        return (
                          <TableRow key={tx.id}>
                            <TableCell className="font-mono text-xs">{tx.timestamp}</TableCell>
                            <TableCell>
                              <Badge className={typeInfo.color}>{typeInfo.label}</Badge>
                            </TableCell>
                            <TableCell>
                              <div className="flex items-center gap-2">
                                <span className="font-medium">{tx.amountIn}</span>
                                <span className="text-muted-foreground">{tx.tokenIn}</span>
                                <ArrowRight className="h-3 w-3 text-muted-foreground" />
                                <span className="font-medium">{tx.amountOut}</span>
                                <span className="text-muted-foreground">{tx.tokenOut}</span>
                              </div>
                            </TableCell>
                            <TableCell>
                              <Badge variant="outline">{tx.dex}</Badge>
                            </TableCell>
                            <TableCell>
                              {tx.savings > 0 ? (
                                <span className="text-green-500 font-medium">+{tx.savings}%</span>
                              ) : (
                                <span className="text-muted-foreground">-</span>
                              )}
                            </TableCell>
                            <TableCell className="text-muted-foreground">{tx.gasCost}</TableCell>
                            <TableCell>
                              <TooltipProvider>
                                <Tooltip>
                                  <TooltipTrigger>
                                    <Badge
                                      variant={statusConfig[tx.status].variant}
                                      className="flex items-center gap-1 w-fit"
                                    >
                                      <StatusIcon className="h-3 w-3" />
                                      {statusConfig[tx.status].label}
                                    </Badge>
                                  </TooltipTrigger>
                                  <TooltipContent>
                                    <p>Transaction {statusConfig[tx.status].label.toLowerCase()}</p>
                                  </TooltipContent>
                                </Tooltip>
                              </TooltipProvider>
                            </TableCell>
                            <TableCell className="text-right">
                              <TooltipProvider>
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <Button variant="ghost" size="icon">
                                      <ExternalLink className="h-4 w-4" />
                                    </Button>
                                  </TooltipTrigger>
                                  <TooltipContent>
                                    <p>View on explorer</p>
                                  </TooltipContent>
                                </Tooltip>
                              </TooltipProvider>
                            </TableCell>
                          </TableRow>
                        );
                      })
                    )}
                  </TableBody>
                </Table>
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}

