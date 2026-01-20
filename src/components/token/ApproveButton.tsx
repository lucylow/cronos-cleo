import React, { useCallback, useEffect, useState } from 'react';
import { ethers } from 'ethers';
import type { TokenMeta } from '../../lib/mock-data';
import { useWagmiWallet } from '../../hooks/useWagmiWallet';
import { Button } from '../ui/button';
import { toast } from 'sonner';

const ERC20_ABI = [
  'function allowance(address owner, address spender) view returns (uint256)',
  'function approve(address spender, uint256 amount) returns (bool)',
  'function decimals() view returns (uint8)'
];

export default function ApproveButton({ token, spender }: { token: TokenMeta; spender: string }) {
  const { signer, info } = useWagmiWallet();
  const [allowance, setAllowance] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [checking, setChecking] = useState(true);
  const [decimals, setDecimals] = useState<number>(token.decimals || 18);

  const getAllowance = useCallback(async () => {
    if (!signer || !info.address || token.isNative) {
      setAllowance(null);
      setChecking(false);
      return;
    }
    
    try {
      setChecking(true);
      const owner = info.address;
      const provider = signer.provider || 
        new ethers.JsonRpcProvider(import.meta.env.VITE_CRO_RPC || 'https://evm-cronos.crypto.org');
      const contract = new ethers.Contract(token.address, ERC20_ABI, provider);
      
      const [raw, dec] = await Promise.all([
        contract.allowance(owner, spender),
        contract.decimals().catch(() => token.decimals || 18)
      ]);
      
      setDecimals(dec);
      setAllowance(raw.toString());
    } catch (err) {
      console.error('Error checking allowance:', err);
      setAllowance(null);
    } finally {
      setChecking(false);
    }
  }, [signer, token, spender, info.address]);

  useEffect(() => { 
    getAllowance(); 
  }, [getAllowance]);

  const handleApprove = useCallback(async () => {
    if (!signer || !info.address) {
      toast.error('Connect wallet first');
      return;
    }
    
    setLoading(true);
    try {
      const contract = new ethers.Contract(token.address, ERC20_ABI, signer);
      // Approve large amount (infinite) - prefer a safe cap in production
      const amount = ethers.MaxUint256; // Infinite approval
      const tx = await contract.approve(spender, amount);
      toast.info('Approval transaction submitted...');
      await tx.wait();
      await getAllowance();
      toast.success('Token approved successfully');
    } catch (err: any) {
      console.error('Approve error:', err);
      const message = err?.message ?? 'Approve failed';
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }, [signer, token, spender, decimals, getAllowance, info.address]);

  if (token.isNative) return null;
  
  if (checking) {
    return (
      <Button variant="outline" size="sm" disabled className="h-7 text-xs">
        Checking...
      </Button>
    );
  }

  const hasAllowance = allowance && BigInt(allowance) > 0n;

  return (
    <Button
      onClick={handleApprove}
      disabled={loading}
      variant={hasAllowance ? "outline" : "default"}
      size="sm"
      className="h-7 text-xs"
    >
      {loading ? 'Approving…' : hasAllowance ? 'Approved' : 'Approve'}
    </Button>
  );
}


