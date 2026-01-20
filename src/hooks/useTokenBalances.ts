import { useCallback, useEffect, useState } from 'react';
import { ethers } from 'ethers';
import type { TokenMeta } from '../lib/mock-data';
import { FIXTURES } from '../lib/mock-data';
import { useWagmiWallet } from './useWagmiWallet';

const ERC20_ABI = [
  'function balanceOf(address owner) view returns (uint256)',
  'function decimals() view returns (uint8)',
  'function symbol() view returns (string)'
];

type TokenBalance = { 
  token: TokenMeta; 
  balance: string | null; 
  raw?: string | null; 
  loading: boolean; 
  error?: string | null 
};

export function useTokenBalances(tokens: TokenMeta[] = FIXTURES.tokens) {
  const { signer, info } = useWagmiWallet();
  const [balances, setBalances] = useState<TokenBalance[]>(() => 
    tokens.map(t => ({ token: t, balance: null, raw: null, loading: true }))
  );

  const refresh = useCallback(async () => {
    if (!info.address) {
      setBalances(tokens.map(t => ({ token: t, balance: null, loading: false })));
      return;
    }

    setBalances(tokens.map(t => ({ token: t, balance: null, loading: true })));
    try {
      const provider = signer?.provider || 
        new ethers.JsonRpcProvider(import.meta.env.VITE_CRO_RPC || 'https://evm-cronos.crypto.org');
      
      const results: TokenBalance[] = [];
      
      for (const t of tokens) {
        try {
          if (t.isNative) {
            const raw = await provider.getBalance(info.address);
            const fmt = ethers.formatUnits(raw, t.decimals);
            results.push({ 
              token: t, 
              balance: String(Number(fmt).toFixed(6)), 
              raw: raw.toString(), 
              loading: false 
            });
          } else {
            const contract = new ethers.Contract(t.address, ERC20_ABI, provider);
            const decimals = (t.decimals ?? (await contract.decimals?.().catch(() => 18)));
            const raw = await contract.balanceOf(info.address);
            const fmt = ethers.formatUnits(raw, decimals);
            results.push({ 
              token: t, 
              balance: String(Number(fmt).toFixed(6)), 
              raw: raw.toString(), 
              loading: false 
            });
          }
        } catch (err: any) {
          results.push({ 
            token: t, 
            balance: null, 
            loading: false, 
            error: err?.message ?? String(err) 
          });
        }
      }
      setBalances(results);
    } catch (e) {
      setBalances(tokens.map(t => ({ 
        token: t, 
        balance: null, 
        loading: false, 
        error: (e as any).message 
      })));
    }
  }, [signer, tokens, info.address]);

  useEffect(() => { 
    refresh(); 
  }, [refresh]);

  return { balances, refresh };
}


