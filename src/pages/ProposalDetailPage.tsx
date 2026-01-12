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
import { useState } from 'react';
import { format } from 'date-fns';
import { parseEther } from 'viem';
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

  const { writeContract, data: txHash, isPending, error } = useWriteContract();
  const { isLoading: waiting, isSuccess } = useWaitForTransactionReceipt({
    hash: txHash,
  });

  const [errorMessage, setErrorMessage] = useState<string | null>(null);

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
  ] = proposal as any[];

  const supportLabels = ['Against', 'For', 'Abstain'];

  const handleVote = (support: 0 | 1 | 2) => {
    setErrorMessage(null);
    writeContract(
      {
        address: daoAddress as `0x${string}`,
        abi: DAO_ABI,
        functionName: 'vote',
        args: [proposalId, support],
      },
      {
        onSuccess: () => {
          toast.success('Vote submitted!');
        },
        onError: (err) => {
          setErrorMessage(err.message);
          toast.error('Vote failed: ' + err.message);
        },
      },
    );
  };

  const handleExecute = () => {
    setErrorMessage(null);
    writeContract(
      {
        address: daoAddress as `0x${string}`,
        abi: DAO_ABI,
        functionName: 'execute',
        args: [proposalId],
      },
      {
        onSuccess: () => {
          toast.success('Proposal executed!');
        },
        onError: (err) => {
          setErrorMessage(err.message);
          toast.error('Execution failed: ' + err.message);
        },
      },
    );
  };

  const handleFinalize = () => {
    setErrorMessage(null);
    writeContract(
      {
        address: daoAddress as `0x${string}`,
        abi: DAO_ABI,
        functionName: 'finalizeProposal',
        args: [proposalId],
      },
      {
        onSuccess: () => {
          toast.success('Proposal finalized!');
        },
        onError: (err) => {
          setErrorMessage(err.message);
          toast.error('Finalization failed: ' + err.message);
        },
      },
    );
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
            {(errorMessage || error) && (
              <p className="text-xs text-destructive">
                {errorMessage || error?.message}
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
