'use client';

import { useState } from 'react';
import { useAccount, useWriteContract, useWaitForTransactionReceipt, useChainId } from 'wagmi';
import { DAO_ABI } from '@/lib/daoAbi';
import { DAO_ADDRESS_TESTNET, DAO_ADDRESS_MAINNET } from '@/lib/daoConstants';
import { parseEther, isAddress } from 'viem';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { ArrowLeft } from 'lucide-react';
import { toast } from 'sonner';

function useDaoAddress() {
  const chainId = useChainId();
  return chainId === 25 ? DAO_ADDRESS_MAINNET : DAO_ADDRESS_TESTNET;
}

export default function CreateProposalPage() {
  const { address } = useAccount();
  const daoAddress = useDaoAddress();
  const navigate = useNavigate();

  const [recipient, setRecipient] = useState('');
  const [amount, setAmount] = useState('');
  const [description, setDescription] = useState('');
  const [error, setError] = useState<string | null>(null);

  const { writeContract, data: txHash, isPending } = useWriteContract();
  const { isLoading: waiting, isSuccess } = useWaitForTransactionReceipt({
    hash: txHash,
    onSuccess: () => {
      toast.success('Proposal created successfully!');
      navigate('/dao');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!address) {
      setError('Connect wallet first.');
      toast.error('Please connect your wallet');
      return;
    }
    if (!recipient || !amount || !description) {
      setError('Fill all fields.');
      toast.error('Please fill all fields');
      return;
    }
    if (!isAddress(recipient)) {
      setError('Invalid recipient address.');
      toast.error('Invalid recipient address');
      return;
    }
    try {
      parseEther(amount);
    } catch {
      setError('Invalid amount.');
      toast.error('Invalid amount');
      return;
    }
    setError(null);

    writeContract(
      {
        address: daoAddress as `0x${string}`,
        abi: DAO_ABI,
        functionName: 'proposeTreasuryETHTransfer',
        args: [recipient as `0x${string}`, parseEther(amount), description],
      },
      {
        onError: (err) => {
          setError(err.message);
          toast.error('Proposal creation failed: ' + err.message);
        },
      },
    );
  };

  return (
    <div className="container mx-auto py-10">
      <Button variant="ghost" onClick={() => navigate('/dao')} className="mb-4">
        <ArrowLeft className="w-4 h-4 mr-2" />
        Back to Proposals
      </Button>

      <Card className="max-w-2xl mx-auto">
        <CardHeader>
          <CardTitle className="text-2xl">New Treasury ETH Proposal</CardTitle>
          <CardDescription>
            Create a proposal to transfer CRO from the DAO treasury
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="recipient">Recipient Address</Label>
              <Input
                id="recipient"
                value={recipient}
                onChange={(e) => setRecipient(e.target.value)}
                placeholder="0x..."
                className="font-mono"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="amount">Amount (CRO)</Label>
              <Input
                id="amount"
                type="number"
                min="0"
                step="0.000000000000000001"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="0.0"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                rows={4}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe what this proposal will do..."
              />
            </div>
            {error && (
              <p className="text-sm text-destructive">{error}</p>
            )}
            <Button
              type="submit"
              disabled={isPending || waiting || !address}
              className="w-full bg-gradient-primary"
            >
              {isPending || waiting ? 'Submitting...' : 'Submit Proposal'}
            </Button>
            {txHash && (
              <p className="text-xs text-muted-foreground text-center">
                Transaction: {txHash.slice(0, 10)}...
              </p>
            )}
            {!address && (
              <p className="text-sm text-muted-foreground text-center">
                Please connect your wallet to create a proposal
              </p>
            )}
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
