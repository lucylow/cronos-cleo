import { useEffect, useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { 
  Loader2, 
  Sparkles, 
  Image as ImageIcon, 
  Plus, 
  Info, 
  ExternalLink,
  CheckCircle,
  XCircle,
  Wallet,
  AlertCircle,
} from 'lucide-react';
import { useAccount, useChainId, useBalance } from 'wagmi';
import { formatUnits, parseUnits } from 'viem';
import { useWagmiWallet } from '@/hooks/useWagmiWallet';
import { NFTService, type NFTCollectionInfo, type NFTInfo } from '@/services/nftService';
import { ethers } from 'ethers';
import { toast } from 'sonner';
import { ExplorerLink } from '@/components/ExplorerLink';
import { motion, AnimatePresence } from 'framer-motion';
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from '@/components/ui/tooltip';

export default function NFT() {
  const { address, isConnected } = useAccount();
  const chainId = useChainId();
  const { signer, info } = useWagmiWallet();
  const { data: balanceData } = useBalance({ address });

  const [nftService, setNftService] = useState<NFTService | null>(null);
  const [collectionInfo, setCollectionInfo] = useState<NFTCollectionInfo | null>(null);
  const [ownedNFTs, setOwnedNFTs] = useState<NFTInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mintQuantity, setMintQuantity] = useState(1);
  const [minting, setMinting] = useState(false);
  const [selectedNFT, setSelectedNFT] = useState<NFTInfo | null>(null);

  // Initialize NFT service
  useEffect(() => {
    if (signer && signer.provider) {
      const provider = signer.provider as ethers.Provider;
      const service = new NFTService(provider, signer, chainId);
      setNftService(service);
    } else if (window.ethereum) {
      const provider = new ethers.BrowserProvider(window.ethereum);
      const service = new NFTService(provider, null, chainId);
      setNftService(service);
    }
  }, [signer, chainId]);

  // Load collection info and user NFTs
  const loadNFTData = useCallback(async () => {
    if (!nftService) return;

    try {
      setError(null);
      setLoading(true);

      const [info, nfts] = await Promise.all([
        nftService.getCollectionInfo(),
        address ? nftService.getOwnedNFTs(address) : Promise.resolve([]),
      ]);

      setCollectionInfo(info);
      setOwnedNFTs(nfts);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load NFT data';
      console.error('Failed to load NFT data:', err);
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [nftService, address]);

  useEffect(() => {
    loadNFTData();
    // Refresh every 30 seconds
    const interval = setInterval(loadNFTData, 30000);
    return () => clearInterval(interval);
  }, [loadNFTData]);

  // Handle minting
  const handleMint = async () => {
    if (!nftService || !isConnected || !address) {
      toast.error('Please connect your wallet');
      return;
    }

    if (!collectionInfo) {
      toast.error('Collection information not available');
      return;
    }

    if (!collectionInfo.publicMintEnabled) {
      toast.error('Public minting is not enabled');
      return;
    }

    // Check if user can mint
    const canMintResult = await nftService.canMint(address, mintQuantity);
    if (!canMintResult.canMint) {
      toast.error(canMintResult.reason || 'Cannot mint');
      return;
    }

    // Check balance
    const totalPrice = collectionInfo.mintPrice * BigInt(mintQuantity);
    if (balanceData && balanceData.value < totalPrice) {
      toast.error('Insufficient balance for minting');
      return;
    }

    setMinting(true);
    try {
      const tx = await nftService.mint(mintQuantity);
      toast.success('Transaction submitted!', {
        description: 'Waiting for confirmation...',
      });

      const receipt = await tx.wait();
      toast.success('Minting successful!', {
        description: `Minted ${mintQuantity} NFT(s)`,
      });

      // Refresh data
      await loadNFTData();
    } catch (err: any) {
      const errorMessage = err?.reason || err?.message || 'Failed to mint NFT';
      console.error('Mint error:', err);
      toast.error('Minting failed', {
        description: errorMessage,
      });
    } finally {
      setMinting(false);
    }
  };

  const formatPrice = (price: bigint) => {
    return parseFloat(formatUnits(price, 18)).toFixed(4);
  };

  const supplyPercentage = collectionInfo
    ? (Number(collectionInfo.totalSupply) / Number(collectionInfo.maxSupply)) * 100
    : 0;

  if (loading && !collectionInfo) {
    return (
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-6 w-32" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-8 w-24" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  return (
    <TooltipProvider>
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-foreground mb-2 flex items-center gap-2">
              <Sparkles className="h-8 w-8 text-primary" />
              NFT Collection
            </h1>
            <p className="text-muted-foreground text-lg">
              {collectionInfo?.name || 'CLEO Hackathon NFT'} Collection
            </p>
          </div>
          {collectionInfo && (
            <Badge variant="outline" className="text-lg px-4 py-2">
              {collectionInfo.symbol}
            </Badge>
          )}
        </div>

        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {!collectionInfo && !loading && (
          <Alert>
            <Info className="h-4 w-4" />
            <AlertDescription>
              NFT contract not found. Please ensure the contract is deployed and the address is configured.
            </AlertDescription>
          </Alert>
        )}

        {collectionInfo && (
          <>
            {/* Collection Stats */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
              >
                <Card>
                  <CardHeader className="flex flex-row items-center justify-between pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">
                      Total Supply
                    </CardTitle>
                    <ImageIcon className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      {Number(collectionInfo.totalSupply).toLocaleString()} /{' '}
                      {Number(collectionInfo.maxSupply).toLocaleString()}
                    </div>
                    <div className="mt-2 h-2 bg-muted rounded-full overflow-hidden">
                      <div
                        className="h-full bg-primary transition-all duration-500"
                        style={{ width: `${supplyPercentage}%` }}
                      />
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {supplyPercentage.toFixed(1)}% minted
                    </p>
                  </CardContent>
                </Card>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
              >
                <Card>
                  <CardHeader className="flex flex-row items-center justify-between pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">
                      Mint Price
                    </CardTitle>
                    <Wallet className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      {formatPrice(collectionInfo.mintPrice)} CRO
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">Per NFT</p>
                  </CardContent>
                </Card>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
              >
                <Card>
                  <CardHeader className="flex flex-row items-center justify-between pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">
                      Max Per Wallet
                    </CardTitle>
                    <Info className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      {collectionInfo.maxPerWallet > 0n
                        ? Number(collectionInfo.maxPerWallet).toLocaleString()
                        : 'Unlimited'}
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">Mint limit</p>
                  </CardContent>
                </Card>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
              >
                <Card>
                  <CardHeader className="flex flex-row items-center justify-between pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">
                      Status
                    </CardTitle>
                    {collectionInfo.publicMintEnabled ? (
                      <CheckCircle className="h-4 w-4 text-green-500" />
                    ) : (
                      <XCircle className="h-4 w-4 text-red-500" />
                    )}
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      {collectionInfo.publicMintEnabled ? 'Live' : 'Paused'}
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">Mint status</p>
                  </CardContent>
                </Card>
              </motion.div>
            </div>

            {/* Main Content Tabs */}
            <Tabs defaultValue="mint" className="space-y-4">
              <TabsList>
                <TabsTrigger value="mint">Mint</TabsTrigger>
                <TabsTrigger value="gallery">My NFTs ({ownedNFTs.length})</TabsTrigger>
                <TabsTrigger value="collection">Collection Info</TabsTrigger>
              </TabsList>

              {/* Mint Tab */}
              <TabsContent value="mint" className="space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Plus className="h-5 w-5" />
                      Mint NFT
                    </CardTitle>
                    <CardDescription>
                      Mint NFTs from the {collectionInfo.name} collection
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {!isConnected ? (
                      <Alert>
                        <Wallet className="h-4 w-4" />
                        <AlertDescription>
                          Please connect your wallet to mint NFTs
                        </AlertDescription>
                      </Alert>
                    ) : !collectionInfo.publicMintEnabled ? (
                      <Alert variant="destructive">
                        <XCircle className="h-4 w-4" />
                        <AlertDescription>
                          Public minting is currently disabled
                        </AlertDescription>
                      </Alert>
                    ) : (
                      <>
                        <div className="space-y-2">
                          <Label htmlFor="quantity">Quantity</Label>
                          <div className="flex items-center gap-2">
                            <Button
                              variant="outline"
                              size="icon"
                              onClick={() => setMintQuantity(Math.max(1, mintQuantity - 1))}
                              disabled={mintQuantity <= 1 || minting}
                            >
                              -
                            </Button>
                            <Input
                              id="quantity"
                              type="number"
                              min={1}
                              max={10}
                              value={mintQuantity}
                              onChange={(e) => {
                                const value = parseInt(e.target.value) || 1;
                                setMintQuantity(Math.max(1, Math.min(10, value)));
                              }}
                              className="text-center w-20"
                              disabled={minting}
                            />
                            <Button
                              variant="outline"
                              size="icon"
                              onClick={() => setMintQuantity(Math.min(10, mintQuantity + 1))}
                              disabled={mintQuantity >= 10 || minting}
                            >
                              +
                            </Button>
                          </div>
                        </div>

                        <div className="p-4 bg-muted rounded-lg space-y-2">
                          <div className="flex justify-between text-sm">
                            <span className="text-muted-foreground">Price per NFT:</span>
                            <span className="font-medium">
                              {formatPrice(collectionInfo.mintPrice)} CRO
                            </span>
                          </div>
                          <div className="flex justify-between text-sm">
                            <span className="text-muted-foreground">Total Price:</span>
                            <span className="font-bold text-lg">
                              {formatPrice(collectionInfo.mintPrice * BigInt(mintQuantity))} CRO
                            </span>
                          </div>
                          {balanceData && (
                            <div className="flex justify-between text-sm pt-2 border-t">
                              <span className="text-muted-foreground">Your Balance:</span>
                              <span className="font-medium">
                                {parseFloat(formatUnits(balanceData.value, balanceData.decimals)).toFixed(4)}{' '}
                                {balanceData.symbol}
                              </span>
                            </div>
                          )}
                        </div>

                        <Button
                          onClick={handleMint}
                          disabled={minting || !isConnected}
                          className="w-full"
                          size="lg"
                        >
                          {minting ? (
                            <>
                              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                              Minting...
                            </>
                          ) : (
                            <>
                              <Plus className="mr-2 h-4 w-4" />
                              Mint {mintQuantity} NFT{mintQuantity > 1 ? 's' : ''}
                            </>
                          )}
                        </Button>
                      </>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>

              {/* Gallery Tab */}
              <TabsContent value="gallery" className="space-y-4">
                {!isConnected ? (
                  <Alert>
                    <Wallet className="h-4 w-4" />
                    <AlertDescription>
                      Please connect your wallet to view your NFTs
                    </AlertDescription>
                  </Alert>
                ) : ownedNFTs.length === 0 ? (
                  <Card>
                    <CardContent className="flex flex-col items-center justify-center py-12">
                      <ImageIcon className="h-16 w-16 text-muted-foreground/30 mb-4" />
                      <p className="text-lg font-medium text-muted-foreground">
                        No NFTs owned
                      </p>
                      <p className="text-sm text-muted-foreground mt-2">
                        Mint your first NFT to get started!
                      </p>
                    </CardContent>
                  </Card>
                ) : (
                  <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                    <AnimatePresence>
                      {ownedNFTs.map((nft, index) => (
                        <motion.div
                          key={nft.tokenId}
                          initial={{ opacity: 0, scale: 0.9 }}
                          animate={{ opacity: 1, scale: 1 }}
                          exit={{ opacity: 0, scale: 0.9 }}
                          transition={{ delay: index * 0.05 }}
                        >
                          <Card
                            className="cursor-pointer hover:border-primary transition-all duration-300 overflow-hidden group"
                            onClick={() => setSelectedNFT(nft)}
                          >
                            <div className="aspect-square bg-muted relative overflow-hidden">
                              {nft.metadata?.image ? (
                                <img
                                  src={nft.metadata.image}
                                  alt={nft.metadata.name || `NFT #${nft.tokenId}`}
                                  className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-300"
                                  onError={(e) => {
                                    const target = e.target as HTMLImageElement;
                                    target.src = '/placeholder.svg';
                                  }}
                                />
                              ) : (
                                <div className="w-full h-full flex items-center justify-center">
                                  <ImageIcon className="h-12 w-12 text-muted-foreground/30" />
                                </div>
                              )}
                              <div className="absolute top-2 right-2">
                                <Badge variant="secondary">#{nft.tokenId}</Badge>
                              </div>
                            </div>
                            <CardContent className="p-4">
                              <h3 className="font-semibold text-lg mb-1 truncate">
                                {nft.metadata?.name || `NFT #${nft.tokenId}`}
                              </h3>
                              {nft.metadata?.description && (
                                <p className="text-sm text-muted-foreground line-clamp-2 mb-2">
                                  {nft.metadata.description}
                                </p>
                              )}
                              <div className="flex items-center justify-between mt-2">
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        if (collectionInfo) {
                                          window.open(
                                            `https://${
                                              chainId === 338 ? 'testnet.' : ''
                                            }cronoscan.com/token/${collectionInfo.contractAddress}?a=${nft.tokenId}`,
                                            '_blank'
                                          );
                                        }
                                      }}
                                    >
                                      <ExternalLink className="h-4 w-4" />
                                    </Button>
                                  </TooltipTrigger>
                                  <TooltipContent>
                                    <p>View on Cronoscan</p>
                                  </TooltipContent>
                                </Tooltip>
                              </div>
                            </CardContent>
                          </Card>
                        </motion.div>
                      ))}
                    </AnimatePresence>
                  </div>
                )}
              </TabsContent>

              {/* Collection Info Tab */}
              <TabsContent value="collection" className="space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle>Collection Details</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid gap-4 md:grid-cols-2">
                      <div>
                        <Label className="text-muted-foreground">Name</Label>
                        <p className="text-lg font-semibold">{collectionInfo.name}</p>
                      </div>
                      <div>
                        <Label className="text-muted-foreground">Symbol</Label>
                        <p className="text-lg font-semibold">{collectionInfo.symbol}</p>
                      </div>
                      <div>
                        <Label className="text-muted-foreground">Contract Address</Label>
                        <div className="flex items-center gap-2">
                          <code className="text-sm font-mono bg-muted px-2 py-1 rounded">
                            {collectionInfo.contractAddress.slice(0, 10)}...
                            {collectionInfo.contractAddress.slice(-8)}
                          </code>
                          {collectionInfo.contractAddress && (
                            <ExplorerLink
                              address={collectionInfo.contractAddress}
                              chainId={chainId}
                            />
                          )}
                        </div>
                      </div>
                      <div>
                        <Label className="text-muted-foreground">Total Supply</Label>
                        <p className="text-lg font-semibold">
                          {Number(collectionInfo.totalSupply).toLocaleString()} /{' '}
                          {Number(collectionInfo.maxSupply).toLocaleString()}
                        </p>
                      </div>
                      <div>
                        <Label className="text-muted-foreground">Mint Price</Label>
                        <p className="text-lg font-semibold">
                          {formatPrice(collectionInfo.mintPrice)} CRO
                        </p>
                      </div>
                      <div>
                        <Label className="text-muted-foreground">Max Per Wallet</Label>
                        <p className="text-lg font-semibold">
                          {collectionInfo.maxPerWallet > 0n
                            ? Number(collectionInfo.maxPerWallet).toLocaleString()
                            : 'Unlimited'}
                        </p>
                      </div>
                      <div>
                        <Label className="text-muted-foreground">Public Mint Status</Label>
                        <Badge
                          variant={collectionInfo.publicMintEnabled ? 'default' : 'secondary'}
                          className={
                            collectionInfo.publicMintEnabled
                              ? 'bg-green-500'
                              : 'bg-red-500'
                          }
                        >
                          {collectionInfo.publicMintEnabled ? 'Enabled' : 'Disabled'}
                        </Badge>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          </>
        )}

        {/* NFT Detail Modal/Dialog */}
        {selectedNFT && (
          <Card className="fixed inset-4 z-50 overflow-auto bg-background border-2">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>
                {selectedNFT.metadata?.name || `NFT #${selectedNFT.tokenId}`}
              </CardTitle>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setSelectedNFT(null)}
              >
                <XCircle className="h-4 w-4" />
              </Button>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="aspect-square max-w-md mx-auto bg-muted rounded-lg overflow-hidden">
                {selectedNFT.metadata?.image ? (
                  <img
                    src={selectedNFT.metadata.image}
                    alt={selectedNFT.metadata.name || `NFT #${selectedNFT.tokenId}`}
                    className="w-full h-full object-cover"
                    onError={(e) => {
                      const target = e.target as HTMLImageElement;
                      target.src = '/placeholder.svg';
                    }}
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <ImageIcon className="h-24 w-24 text-muted-foreground/30" />
                  </div>
                )}
              </div>
              {selectedNFT.metadata?.description && (
                <p className="text-muted-foreground">{selectedNFT.metadata.description}</p>
              )}
              <div className="grid gap-2">
                <div>
                  <Label className="text-muted-foreground">Token ID</Label>
                  <p className="font-semibold">#{selectedNFT.tokenId}</p>
                </div>
                <div>
                  <Label className="text-muted-foreground">Owner</Label>
                  <code className="text-sm font-mono">{selectedNFT.owner}</code>
                </div>
                {selectedNFT.metadata?.attributes && (
                  <div>
                    <Label className="text-muted-foreground">Attributes</Label>
                    <div className="flex flex-wrap gap-2 mt-2">
                      {selectedNFT.metadata.attributes.map((attr, idx) => (
                        <Badge key={idx} variant="outline">
                          {attr.trait_type}: {attr.value}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </TooltipProvider>
  );
}

