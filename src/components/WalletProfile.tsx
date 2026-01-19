import React from 'react';
import { useWagmiWallet } from '../hooks/useWagmiWallet';
import { Copy, LogOut } from 'lucide-react';
import { copyToClipboard } from '../lib/utils';
import { Button } from './ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';
import { toast } from 'sonner';

export default function WalletProfile() {
  const { info, disconnect, switchToChain } = useWagmiWallet();

  const handleCopy = () => {
    if (info.address) {
      copyToClipboard(info.address);
      toast.success('Address copied to clipboard');
    }
  };

  const handleDisconnect = () => {
    disconnect();
    toast.success('Wallet disconnected');
  };

  if (!info.isConnected) {
    return null;
  }

  return (
    <div className="flex items-center gap-3">
      <div className="hidden sm:flex flex-col items-end text-sm">
        <div className="font-medium">{info.displayName ?? '—'}</div>
        <div className="text-xs text-muted-foreground">{info.nativeBalance ?? '—'}</div>
      </div>
      <div className="flex items-center gap-2 bg-slate-50 p-1 rounded">
        <Select
          value={String(info.chainId ?? 25)}
          onValueChange={(val) => {
            const id = Number(val);
            switchToChain(id).catch((err) => {
              toast.error(err?.message || 'Failed to switch network');
            });
          }}
        >
          <SelectTrigger className="w-[120px] h-8 text-sm bg-transparent border-0">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="25">Cronos</SelectItem>
            <SelectItem value="1">Ethereum</SelectItem>
          </SelectContent>
        </Select>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleCopy}
          className="h-8 w-8 p-0"
          title="Copy address"
        >
          <Copy size={14} />
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleDisconnect}
          className="h-8 px-2"
        >
          <LogOut size={14} className="mr-1" />
          <span className="hidden sm:inline">Disconnect</span>
        </Button>
      </div>
    </div>
  );
}

