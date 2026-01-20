import { ethers } from 'ethers';
import { NFT_ABI } from '@/lib/nftAbi';
import { getNftContractAddress } from '@/lib/nftConstants';
import { formatUnits, parseUnits } from 'viem';

export interface NFTMetadata {
  name?: string;
  description?: string;
  image?: string;
  attributes?: Array<{
    trait_type: string;
    value: string | number;
  }>;
}

export interface NFTInfo {
  tokenId: number;
  owner: string;
  tokenURI: string;
  metadata?: NFTMetadata;
}

export interface NFTCollectionInfo {
  name: string;
  symbol: string;
  totalSupply: bigint;
  maxSupply: bigint;
  mintPrice: bigint;
  mintPriceFormatted: string;
  maxPerWallet: bigint;
  publicMintEnabled: boolean;
  contractAddress: string;
}

export class NFTService {
  private provider: ethers.Provider | null = null;
  private signer: ethers.Signer | null = null;
  private contract: ethers.Contract | null = null;
  private chainId: number;

  constructor(provider: ethers.Provider | null, signer: ethers.Signer | null, chainId: number) {
    this.provider = provider;
    this.signer = signer;
    this.chainId = chainId;

    const contractAddress = getNftContractAddress(chainId);
    if (contractAddress && (signer || provider)) {
      this.contract = new ethers.Contract(
        contractAddress,
        NFT_ABI,
        signer || provider
      );
    }
  }

  /**
   * Get collection information
   */
  async getCollectionInfo(): Promise<NFTCollectionInfo | null> {
    if (!this.contract) return null;

    try {
      const [
        name,
        symbol,
        totalSupply,
        maxSupply,
        mintPrice,
        maxPerWallet,
        publicMintEnabled,
      ] = await Promise.all([
        this.contract.name(),
        this.contract.symbol(),
        this.contract.totalSupply(),
        this.contract.maxSupply(),
        this.contract.mintPrice(),
        this.contract.maxPerWallet(),
        this.contract.publicMintEnabled(),
      ]);

      return {
        name,
        symbol,
        totalSupply,
        maxSupply,
        mintPrice,
        mintPriceFormatted: formatUnits(mintPrice, 18),
        maxPerWallet,
        publicMintEnabled,
        contractAddress: getNftContractAddress(this.chainId),
      };
    } catch (error) {
      console.error('Error fetching collection info:', error);
      return null;
    }
  }

  /**
   * Get user's minted count
   */
  async getMintedByWallet(address: string): Promise<bigint> {
    if (!this.contract || !address) return 0n;

    try {
      return await this.contract.mintedByWallet(address);
    } catch (error) {
      console.error('Error fetching minted count:', error);
      return 0n;
    }
  }

  /**
   * Get user's balance (owned NFTs count)
   */
  async getBalance(address: string): Promise<bigint> {
    if (!this.contract || !address) return 0n;

    try {
      return await this.contract.balanceOf(address);
    } catch (error) {
      console.error('Error fetching balance:', error);
      return 0n;
    }
  }

  /**
   * Get all token IDs owned by an address
   */
  async getOwnedTokenIds(address: string): Promise<bigint[]> {
    if (!this.contract || !address) return [];

    try {
      const balance = await this.getBalance(address);
      const tokenIds: bigint[] = [];

      for (let i = 0; i < Number(balance); i++) {
        try {
          const tokenId = await this.contract.tokenOfOwnerByIndex(address, i);
          tokenIds.push(tokenId);
        } catch (error) {
          console.error(`Error fetching token at index ${i}:`, error);
        }
      }

      return tokenIds;
    } catch (error) {
      console.error('Error fetching owned token IDs:', error);
      return [];
    }
  }

  /**
   * Get token URI
   */
  async getTokenURI(tokenId: bigint): Promise<string> {
    if (!this.contract) return '';

    try {
      return await this.contract.tokenURI(tokenId);
    } catch (error) {
      console.error(`Error fetching token URI for ${tokenId}:`, error);
      return '';
    }
  }

