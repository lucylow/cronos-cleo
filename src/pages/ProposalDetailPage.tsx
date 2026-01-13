'use client';

import { useParams, useNavigate } from 'react-router-dom';
import {
  useAccount,
  useWriteContract,
  useReadContract,
  useWaitForTransactionReceipt,
  useChainId,
} from 'wagmi';
import { DAO_ABI } from '@/lib/daoAbi';
import { DAO_ADDRESS_TESTNET, DAO_ADDRESS_MAINNET } from '@/lib/daoConstants';
import { useState, useEffect } from 'react';
import { format } from 'date-fns';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ArrowLeft } from 'lucide-react';
import { toast } from 'sonner';

function useDaoAddress() {
  const chainId = useChainId();
  return chainId === 25 ? DAO_ADDRESS_MAINNET : DAO_ADDRESS_TESTNET;
}

export default function ProposalDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const proposalId = BigInt(id || '0');
  const daoAddress = useDaoAddress();
  const { address } = useAccount();

  const { data: proposal, isLoading } = useReadContract({
    address: daoAddress as `0x${string}`,
    abi: DAO_ABI,
    functionName: 'getProposal',
    args: [proposalId],
  });

  const { data: hasVoted } = useReadContract({
    address: daoAddress as `0x${string}`,
    abi: DAO_ABI,
    functionName: 'hasVoted',
    args: [proposalId, address as `0x${string}`],
    query: {
      enabled: !!address,
    },
  });

  const { writeContract, data: txHash, isPending, error: writeError } = useWriteContract();
  const { isLoading: waiting, isSuccess } = useWaitForTransactionReceipt({
    hash: txHash,
  });

  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Handle write success
  useEffect(() => {
    if (isSuccess && txHash) {
      toast.success('Transaction confirmed!');
    }
  }, [isSuccess, txHash]);

  // Handle write error
  useEffect(() => {
    if (writeError) {
      setErrorMessage(writeError.message);
      toast.error('Transaction failed: ' + writeError.message);
    }
  }, [writeError]);

  if (isLoading) {
    return (
      <div className="container mx-auto py-10">
        <Card>
          <CardContent className="pt-6">
            <p className="text-center text-muted-foreground">Loading proposal...</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!proposal) {
    return (
      <div className="container mx-auto py-10">
        <Card>
          <CardContent className="pt-6">
            <p className="text-center text-muted-foreground">Proposal not found</p>
            <Button onClick={() => navigate('/dao')} className="mt-4">
              Back to Proposals
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Handle both array and object responses from contract
  const proposalData = proposal as unknown;
  let _id: bigint, proposer: string, startTime: bigint, endTime: bigint, forVotes: bigint, againstVotes: bigint, abstainVotes: bigint, status: number, pType: number, target: string, value: bigint, token: string, recipient: string, _callData: string, description: string;
  
  if (Array.isArray(proposalData)) {
    [_id, proposer, startTime, endTime, forVotes, againstVotes, abstainVotes, status, pType, target, value, token, recipient, _callData, description] = proposalData as [bigint, string, bigint, bigint, bigint, bigint, bigint, number, number, string, bigint, string, string, string, string];
  } else {
    const p = proposalData as { id: bigint; proposer: string; startTime: bigint; endTime: bigint; forVotes: bigint; againstVotes: bigint; abstainVotes: bigint; status: number; pType: number; target: string; value: bigint; token: string; recipient: string; callData: string; description: string };
    _id = p.id; proposer = p.proposer; startTime = p.startTime; endTime = p.endTime; forVotes = p.forVotes; againstVotes = p.againstVotes; abstainVotes = p.abstainVotes; status = p.status; pType = p.pType; target = p.target; value = p.value; token = p.token; recipient = p.recipient; _callData = p.callData; description = p.description;
  }

  const supportLabels = ['Against', 'For', 'Abstain'];

  // Use type assertion to work around wagmi's strict typing
  const writeContractTyped = writeContract as (config: unknown) => void;

  const handleVote = (support: 0 | 1 | 2) => {
    setErrorMessage(null);
    writeContractTyped({
      address: daoAddress as `0x${string}`,
      abi: DAO_ABI,
      functionName: 'vote',
      args: [proposalId, support],
    });
  };

  const handleExecute = () => {
    setErrorMessage(null);
    writeContractTyped({
      address: daoAddress as `0x${string}`,
      abi: DAO_ABI,
      functionName: 'execute',
      args: [proposalId],
    });
  };

  const handleFinalize = () => {
    setErrorMessage(null);
    writeContractTyped({
      address: daoAddress as `0x${string}`,
      abi: DAO_ABI,
      functionName: 'finalizeProposal',
      args: [proposalId],
    });
  };

  const now = Date.now();
  const end = Number(endTime) * 1000;
  const isActive = Number(status) === 1 && now < end;
  const isSucceeded = Number(status) === 3;
  const canExecute = isSucceeded && Number(status) !== 4;
  const canFinalize = isActive && now > end;

  return (
    <div className="container mx-auto py-10 space-y-6">
      <Button variant="ghost" onClick={() => navigate('/dao')} className="mb-4">
        <ArrowLeft className="w-4 h-4 mr-2" />
        Back to Proposals
      </Button>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-2xl">Proposal #{id}</CardTitle>
              <CardDescription className="mt-2">
                Proposer: {proposer?.slice(0, 6)}...{proposer?.slice(-4)} • Start:{' '}
                {format(new Date(Number(startTime) * 1000), 'yyyy-MM-dd HH:mm')} • End:{' '}
                {format(new Date(Number(endTime) * 1000), 'yyyy-MM-dd HH:mm')}
              </CardDescription>
            </div>
            <Badge variant={isActive ? 'default' : isSucceeded ? 'default' : 'secondary'}>
              {isActive ? 'Active' : isSucceeded ? 'Succeeded' : Number(status) === 4 ? 'Executed' : 'Ended'}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          <div>
            <h3 className="font-semibold mb-2">Description</h3>
            <p className="text-muted-foreground">{description || 'No description provided'}</p>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <Card>
              <CardContent className="pt-6">
                <p className="text-xs text-muted-foreground mb-1">For</p>
                <p className="text-green-500 font-semibold text-xl">{Number(forVotes).toLocaleString()}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <p className="text-xs text-muted-foreground mb-1">Against</p>
                <p className="text-red-500 font-semibold text-xl">{Number(againstVotes).toLocaleString()}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <p className="text-xs text-muted-foreground mb-1">Abstain</p>
                <p className="text-muted-foreground font-semibold text-xl">{Number(abstainVotes).toLocaleString()}</p>
              </CardContent>
            </Card>
          </div>

          <div className="space-y-3">
            <h3 className="font-semibold">Actions</h3>
            <div className="flex flex-wrap gap-2">
              {!hasVoted && isActive && address && (
                <>
                  {([0, 1, 2] as const).map((s) => (
                    <Button
                      key={s}
                      disabled={isPending || waiting}
                      onClick={() => handleVote(s)}
                      variant="outline"
                    >
                      Vote {supportLabels[s]}
                    </Button>
                  ))}
                </>
              )}
              {hasVoted && (
                <Badge variant="secondary">You have already voted</Badge>
              )}
              {canFinalize && (
                <Button
                  disabled={isPending || waiting || !address}
                  onClick={handleFinalize}
                  variant="outline"
                >
                  Finalize Proposal
                </Button>
              )}
              {canExecute && (
                <Button
                  disabled={isPending || waiting || !address}
                  onClick={handleExecute}
                  className="bg-gradient-primary"
                >
                  Execute Proposal
                </Button>
              )}
            </div>
            {txHash && (
              <p className="text-xs text-muted-foreground">
                Transaction: {txHash.slice(0, 10)}... (status: {waiting ? 'Confirming' : isSuccess ? 'Confirmed' : 'Sent'})
              </p>
            )}
            {(errorMessage || writeError) && (
              <p className="text-xs text-destructive">
                {errorMessage || writeError?.message}
              </p>
            )}
          </div>

          <div className="space-y-2 text-sm text-muted-foreground border-t pt-4">
            <p>Target: {target}</p>
            <p>Recipient: {recipient}</p>
            <p>
              Value: {Number(value) > 0 ? `${Number(value) / 1e18} CRO` : '0'}
            </p>
            <p>
              Type:{' '}
              {Number(pType) === 0
                ? 'Treasury ETH'
                : Number(pType) === 1
                ? 'Treasury ERC20'
                : 'Arbitrary Call'}
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}