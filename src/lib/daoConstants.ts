// DAO contract addresses - Update these with your deployed addresses
export const DAO_ADDRESS_TESTNET = process.env.VITE_DAO_ADDRESS_TESTNET || '0x0000000000000000000000000000000000000000';
export const DAO_ADDRESS_MAINNET = process.env.VITE_DAO_ADDRESS_MAINNET || '0x0000000000000000000000000000000000000000';

// Helper hook to get the correct DAO address based on chain
export function useDaoAddress() {
  // This will be used in components with wagmi hooks
  return DAO_ADDRESS_TESTNET; // Default to testnet, will be overridden in components
}
