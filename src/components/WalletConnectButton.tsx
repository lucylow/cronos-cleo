import React from 'react';
import { Wallet } from 'lucide-react';
import { useWagmiWallet } from '../hooks/useWagmiWallet';
import { Button } from './ui/button';

export default function WalletConnectButton({ className = '' }: { className?: string }) {
  const { info, openModal } = useWagmiWallet();
  
  if (info.isConnected) {
    return (
      <div className={`inline-flex items-center gap-2 px-3 py-1 rounded bg-slate-50 ${className}`}>
        <Wallet size={16} />
        <span className="text-sm">{info.displayName ?? 'Connected'}</span>
      </div>
    );
  }

  return (
    <Button onClick={openModal} className={className}>
      <Wallet className="h-4 w-4 mr-2" />
      <span>Connect Wallet</span>
    </Button>
  );
}