  /**
   * Fetch metadata from URI
   */
  async fetchMetadata(uri: string): Promise<NFTMetadata | null> {
    if (!uri) return null;

    try {
      // Handle IPFS URIs
      let fetchUrl = uri;
      if (uri.startsWith('ipfs://')) {
        const ipfsHash = uri.replace('ipfs://', '');
        fetchUrl = `https://ipfs.io/ipfs/${ipfsHash}`;
      }

      const response = await fetch(fetchUrl);
      if (!response.ok) {
        throw new Error(`Failed to fetch metadata: ${response.statusText}`);
      }

      const metadata: NFTMetadata = await response.json();
      return metadata;
    } catch (error) {
      console.error('Error fetching metadata:', error);
      return null;
    }
  }

  /**
   * Get NFT info including metadata
   */
  async getNFTInfo(tokenId: bigint): Promise<NFTInfo | null> {
    if (!this.contract) return null;

    try {
      const [owner, tokenURI] = await Promise.all([
        this.contract.ownerOf(tokenId),
        this.getTokenURI(tokenId),
      ]);

      const metadata = tokenURI ? await this.fetchMetadata(tokenURI) : null;

      return {
        tokenId: Number(tokenId),
        owner,
        tokenURI,
        metadata,
      };
    } catch (error) {
      console.error(`Error fetching NFT info for ${tokenId}:`, error);
      return null;
    }
  }

  /**
   * Mint NFTs
   */
  async mint(quantity: number): Promise<ethers.ContractTransactionResponse> {
    if (!this.contract || !this.signer) {
      throw new Error('Contract or signer not available');
    }

    try {
      const collectionInfo = await this.getCollectionInfo();
      if (!collectionInfo) {
        throw new Error('Failed to fetch collection info');
      }

      if (!collectionInfo.publicMintEnabled) {
        throw new Error('Public minting is not enabled');
      }

      const totalPrice = collectionInfo.mintPrice * BigInt(quantity);
      const tx = await this.contract.mint(quantity, { value: totalPrice });

      return tx;
    } catch (error) {
      console.error('Error minting NFT:', error);
      throw error;
    }
  }

  /**
   * Check if user can mint
   */
  async canMint(address: string, quantity: number): Promise<{
    canMint: boolean;
    reason?: string;
    remainingMints?: number;
  }> {
    if (!this.contract || !address) {
      return { canMint: false, reason: 'Contract or address not available' };
    }

    try {
      const collectionInfo = await this.getCollectionInfo();
      if (!collectionInfo) {
        return { canMint: false, reason: 'Failed to fetch collection info' };
      }

      if (!collectionInfo.publicMintEnabled) {
        return { canMint: false, reason: 'Public minting is not enabled' };
      }

      const minted = await this.getMintedByWallet(address);
      const remainingMints = Number(collectionInfo.maxPerWallet) - Number(minted);

      if (collectionInfo.maxPerWallet > 0n && Number(minted) + quantity > Number(collectionInfo.maxPerWallet)) {
        return {
          canMint: false,
          reason: `Exceeds wallet limit. You can mint ${remainingMints} more.`,
          remainingMints: Math.max(0, remainingMints),
        };
      }

      const totalSupply = await this.contract.totalSupply();
      if (totalSupply + BigInt(quantity) > collectionInfo.maxSupply) {
        return {
          canMint: false,
          reason: 'Would exceed max supply',
        };
      }

      return { canMint: true, remainingMints };
    } catch (error) {
      console.error('Error checking mint eligibility:', error);
      return { canMint: false, reason: 'Error checking eligibility' };
    }
  }

  /**
   * Get all NFTs owned by an address with metadata
   */
  async getOwnedNFTs(address: string): Promise<NFTInfo[]> {
    if (!this.contract || !address) return [];

    try {
      const tokenIds = await this.getOwnedTokenIds(address);
      const nftInfos = await Promise.all(
        tokenIds.map((tokenId) => this.getNFTInfo(tokenId))
      );

      return nftInfos.filter((info): info is NFTInfo => info !== null);
    } catch (error) {
      console.error('Error fetching owned NFTs:', error);
      return [];
    }
  }
}


