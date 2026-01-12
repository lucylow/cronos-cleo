import React, { useState, useEffect } from 'react';
import { useWallet } from '@/wallet/WalletProvider';
import { ethers } from 'ethers';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Loader2, TrendingUp, Zap, Shield } from 'lucide-react';
import { api } from '@/lib/api';

interface Route {
  id: string;
  dex: string;
  amountIn: number;
  estimatedOut: number;
  path: string[];
  pool_address?: string;
}

interface OptimizationResult {
  optimized_split: any;
  routes: Route[];
  predicted_improvement: number;
  risk_metrics: {
    diversification_score: number;
    max_single_route_share: number;
    route_count: number;
  };
}

// Common Cronos token addresses
const TOKEN_ADDRESSES: Record<string, string> = {
  CRO: '0x5C7F8A570d578B91F22530C0dbE9b54e18D7c019',
  'USDC.e': '0xc21223249CA28397B4B6541dfFaEcC539BfF0c59',
  USDT: '0x66e428c3f67a68878562e79A0234c1F83c208770',
};

export function CLEOSwapInterface() {
  const { account, signer } = useWallet();
  const isConnected = !!account;
  
  const [tokenIn, setTokenIn] = useState('CRO');
  const [tokenOut, setTokenOut] = useState('USDC.e');
  const [amount, setAmount] = useState('');
  const [maxSlippage, setMaxSlippage] = useState(0.5);
  const [optimization, setOptimization] = useState<OptimizationResult | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [executionProgress, setExecutionProgress] = useState(0);

  const handleAnalyze = async () => {
    if (!amount || parseFloat(amount) <= 0) {
      setError('Please enter a valid amount');
      return;
    }

    setIsAnalyzing(true);
    setError(null);
    setOptimization(null);

    try {
      const result = await api.optimize({
        token_in: tokenIn,
        token_out: tokenOut,
        amount_in: parseFloat(amount),
        max_slippage: maxSlippage / 100,
      });

      setOptimization(result);
    } catch (err: any) {
      setError(err.message || 'Failed to analyze routes');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleExecute = async () => {
    if (!optimization || !signer || !address) {
      setError('Missing required data for execution');
      return;
    }

    setIsExecuting(true);
    setError(null);
    setSuccess(null);
    setExecutionProgress(0);

    try {
      // Step 1: Approve tokens
      setExecutionProgress(10);
      await approveTokens(signer, tokenIn, amount);

      // Step 2: Execute swap
      setExecutionProgress(30);
      const result = await api.execute({
        token_in: tokenIn,
        token_out: tokenOut,
        amount_in: parseFloat(amount),
        max_slippage: maxSlippage / 100,
      });

      setExecutionProgress(100);
      
      if (result.execution?.success) {
        const savings = result.optimization?.predicted_improvement || 0;
        setSuccess(
          `Swap executed successfully! Transaction: ${result.execution.tx_hash?.slice(0, 10)}...` +
          (savings > 0 ? ` Estimated savings: ${(savings * 100).toFixed(2)}%` : '')
        );
        setOptimization(null);
      } else {
        setError(result.execution?.error || 'Execution failed');
      }
    } catch (err: any) {
      setError(err.message || 'Execution failed');
    } finally {
      setIsExecuting(false);
      setExecutionProgress(0);
    }
  };

  const approveTokens = async (signer: ethers.Signer, tokenSymbol: string, amount: string) => {
    const tokenAddress = TOKEN_ADDRESSES[tokenSymbol];
    if (!tokenAddress) {
      throw new Error(`Token address not found for ${tokenSymbol}`);
    }

    // ERC20 approve ABI
    const erc20Abi = [
      'function approve(address spender, uint256 amount) returns (bool)',
      'function allowance(address owner, address spender) view returns (uint256)',
    ];

    const tokenContract = new ethers.Contract(tokenAddress, erc20Abi, signer);
    const routerAddress = process.env.VITE_ROUTER_ADDRESS || '0x0000000000000000000000000000000000000000';
    
    // Check current allowance
    const allowance = await tokenContract.allowance(address, routerAddress);
    const amountWei = ethers.parseEther(amount);

    if (allowance < amountWei) {
      const tx = await tokenContract.approve(routerAddress, ethers.MaxUint256);
      await tx.wait();
    }
  };

  const totalEstimatedOut = optimization?.routes.reduce((sum, r) => sum + r.estimatedOut, 0) || 0;
  const estimatedSlippage = optimization?.optimized_split?.predicted_slippage 
    ? (optimization.optimized_split.predicted_slippage * 100).toFixed(2)
    : '0.00';

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Zap className="h-5 w-5" />
            C.L.E.O. Optimized Swap
          </CardTitle>
          <CardDescription>
            AI-powered cross-DEX routing with x402 atomic execution
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Token Selection */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>From</Label>
              <Select value={tokenIn} onValueChange={setTokenIn}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="CRO">CRO</SelectItem>
                  <SelectItem value="USDC.e">USDC.e</SelectItem>
                  <SelectItem value="USDT">USDT</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>To</Label>
              <Select value={tokenOut} onValueChange={setTokenOut}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="CRO">CRO</SelectItem>
                  <SelectItem value="USDC.e">USDC.e</SelectItem>
                  <SelectItem value="USDT">USDT</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Amount Input */}
          <div className="space-y-2">
            <Label>Amount</Label>
            <Input
              type="number"
              placeholder="0.0"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              disabled={isAnalyzing || isExecuting}
            />
          </div>

          {/* Max Slippage */}
          <div className="space-y-2">
            <Label>Max Slippage: {maxSlippage}%</Label>
            <input
              type="range"
              min="0.1"
              max="5"
              step="0.1"
              value={maxSlippage}
              onChange={(e) => setMaxSlippage(parseFloat(e.target.value))}
              className="w-full"
            />
          </div>

          {/* Analyze Button */}
          <Button
            onClick={handleAnalyze}
            disabled={!isConnected || isAnalyzing || isExecuting || !amount}
            className="w-full"
            size="lg"
          >
            {isAnalyzing ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Analyzing Routes...
              </>
            ) : (
              <>
                <TrendingUp className="mr-2 h-4 w-4" />
                Find Optimal Route
              </>
            )}
          </Button>

          {/* Error/Success Messages */}
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          {success && (
            <Alert>
              <AlertDescription>{success}</AlertDescription>
            </Alert>
          )}

          {/* Execution Progress */}
          {isExecuting && executionProgress > 0 && (
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Executing swap...</span>
                <span>{executionProgress}%</span>
              </div>
              <Progress value={executionProgress} />
            </div>
          )}
        </CardContent>
      </Card>

      {/* Optimization Results */}
      {optimization && (
        <Card>
          <CardHeader>
            <CardTitle>Optimized Route Found</CardTitle>
            <CardDescription>
              Split across {optimization.routes.length} DEX{optimization.routes.length > 1 ? 'es' : ''}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Route Visualization */}
            <div className="space-y-2">
              <Label>Route Distribution</Label>
              <div className="flex gap-1 h-8 rounded-md overflow-hidden">
                {optimization.routes.map((route, idx) => {
                  const percentage = (route.amountIn / parseFloat(amount)) * 100;
                  return (
                    <div
                      key={route.id}
                      className="flex items-center justify-center text-xs font-medium text-white"
                      style={{
                        width: `${percentage}%`,
                        backgroundColor: `hsl(${idx * 60}, 70%, 50%)`,
                      }}
                      title={`${route.dex}: ${percentage.toFixed(1)}%`}
                    >
                      {percentage > 10 && route.dex}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Metrics */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">Predicted Slippage</Label>
                <div className="text-2xl font-bold">{estimatedSlippage}%</div>
              </div>
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">Expected Output</Label>
                <div className="text-2xl font-bold">
                  {totalEstimatedOut.toFixed(2)} {tokenOut}
                </div>
              </div>
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">Improvement</Label>
                <div className="text-2xl font-bold text-green-600">
                  +{((optimization.predicted_improvement || 0) * 100).toFixed(2)}%
                </div>
              </div>
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">Diversification</Label>
                <div className="flex items-center gap-2">
                  <Shield className="h-4 w-4" />
                  <span className="text-lg font-semibold">
                    {optimization.risk_metrics.diversification_score}/10
                  </span>
                </div>
              </div>
            </div>

            {/* Route Breakdown */}
            <div className="space-y-2">
              <Label>Route Details</Label>
              <div className="space-y-2">
                {optimization.routes.map((route) => (
                  <div
                    key={route.id}
                    className="flex items-center justify-between p-3 border rounded-lg"
                  >
                    <div className="flex items-center gap-2">
                      <Badge variant="outline">{route.dex}</Badge>
                      <span className="text-sm text-muted-foreground">
                        {route.amountIn.toFixed(2)} {tokenIn}
                      </span>
                    </div>
                    <div className="text-sm font-medium">
                      → {route.estimatedOut.toFixed(2)} {tokenOut}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Execute Button */}
            <Button
              onClick={handleExecute}
              disabled={!isConnected || isExecuting}
              className="w-full"
              size="lg"
            >
              {isExecuting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Executing...
                </>
              ) : (
                <>
                  <Zap className="mr-2 h-4 w-4" />
                  Execute Optimized Swap
                </>
              )}
            </Button>
          </CardContent>
        </Card>
      )}

      {!isConnected && (
        <Alert>
          <AlertDescription>
            Please connect your wallet to use C.L.E.O. swap
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}

