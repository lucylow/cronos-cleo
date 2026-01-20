import React from 'react';
import { explorerAddressUrl, explorerTxUrl } from '../lib/utils';
import { Button } from './ui/button';
import { ExternalLink } from 'lucide-react';

export function ExplorerLinkAddress({ address, className }: { address: string; className?: string }) {
  if (!address) return null;
  
  return (
    <Button
      variant="ghost"
      size="sm"
      className={className}
      asChild
    >
      <a 
        href={explorerAddressUrl('cronos', address)} 
        target="_blank" 
        rel="noreferrer"
        className="inline-flex items-center gap-1"
      >
        <span className="text-xs">View on Explorer</span>
        <ExternalLink size={12} />
      </a>
    </Button>
  );
}

export function ExplorerLinkTx({ tx, className }: { tx: string; className?: string }) {
  if (!tx) return null;
  
  return (
    <Button
      variant="ghost"
      size="sm"
      className={className}
      asChild
    >
      <a 
        href={explorerTxUrl('cronos', tx)} 
        target="_blank" 
        rel="noreferrer"
        className="inline-flex items-center gap-1"
      >
        <span className="text-xs">View TX</span>
        <ExternalLink size={12} />
      </a>
    </Button>
  );
}

// Main ExplorerLink component that accepts address and chainId
export function ExplorerLink({ address, chainId, className }: { address: string; chainId?: bigint | number; className?: string }) {
  if (!address) return null;
  
  const chain = chainId === BigInt(25) || chainId === 25 ? 'cronos' : 'cronos'; // Default to cronos
  
  return (
    <Button
      variant="ghost"
      size="sm"
      className={className}
      asChild
    >
      <a 
        href={explorerAddressUrl(chain, address)} 
        target="_blank" 
        rel="noreferrer"
        className="inline-flex items-center gap-1"
      >
        <span className="text-xs">View on Explorer</span>
        <ExternalLink size={12} />
      </a>
    </Button>
  );
}

