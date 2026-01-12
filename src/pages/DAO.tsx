import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, Vote, FileText, CheckCircle, XCircle, Clock, Users, Coins } from 'lucide-react';
import { api, ApiClientError, type DAOInfo, type Proposal, type VotingPower } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

const PROPOSAL_STATUS = {
  0: { label: 'Pending', color: 'bg-gray-500' },
  1: { label: 'Active', color: 'bg-blue-500' },
  2: { label: 'Defeated', color: 'bg-red-500' },
  3: { label: 'Succeeded', color: 'bg-green-500' },
  4: { label: 'Executed', color: 'bg-purple-500' },
  5: { label: 'Cancelled', color: 'bg-gray-400' },
};

const PROPOSAL_TYPE = {
  0: 'Treasury ETH Transfer',
  1: 'Treasury ERC20 Transfer',
  2: 'Arbitrary Call',
};

export default function DAO() {
  const { toast } = useToast();
  const [daoInfo, setDaoInfo] = useState<DAOInfo | null>(null);
  const [votingPower, setVotingPower] = useState<VotingPower | null>(null);
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [userAddress, setUserAddress] = useState('');
  const [privateKey, setPrivateKey] = useState('');

  // Proposal creation form
  const [proposalType, setProposalType] = useState<'eth_transfer' | 'erc20_transfer' | 'arbitrary_call'>('eth_transfer');
  const [recipient, setRecipient] = useState('');
  const [amount, setAmount] = useState('');
  const [description, setDescription] = useState('');
  const [creating, setCreating] = useState(false);

  // Voting
  const [votingProposalId, setVotingProposalId] = useState<number | null>(null);
  const [voteSupport, setVoteSupport] = useState<0 | 1 | 2>(1);
  const [voting, setVoting] = useState(false);

  useEffect(() => {
    loadDAOData();
  }, []);

  const loadDAOData = async () => {
    try {
      setError(null);
      const info = await api.getDAOInfo();
      setDaoInfo(info);
      
      // Load recent proposals (you'd need to implement a list endpoint or track IDs)
      // For now, we'll just show the info
    } catch (err) {
      const errorMessage = err instanceof ApiClientError 
        ? err.message 
        : 'Failed to load DAO information';
      console.error('Failed to load DAO data:', err);
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const loadVotingPower = async () => {
    if (!userAddress) return;
    
    try {
      const power = await api.getVotingPower(userAddress);
      setVotingPower(power);
    } catch (err) {
      toast({
        title: 'Error',
        description: err instanceof ApiClientError ? err.message : 'Failed to load voting power',
        variant: 'destructive',
      });
    }
  };

  const handleCreateProposal = async () => {
    if (!privateKey || !recipient || !amount || !description) {
      toast({
        title: 'Error',
        description: 'Please fill in all required fields',
        variant: 'destructive',
      });
      return;
    }

    setCreating(true);
    try {
      const result = await api.createProposal({
        proposal_type: proposalType,
        recipient: proposalType === 'eth_transfer' ? recipient : undefined,
        amount,
        description,
        private_key: privateKey,
      });

      toast({
        title: 'Success',
        description: `Proposal created! TX: ${result.tx_hash.substring(0, 10)}...`,
      });

      // Reset form
      setRecipient('');
      setAmount('');
      setDescription('');
      
      // Reload data
      if (result.proposal_id) {
        loadProposal(result.proposal_id);
      }
    } catch (err) {
      toast({
        title: 'Error',
        description: err instanceof ApiClientError ? err.message : 'Failed to create proposal',
        variant: 'destructive',
      });
    } finally {
      setCreating(false);
    }
  };

  const handleVote = async (proposalId: number) => {
    if (!privateKey) {
      toast({
        title: 'Error',
        description: 'Private key required for voting',
        variant: 'destructive',
      });
      return;
    }

    setVoting(true);
    try {
      const result = await api.voteOnProposal({
        proposal_id: proposalId,
        support: voteSupport,
        private_key: privateKey,
      });

      toast({
        title: 'Success',
        description: `Vote cast! TX: ${result.tx_hash.substring(0, 10)}...`,
      });

      // Reload proposal
      loadProposal(proposalId);
    } catch (err) {
      toast({
        title: 'Error',
        description: err instanceof ApiClientError ? err.message : 'Failed to vote',
        variant: 'destructive',
      });
    } finally {
      setVoting(false);
    }
  };

  const loadProposal = async (proposalId: number) => {
    try {
      const proposal = await api.getProposal(proposalId);
      setProposals(prev => {
        const existing = prev.findIndex(p => p.id === proposalId);
        if (existing >= 0) {
          const updated = [...prev];
          updated[existing] = proposal;
          return updated;
        }
        return [...prev, proposal];
      });
    } catch (err) {
      toast({
        title: 'Error',
        description: err instanceof ApiClientError ? err.message : 'Failed to load proposal',
        variant: 'destructive',
      });
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto p-6">
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">DAO Governance</h1>
          <p className="text-muted-foreground mt-1">Manage proposals and vote on treasury actions</p>
        </div>
      </div>

      {/* DAO Info */}
      {daoInfo && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Users className="h-4 w-4" />
                Governance
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Quorum:</span>
                  <span className="text-sm font-medium">{daoInfo.quorum_percentage}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Voting Period:</span>
                  <span className="text-sm font-medium">
                    {Math.floor(daoInfo.voting_period_seconds / (24 * 60 * 60))} days
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <FileText className="h-4 w-4" />
                Proposal Threshold
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {parseFloat(daoInfo.proposal_threshold) / 1e18} CLEO
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Coins className="h-4 w-4" />
                Treasury
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-xs text-muted-foreground font-mono">
                {daoInfo.treasury_address.substring(0, 10)}...
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Voting Power */}
      <Card>
        <CardHeader>
          <CardTitle>Check Voting Power</CardTitle>
          <CardDescription>Enter your address to check your voting power</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Input
              placeholder="0x..."
              value={userAddress}
              onChange={(e) => setUserAddress(e.target.value)}
            />
            <Button onClick={loadVotingPower}>Check</Button>
          </div>
          {votingPower && (
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Balance:</span>
                <span className="text-sm font-medium">
                  {parseFloat(votingPower.balance) / 1e18} CLEO
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Can Propose:</span>
                <Badge variant={votingPower.can_propose ? 'default' : 'secondary'}>
                  {votingPower.can_propose ? 'Yes' : 'No'}
                </Badge>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Tabs defaultValue="proposals" className="space-y-4">
        <TabsList>
          <TabsTrigger value="proposals">Proposals</TabsTrigger>
          <TabsTrigger value="create">Create Proposal</TabsTrigger>
          <TabsTrigger value="vote">Vote</TabsTrigger>
        </TabsList>

        <TabsContent value="proposals" className="space-y-4">
          {proposals.length === 0 ? (
            <Card>
              <CardContent className="py-8 text-center text-muted-foreground">
                No proposals loaded. Enter a proposal ID to view it.
              </CardContent>
            </Card>
          ) : (
            proposals.map((proposal) => (
              <Card key={proposal.id}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle>Proposal #{proposal.id}</CardTitle>
                    <Badge className={PROPOSAL_STATUS[proposal.status as keyof typeof PROPOSAL_STATUS]?.color}>
                      {PROPOSAL_STATUS[proposal.status as keyof typeof PROPOSAL_STATUS]?.label}
                    </Badge>
                  </div>
                  <CardDescription>{proposal.description}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <div className="text-sm text-muted-foreground">For</div>
                      <div className="text-lg font-semibold">
                        {parseFloat(proposal.for_votes) / 1e18} CLEO
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">Against</div>
                      <div className="text-lg font-semibold">
                        {parseFloat(proposal.against_votes) / 1e18} CLEO
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">Abstain</div>
                      <div className="text-lg font-semibold">
                        {parseFloat(proposal.abstain_votes) / 1e18} CLEO
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">Type</div>
                      <div className="text-sm font-medium">
                        {PROPOSAL_TYPE[proposal.proposal_type as keyof typeof PROPOSAL_TYPE]}
                      </div>
                    </div>
                  </div>
                  {proposal.status === 3 && (
                    <Button
                      onClick={async () => {
                        if (!privateKey) {
                          toast({
                            title: 'Error',
                            description: 'Private key required',
                            variant: 'destructive',
                          });
                          return;
                        }
                        try {
                          const result = await api.executeProposal({
                            proposal_id: proposal.id,
                            private_key: privateKey,
                          });
                          toast({
                            title: 'Success',
                            description: `Proposal executed! TX: ${result.tx_hash.substring(0, 10)}...`,
                          });
                          loadProposal(proposal.id);
                        } catch (err) {
                          toast({
                            title: 'Error',
                            description: err instanceof ApiClientError ? err.message : 'Failed to execute',
                            variant: 'destructive',
                          });
                        }
                      }}
                    >
                      Execute Proposal
                    </Button>
                  )}
                </CardContent>
              </Card>
            ))
          )}
          <Card>
            <CardHeader>
              <CardTitle>Load Proposal</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-2">
                <Input
                  type="number"
                  placeholder="Proposal ID"
                  onChange={(e) => {
                    const id = parseInt(e.target.value);
                    if (id) loadProposal(id);
                  }}
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="create" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Create Proposal</CardTitle>
              <CardDescription>Create a new DAO proposal</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Private Key (for signing)</Label>
                <Input
                  type="password"
                  value={privateKey}
                  onChange={(e) => setPrivateKey(e.target.value)}
                  placeholder="0x..."
                />
              </div>
              <div className="space-y-2">
                <Label>Proposal Type</Label>
                <Select value={proposalType} onValueChange={(v: any) => setProposalType(v)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="eth_transfer">Treasury ETH Transfer</SelectItem>
                    <SelectItem value="erc20_transfer">Treasury ERC20 Transfer</SelectItem>
                    <SelectItem value="arbitrary_call">Arbitrary Call</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Recipient Address</Label>
                <Input
                  value={recipient}
                  onChange={(e) => setRecipient(e.target.value)}
                  placeholder="0x..."
                />
              </div>
              <div className="space-y-2">
                <Label>Amount (wei)</Label>
                <Input
                  type="text"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  placeholder="1000000000000000000"
                />
              </div>
              <div className="space-y-2">
                <Label>Description</Label>
                <Textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Describe your proposal..."
                  rows={4}
                />
              </div>
              <Button onClick={handleCreateProposal} disabled={creating}>
                {creating && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Create Proposal
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="vote" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Vote on Proposal</CardTitle>
              <CardDescription>Cast your vote on an active proposal</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Private Key (for signing)</Label>
                <Input
                  type="password"
                  value={privateKey}
                  onChange={(e) => setPrivateKey(e.target.value)}
                  placeholder="0x..."
                />
              </div>
              <div className="space-y-2">
                <Label>Proposal ID</Label>
                <Input
                  type="number"
                  value={votingProposalId || ''}
                  onChange={(e) => setVotingProposalId(parseInt(e.target.value) || null)}
                  placeholder="1"
                />
              </div>
              <div className="space-y-2">
                <Label>Vote</Label>
                <Select
                  value={voteSupport.toString()}
                  onValueChange={(v) => setVoteSupport(parseInt(v) as 0 | 1 | 2)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="1">For</SelectItem>
                    <SelectItem value="0">Against</SelectItem>
                    <SelectItem value="2">Abstain</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <Button
                onClick={() => votingProposalId && handleVote(votingProposalId)}
                disabled={!votingProposalId || voting}
              >
                {voting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Cast Vote
              </Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
