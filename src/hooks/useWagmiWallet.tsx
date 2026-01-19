import { useCallback, useMemo } from 'react';
import { useAccount, useDisconnect, useEnsName, useBalance, useChainId, useSwitchChain, useWalletClient } from 'wagmi';
import { ethers } from 'ethers';
import type { WalletConnectionInfo } from '../lib/wagmi-client-types';

export function useWagmiWallet(): {
  info: WalletConnectionInfo;
  openModal: () => void;
  disconnect: () => void;
  switchToChain: (chainId: number) => Promise<void>;
  signer: ethers.Signer | null;
} {
  const account = useAccount();
  const { disconnect } = useDisconnect();
  const { data: ens } = useEnsName({ address: account.address, query: { enabled: !!account.address } });
  const { data: balance } = useBalance({ address: account.address, query: { enabled: !!account.address } });
  const chainId = useChainId();
  const { data: walletClient } = useWalletClient();
  const { switchChain } = useSwitchChain();

  // Convert viem WalletClient to ethers Signer
  const signer = useMemo(() => {
    if (!walletClient) return null;
    // Use ethers adapter for viem
    const { BrowserProvider } = ethers;
    if (window.ethereum) {
      const provider = new BrowserProvider(window.ethereum);
      return provider.getSigner().catch(() => null);
    }
    return null;
  }, [walletClient]);

  const info: WalletConnectionInfo = useMemo(() => ({
    address: account.address,
    isConnected: account.isConnected,
    chainId: chainId,
    displayName: ens ?? (account.address ? `${account.address.slice(0, 6)}...${account.address.slice(-4)}` : null),
    ensName: ens ?? null,
    nativeBalance: balance ? `${Number(balance.formatted).toFixed(4)} ${balance.symbol}` : null
  }), [account.address, account.isConnected, ens, balance, chainId]);

  const openModal = useCallback(() => {
    // In a real implementation with Web3Modal, you'd open the modal here
    // For now, this is a placeholder - you may want to integrate with your existing WalletProvider
    console.log('Open wallet modal');
  }, []);

  const switchToChain = useCallback(async (targetChainId: number) => {
    if (!switchChain) throw new Error('switchChain not available');
    switchChain({ chainId: targetChainId });
  }, [switchChain]);

  return { info, openModal, disconnect, switchToChain, signer: null }; // Signer will be resolved asynchronously
}

