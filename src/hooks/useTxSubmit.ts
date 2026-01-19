import { useCallback, useState } from 'react';
import type { ethers } from 'ethers';
import { explorerTxUrl } from '../lib/utils';

export function useTxSubmit() {
  const [pending, setPending] = useState<Record<string, any>>({});
  const [history, setHistory] = useState<any[]>(() => {
    try { 
      return JSON.parse(localStorage.getItem('cleo.tx.history') || '[]'); 
    } catch { 
      return []; 
    }
  });

  const submit = useCallback(async (
    txPromise: Promise<ethers.TransactionResponse>, 
    meta: Record<string, any> = {}
  ) => {
    try {
      const tx = await txPromise;
      const stub = { txHash: tx.hash, status: 'pending', ts: Date.now(), meta };
      setPending((p) => ({ ...p, [tx.hash]: stub }));
      
      // Save pending to history
      const h = [...history, stub].slice(-200);
      localStorage.setItem('cleo.tx.history', JSON.stringify(h));
      setHistory(h);

      const receipt = await tx.wait();
      const finished = { 
        txHash: tx.hash, 
        status: receipt?.status === 1 ? 'success' : 'reverted', 
        receipt, 
        ts: Date.now(), 
        meta 
      };
      
      // Update pending/history
      setPending((p) => { 
        const cp = { ...p }; 
        delete cp[tx.hash]; 
        return cp; 
      });
      
      const newHist = [...h.filter((hh: any) => hh.txHash !== tx.hash), finished].slice(-200);
      localStorage.setItem('cleo.tx.history', JSON.stringify(newHist));
      setHistory(newHist);
      
      return finished;
    } catch (err: any) {
      // Store a failed tx stub if possible
      const txHash = (err?.transactionHash || err?.txHash) ?? (`failed_${Date.now()}`);
      const failed = { 
        txHash, 
        status: 'failed', 
        error: err?.message ?? String(err), 
        ts: Date.now(), 
        meta 
      };
      const newHist = [...history, failed].slice(-200);
      localStorage.setItem('cleo.tx.history', JSON.stringify(newHist));
      setHistory(newHist);
      throw err;
    }
  }, [history]);

  const explorerLink = useCallback((txHash: string, chain = 'cronos') => 
    explorerTxUrl(chain, txHash), 
  []);

  return { pending, history, submit, explorerLink };
}

