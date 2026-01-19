import { useCallback, useMemo, useState, useEffect } from 'react';
import { useAccount, useDisconnect, useEnsName, useBalance, useChainId, useSwitchChain } from 'wagmi';
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
  const { switchChain } = useSwitchChain();
  const [signer, setSigner] = useState<ethers.Signer | null>(null);

  // Get ethers signer from window.ethereum when account is connected
  useEffect(() => {
    const getSigner = async () => {
      if (!account.isConnected || !window.ethereum) {
        setSigner(null);
        return;
      }
      
      try {
        const provider = new ethers.BrowserProvider(window.ethereum);
        const s = await provider.getSigner();
        setSigner(s);
      } catch (error) {
        console.error('Failed to get signer:', error);
        setSigner(null);
      }
    };

    getSigner();
  }, [account.isConnected, account.address]);

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
    // For now, this triggers the wallet connection via wagmi injected connector
    // Users can connect via the existing WalletProvider or wagmi's injected connector
    console.log('Open wallet modal - use existing wallet connection flow');
  }, []);

  const switchToChain = useCallback(async (targetChainId: number) => {
    if (!switchChain) throw new Error('switchChain not available');
    switchChain({ chainId: targetChainId });
  }, [switchChain]);

  return { info, openModal, disconnect, switchToChain, signer };
}
