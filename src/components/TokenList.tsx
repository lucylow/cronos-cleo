import React from 'react';
import type { TokenMeta } from '../lib/mock-data';
import { useTokenBalances } from '../hooks/useTokenBalances';
import ApproveButton from './token/ApproveButton';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Skeleton } from './ui/skeleton';

export default function TokenList({ tokens }: { tokens?: TokenMeta[] }) {
  const tokenList = tokens ?? [];
  const { balances } = useTokenBalances(tokenList);

  if (balances.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Token Balances</CardTitle>
          <CardDescription>No tokens to display</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <div className="space-y-2">
      {balances.map((b) => (
        <Card key={b.token.address} className="border">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <div className="font-medium">{b.token.symbol}</div>
                <div className="text-xs text-muted-foreground">{b.token.name}</div>
              </div>
              <div className="text-right">
                {b.loading ? (
                  <Skeleton className="h-5 w-20" />
                ) : (
                  <div className="font-mono text-sm">{b.balance ?? '0'}</div>
                )}
                <div className="mt-1 flex gap-2 justify-end">
                  {!b.token.isNative && (
                    <ApproveButton 
                      token={b.token} 
                      spender={import.meta.env.VITE_X402_FACILITATOR || '0xFAC'} 
                    />
                  )}
                  <Button variant="outline" size="sm" className="h-7 text-xs">
                    Send
                  </Button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

