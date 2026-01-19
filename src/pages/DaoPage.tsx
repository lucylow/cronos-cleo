import { useAccount, useChainId, useReadContract } from 'wagmi';
import { DAO_ABI } from '@/lib/daoAbi';
import { DAO_ADDRESS_TESTNET, DAO_ADDRESS_MAINNET } from '@/lib/daoConstants';
import { useMemo, useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { formatDistanceToNow, isValid } from 'date-fns';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { AlertCircle, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';

function useDaoAddress() {
  const chainId = useChainId();
  
  try {
    if (chainId === 25) {
      return DAO_ADDRESS_MAINNET;
    } else if (chainId === 338 || chainId === 1) {
      // Cronos testnet (338) or if fallback needed
      return DAO_ADDRESS_TESTNET;
    } else {
      // Unknown chain, default to testnet but log warning
      console.warn(`Unsupported chain ID: ${chainId}, defaulting to testnet address`);
      return DAO_ADDRESS_TESTNET;
    }
  } catch (error) {
    console.error('Error determining DAO address:', error);
    return DAO_ADDRESS_TESTNET;
  }
}

export default function DaoPage() {
  const { address, isConnected } = useAccount();
  const chainId = useChainId();
  const daoAddress = useDaoAddress();
  const [error, setError] = useState<string | null>(null);

  const { 
    data: nextId, 
    error: nextIdError, 
    isLoading: isLoadingNextId,
    refetch: refetchNextId 
  } = useReadContract({
    address: daoAddress as `0x${string}`,
    abi: DAO_ABI,
    functionName: 'nextProposalId',
    query: {
      retry: 2,
      retryDelay: 1000,
    },
  });

  // Handle nextId error
  useEffect(() => {
    if (nextIdError) {
      const errorMessage = nextIdError.message || 'Failed to load proposal count';
      console.error('Error fetching nextProposalId:', nextIdError);
      
      // Provide more specific error messages
      if (errorMessage.includes('execution reverted')) {
        setError('Contract execution failed. Please check if you are connected to the correct network.');
      } else if (errorMessage.includes('network') || errorMessage.includes('fetch')) {
        setError('Network error. Please check your connection and try again.');
      } else if (errorMessage.includes('Invalid address')) {
        setError('Invalid DAO contract address. Please check your network configuration.');
      } else {
        setError(`Failed to load proposals: ${errorMessage}`);
      }
      
      toast.error('Failed to load DAO data', {
        description: errorMessage,
      });
    } else {
      setError(null);
    }
  }, [nextIdError]);

  // Validate daoAddress
  useEffect(() => {
    if (!daoAddress || !daoAddress.startsWith('0x')) {
      const errorMsg = 'Invalid DAO contract address configured for this network';
      setError(errorMsg);
      toast.error('Configuration Error', {
        description: errorMsg,
      });
    }
  }, [daoAddress]);

  // Validate chainId
  useEffect(() => {
    if (isConnected && chainId && chainId !== 25 && chainId !== 338 && chainId !== 1) {
      console.warn(`Warning: Connected to unsupported chain (${chainId}). Expected Cronos mainnet (25) or testnet (338).`);
    }
  }, [chainId, isConnected]);

  const proposalIds = useMemo(() => {
    if (!nextId) return [];
    
    try {
    const n = Number(nextId);
      
      // Validate the number
      if (isNaN(n) || n < 0 || !Number.isInteger(n)) {
        console.error('Invalid nextProposalId value:', nextId);
        setError('Invalid proposal count received from contract');
        return [];
      }
      
      // Limit to reasonable number to prevent performance issues
      const maxProposals = 1000;
      const safeN = Math.min(n, maxProposals);
      
      if (n > maxProposals) {
        console.warn(`Proposal count (${n}) exceeds maximum display limit (${maxProposals}). Showing first ${maxProposals} proposals.`);
      }
      
      return Array.from({ length: safeN }, (_, i) => safeN - 1 - i); // newest first
    } catch (err) {
      console.error('Error processing proposal IDs:', err);
      setError('Error processing proposal list');
      return [];
    }
  }, [nextId]);

  const handleRetry = () => {
    setError(null);
    refetchNextId();
  };

  // Show error state
  if (error && !isLoadingNextId) {
    return (
      <div className="container mx-auto py-10 space-y-6">
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Cronos DAO</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Connected: {address ? `${address.slice(0, 6)}...${address.slice(-4)}` : 'Not connected'} (Chain ID: {chainId})
            </p>
          </div>
        </header>

        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error Loading DAO</AlertTitle>
          <AlertDescription className="mt-2">
            {error}
            <div className="mt-4">
              <Button variant="outline" size="sm" onClick={handleRetry} className="mr-2">
                <RefreshCw className="w-4 h-4 mr-2" />
                Retry
              </Button>
              {chainId !== 25 && chainId !== 338 && (
                <p className="text-xs mt-2 text-muted-foreground">
                  Tip: Make sure you're connected to Cronos Mainnet (Chain ID: 25) or Testnet (Chain ID: 338)
                </p>
              )}
            </div>
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-10 space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Cronos DAO</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Connected: {address ? `${address.slice(0, 6)}...${address.slice(-4)}` : 'Not connected'} (Chain ID: {chainId})
            {chainId !== 25 && chainId !== 338 && chainId !== 1 && isConnected && (
              <span className="ml-2 text-yellow-600">⚠ Unsupported network</span>
            )}
          </p>
        </div>
        <Link to="/dao/create">
          <Button className="bg-gradient-primary" disabled={!isConnected || isLoadingNextId}>
            New Proposal
          </Button>
        </Link>
      </header>

      <section>
        <h2 className="text-xl font-semibold mb-4">Proposals</h2>
        
        {isLoadingNextId && (
          <Card>
            <CardContent className="pt-6">
              <p className="text-muted-foreground text-center">Loading proposals...</p>
            </CardContent>
          </Card>
        )}

        {!isLoadingNextId && proposalIds.length === 0 && !error && (
          <Card>
            <CardContent className="pt-6">
              <p className="text-muted-foreground text-center">No proposals yet.</p>
            </CardContent>
          </Card>
        )}

        {!isLoadingNextId && proposalIds.length > 0 && (
        <div className="space-y-3">
          {proposalIds.map((id) => (
            <ProposalRow key={id} id={BigInt(id)} daoAddress={daoAddress as `0x${string}`} />
          ))}
        </div>
        )}
      </section>
    </div>
  );
}

function ProposalRow({ id, daoAddress }: { id: bigint; daoAddress: `0x${string}` }) {
  const [parseError, setParseError] = useState<string | null>(null);
  
  const { 
    data, 
    error, 
    isLoading,
    refetch 
  } = useReadContract({
    address: daoAddress,
    abi: DAO_ABI,
    functionName: 'proposals',
    args: [id],
    query: {
      retry: 2,
      retryDelay: 1000,
    },
  });

  // Handle contract read errors
  useEffect(() => {
    if (error) {
      console.error(`Error loading proposal ${id.toString()}:`, error);
      const errorMessage = error.message || 'Failed to load proposal data';
      
      // Provide specific error messages
      if (errorMessage.includes('execution reverted')) {
        setParseError('Proposal not found or contract error');
      } else if (errorMessage.includes('network') || errorMessage.includes('fetch')) {
        setParseError('Network error');
      } else {
        setParseError('Failed to load');
      }
    } else {
      setParseError(null);
    }
  }, [error, id]);

  if (isLoading) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-muted-foreground">Loading proposal #{id.toString()}...</p>
        </CardContent>
      </Card>
    );
  }

  if (error || !data) {
    return (
      <Card className="border-destructive/50">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-destructive">
                Proposal #{id.toString()}
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                {parseError || 'Failed to load proposal data'}
              </p>
            </div>
            <Button variant="ghost" size="sm" onClick={() => refetch()}>
              <RefreshCw className="w-4 h-4" />
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Safely parse proposal data
  let proposer: string;
  let startTime: bigint;
  let endTime: bigint;
  let forVotes: bigint;
  let againstVotes: bigint;
  let abstainVotes: bigint;
  let status: number;
  let pType: number;
  let target: string;
  let value: bigint;
  let token: string;
  let recipient: string;
  let description: string;

  try {
  const dataArray = [...(data as readonly unknown[])] as unknown[];
    
    // Validate array length
    if (dataArray.length < 15) {
      throw new Error(`Invalid proposal data structure: expected 15 fields, got ${dataArray.length}`);
    }

    [
      , // _id - skip
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
      , // _callData - skip
    description,
  ] = dataArray as [bigint, string, bigint, bigint, bigint, bigint, bigint, number, number, string, bigint, string, string, string, string];

    // Validate required fields
    if (!proposer || typeof proposer !== 'string' || !proposer.startsWith('0x')) {
      throw new Error('Invalid proposer address');
    }
    
    if (!startTime || !endTime) {
      throw new Error('Invalid time fields');
    }
    
    if (typeof status !== 'number' || isNaN(status)) {
      throw new Error('Invalid status value');
    }
  } catch (parseErr: any) {
    console.error(`Error parsing proposal ${id.toString()} data:`, parseErr);
    setParseError(`Data parsing error: ${parseErr.message || 'Unknown error'}`);
    
    return (
      <Card className="border-destructive/50">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-destructive">
                Proposal #{id.toString()}
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                {parseError || 'Invalid proposal data'}
              </p>
            </div>
            <Button variant="ghost" size="sm" onClick={() => refetch()}>
              <RefreshCw className="w-4 h-4" />
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Safely calculate dates and status
  let statusLabel: string;
  let endDate: Date;
  let statusVariant: 'default' | 'secondary' | 'destructive' | 'outline' = 'default';
  let timeRemaining: string = '';

  try {
  const now = Date.now();
    const endTimestamp = Number(endTime) * 1000;
    const startTimestamp = Number(startTime) * 1000;
    
    // Validate timestamps
    if (isNaN(endTimestamp) || isNaN(startTimestamp)) {
      throw new Error('Invalid timestamp values');
    }
    
    endDate = new Date(endTimestamp);
    
    // Validate date
    if (!isValid(endDate)) {
      throw new Error('Invalid end date');
    }
    
    // Calculate status
    const statusNum = Number(status);
    if (statusNum === 1 && now < endTimestamp) {
      statusLabel = 'Active';
      statusVariant = 'default';
    } else if (statusNum === 4) {
      statusLabel = 'Executed';
      statusVariant = 'secondary';
    } else if (statusNum === 2) {
      statusLabel = 'Defeated';
      statusVariant = 'destructive';
    } else if (statusNum === 3) {
      statusLabel = 'Succeeded';
      statusVariant = 'default';
    } else {
      statusLabel = 'Pending';
      statusVariant = 'outline';
    }
    
    // Safely format time remaining
    try {
      timeRemaining = formatDistanceToNow(endDate, { addSuffix: true });
    } catch (dateErr) {
      console.warn(`Error formatting date for proposal ${id.toString()}:`, dateErr);
      timeRemaining = `Ends: ${endDate.toLocaleDateString()}`;
    }
  } catch (dateErr: any) {
    console.error(`Error processing dates for proposal ${id.toString()}:`, dateErr);
    statusLabel = 'Unknown';
    statusVariant = 'outline';
    endDate = new Date();
    timeRemaining = 'Date unavailable';
  }

  // Safely format vote counts
  const formatVotes = (votes: bigint): string => {
    try {
      const num = Number(votes);
      if (isNaN(num) || num < 0) {
        return '0';
      }
      return num.toLocaleString();
    } catch (err) {
      console.warn(`Error formatting votes for proposal ${id.toString()}:`, err);
      return '0';
    }
  };

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
              <p className="text-sm font-medium line-clamp-2">
                {description || 'No description'}
              </p>
              <p className="text-xs text-muted-foreground">
                Ends {timeRemaining}
              </p>
            </div>
            <div className="text-right text-xs space-y-1">
              <p className="text-green-500 font-semibold">
                For: {formatVotes(forVotes)}
              </p>
              <p className="text-red-500 font-semibold">
                Against: {formatVotes(againstVotes)}
              </p>
              <p className="text-muted-foreground">
                Abstain: {formatVotes(abstainVotes)}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
