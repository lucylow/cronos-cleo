import React from 'react';
import { useTxSubmit } from '../hooks/useTxSubmit';
import { explorerTxUrl } from '../lib/utils';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { ExternalLink, Copy } from 'lucide-react';
import { copyToClipboard } from '../lib/utils';
import { toast } from 'sonner';

export default function TxHistory() {
  const { history } = useTxSubmit();
  
  if (!history || history.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Transaction History</CardTitle>
          <CardDescription>No transactions yet</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const handleCopy = (txHash: string) => {
    copyToClipboard(txHash);
    toast.success('Transaction hash copied');
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Transaction History</CardTitle>
        <CardDescription>Your recent transactions</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {history.slice().reverse().map((h: any) => (
            <div 
              key={h.txHash} 
              className="p-3 bg-muted/50 border rounded-lg flex justify-between items-center hover:bg-muted/70 transition-colors"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-mono text-xs truncate">{h.txHash}</span>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 w-6 p-0"
                    onClick={() => handleCopy(h.txHash)}
                  >
                    <Copy size={12} />
                  </Button>
                </div>
                <div className="text-xs text-muted-foreground">
                  {new Date(h.ts).toLocaleString()}
                </div>
                {h.meta?.kind && (
                  <div className="text-xs text-muted-foreground mt-1">
                    {h.meta.kind}
                  </div>
                )}
              </div>
              <div className="flex items-center gap-2">
                <Badge 
                  variant={
                    h.status === 'success' ? 'default' : 
                    h.status === 'pending' ? 'secondary' : 
                    'destructive'
                  }
                >
                  {h.status}
                </Badge>
                {h.txHash && !h.txHash.startsWith('failed_') && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8 p-0"
                    asChild
                  >
                    <a 
                      href={explorerTxUrl('cronos', h.txHash)} 
                      target="_blank" 
                      rel="noreferrer"
                    >
                      <ExternalLink size={14} />
                    </a>
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

