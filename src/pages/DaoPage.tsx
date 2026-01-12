'use client';

import { useAccount, useChainId, useReadContract } from 'wagmi';
import { DAO_ABI } from '@/lib/daoAbi';
import { DAO_ADDRESS_TESTNET, DAO_ADDRESS_MAINNET } from '@/lib/daoConstants';
import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { formatDistanceToNow } from 'date-fns';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

function useDaoAddress() {
  const chainId = useChainId();
  return chainId === 25 ? DAO_ADDRESS_MAINNET : DAO_ADDRESS_TESTNET;
}

export default function DaoPage() {
  const { address } = useAccount();
  const daoAddress = useDaoAddress();

  const { data: nextId } = useReadContract({
    address: daoAddress as `0x${string}`,
    abi: DAO_ABI,
    functionName: 'nextProposalId',
  });

  const proposalIds = useMemo(() => {
    if (!nextId) return [];
    const n = Number(nextId);
    return Array.from({ length: n }, (_, i) => n - 1 - i); // newest first
  }, [nextId]);

  return (
    <div className="container mx-auto py-10 space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Cronos DAO</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Connected: {address ? `${address.slice(0, 6)}...${address.slice(-4)}` : 'Not connected'} (Cronos EVM)
          </p>
        </div>
        <Link to="/dao/create">
          <Button className="bg-gradient-primary">
            New Proposal
          </Button>
        </Link>
      </header>

      <section>
        <h2 className="text-xl font-semibold mb-4">Proposals</h2>
        {proposalIds.length === 0 && (
          <Card>
            <CardContent className="pt-6">
              <p className="text-muted-foreground text-center">No proposals yet.</p>
            </CardContent>
          </Card>
        )}

        <div className="space-y-3">
          {proposalIds.map((id) => (
            <ProposalRow key={id} id={BigInt(id)} daoAddress={daoAddress as `0x${string}`} />
          ))}
        </div>
      </section>
    </div>
  );
}

function ProposalRow({ id, daoAddress }: { id: bigint; daoAddress: `0x${string}` }) {
  const { data } = useReadContract({
    address: daoAddress,
    abi: DAO_ABI,
    functionName: 'proposals',
    args: [id],
  });

  if (!data) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-muted-foreground">Loading proposal #{id.toString()}...</p>
        </CardContent>
      </Card>
    );
  }

  const [
    _id,
    proposer,
    startTime,
    endTime,
    forVotes,
    againstVotes,
    abstainVotes,
    status,
    pType,
    target,
    value,
    token,
    recipient,
    _callData,
    description,
  ] = data as any[];

  const now = Date.now();
  const end = Number(endTime) * 1000;
  const statusLabel =
    Number(status) === 1 && now < end
      ? 'Active'
      : Number(status) === 4
      ? 'Executed'
      : Number(status) === 2
      ? 'Defeated'
      : Number(status) === 3
      ? 'Succeeded'
      : 'Pending';

  const statusVariant = 
    statusLabel === 'Active' ? 'default' :
    statusLabel === 'Succeeded' ? 'default' :
    statusLabel === 'Executed' ? 'secondary' :
    'destructive';

  return (
    <Link to={`/dao/${id.toString()}`}>
      <Card className="hover:border-primary transition-colors cursor-pointer">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between gap-4">
            <div className="space-y-2 flex-1">
              <div className="flex items-center gap-2">
                <p className="text-sm text-muted-foreground">#{id.toString()}</p>
                <Badge variant={statusVariant}>{statusLabel}</Badge>
              </div>
              <p className="text-sm font-medium line-clamp-2">{description || 'No description'}</p>
              <p className="text-xs text-muted-foreground">
                Ends {formatDistanceToNow(new Date(end), { addSuffix: true })}
              </p>
            </div>
            <div className="text-right text-xs space-y-1">
              <p className="text-green-500 font-semibold">For: {Number(forVotes).toLocaleString()}</p>
              <p className="text-red-500 font-semibold">Against: {Number(againstVotes).toLocaleString()}</p>
              <p className="text-muted-foreground">Abstain: {Number(abstainVotes).toLocaleString()}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
