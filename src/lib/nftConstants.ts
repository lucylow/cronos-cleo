// NFT Contract Addresses
// These should be set via environment variables or updated after deployment
export const NFT_CONTRACTS = {
  // Cronos Testnet
  testnet: import.meta.env.VITE_NFT_CONTRACT_ADDRESS_TESTNET || '',
  // Cronos Mainnet
  mainnet: import.meta.env.VITE_NFT_CONTRACT_ADDRESS_MAINNET || '',
} as const;

// Default NFT contract address (will use based on network)
export const getNftContractAddress = (chainId: number): string => {
  if (chainId === 338) {
    // Cronos Testnet
    return NFT_CONTRACTS.testnet;
  } else if (chainId === 25) {
    // Cronos Mainnet
    return NFT_CONTRACTS.mainnet;
  }
  return NFT_CONTRACTS.testnet; // Default to testnet
};

// Default NFT collection metadata
export const NFT_COLLECTION_INFO = {
  name: 'CLEO Hackathon NFT',
  symbol: 'CLEO',
  description: 'C.L.E.O. Hackathon Achievement NFT Collection',
  defaultImage: '/placeholder.svg',
} as const;

