/*
  wagmi-client-types.ts
  Type definitions for wagmi wallet connection info
*/

export interface WalletConnectionInfo {
  address: `0x${string}` | undefined;
  isConnected: boolean;
  chainId: number | undefined;
  displayName: string | null;
  ensName: string | null;
  nativeBalance: string | null;
}

