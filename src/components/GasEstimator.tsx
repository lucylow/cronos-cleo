import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { ethers } from 'ethers';
import { useWagmiWallet } from '../hooks/useWagmiWallet';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Skeleton } from './ui/skeleton';

export default function GasEstimator({ 
  txData 
}: { 
  txData?: { to: string; data?: string; value?: string } | null 
}) {
  const { signer } = useWagmiWallet();
  const [estimate, setEstimate] = useState<bigint | null>(null);
  const [gasPrice, setGasPrice] = useState<bigint | null>(null);
  const [loading, setLoading] = useState(false);

  const runEstimate = useCallback(async () => {
    setEstimate(null);
    setGasPrice(null);
    if (!signer || !txData) return;
    
    setLoading(true);
    try {
      const provider = signer.provider as ethers.Provider;
      const gas = await provider.estimateGas({
        to: txData.to,
        data: txData.data,
        value: txData.value ? ethers.parseUnits(txData.value, 'ether') : undefined
      });
      const price = await provider.getFeeData();
      setEstimate(gas);
      setGasPrice(price.gasPrice || price.maxFeePerGas || null);
    } catch (err) {
      console.warn('Gas estimate failed', err);
      setEstimate(null);
      setGasPrice(null);
    } finally {
      setLoading(false);
    }
  }, [signer, txData]);

  useEffect(() => { 
    runEstimate(); 
  }, [runEstimate]);

  const gasCost = useMemo(() => {
    if (!estimate || !gasPrice) return null;
    return estimate * gasPrice;
  }, [estimate, gasPrice]);

  const usdEst = useMemo(() => {
    // Naive conversion would require CRO price feed - leave undefined for now
    return null;
  }, [gasCost]);

  if (!txData) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Gas Estimate</CardTitle>
          <CardDescription>No transaction data to estimate</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Gas Estimate</CardTitle>
        <CardDescription>Estimated gas cost for this transaction</CardDescription>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-1/2" />
          </div>
        ) : (
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">Gas units:</span>
              <strong className="font-mono text-sm">{estimate?.toString() ?? '—'}</strong>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">Gas price (gwei):</span>
              <strong className="font-mono text-sm">
                {gasPrice ? ethers.formatUnits(gasPrice, 'gwei') : '—'}
              </strong>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">Total cost (CRO):</span>
              <strong className="font-mono text-sm">
                {gasCost ? ethers.formatEther(gasCost) : '—'}
              </strong>
            </div>
            {usdEst && (
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Approx. USD:</span>
                <strong className="font-mono text-sm">{usdEst}</strong>
              </div>
            )}
          </div>
        )}
        <div className="mt-4">
          <Button 
            onClick={runEstimate} 
            variant="outline" 
            size="sm" 
            disabled={loading}
          >
            Refresh Estimate
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}


