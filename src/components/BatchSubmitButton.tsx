import React, { useState } from 'react';
import { useWagmiWallet } from '../hooks/useWagmiWallet';
import { buildX402BatchData, submitX402Batch } from '../services/x402Service';
import { useTxSubmit } from '../hooks/useTxSubmit';
import { Button } from './ui/button';
import { toast } from 'sonner';
import type { TokenMeta } from '../lib/mock-data';

type Route = {
  dex: string;
  amountIn: number;
  estimatedOut?: number;
  minOut?: number;
  path: (string | TokenMeta)[];
};

export default function BatchSubmitButton({ 
  routes, 
  routerMap, 
  finalRecipient 
}: { 
  routes: Route[]; 
  routerMap: Record<string, string>; 
  finalRecipient?: string;
}) {
  const { signer, info } = useWagmiWallet();
  const { submit } = useTxSubmit();
  const [running, setRunning] = useState(false);

  const handleSubmit = async () => {
    if (!signer || !info.address) {
      toast.error('Connect wallet first');
      return;
    }

    const recipient = finalRecipient || info.address;
    
    try {
      setRunning(true);
      toast.info('Preparing batch transaction...');
      
      const { targets, data, condition } = buildX402BatchData(routes, routerMap, recipient);
      
      // Prepare contract call using x402Service
      const txPromise = submitX402Batch(signer, routes, routerMap, recipient);
      const receipt = await submit(txPromise, { 
        kind: 'x402-batch', 
        routesCount: routes.length 
      });
      
      toast.success(`Batch executed successfully! TX: ${receipt.txHash.slice(0, 10)}...`);
    } catch (err: any) {
      console.error('Batch submission error:', err);
      const message = err?.message ?? 'Batch submission failed';
      toast.error(message);
    } finally {
      setRunning(false);
    }
  };

  if (!info.isConnected) {
    return (
      <Button disabled variant="outline">
        Connect wallet to submit
      </Button>
    );
  }

  return (
    <Button 
      onClick={handleSubmit} 
      disabled={running || routes.length === 0} 
      className={running ? '' : 'bg-indigo-600 hover:bg-indigo-700'}
    >
      {running ? 'Submitting…' : `Submit x402 Batch (${routes.length} routes)`}
    </Button>
  );
}


