import React, { createContext, useContext, useEffect, useState, useCallback, ReactNode } from "react";
import { ethers, BrowserProvider, Signer } from "ethers";

interface WalletContextType {
  provider: BrowserProvider | null;
  signer: Signer | null;
  account: string | null;
  chainId: bigint | null;
  balance: string | null;
  connecting: boolean;
  connect: () => Promise<void>;
  disconnect: () => void;
  shorten: (addr: string | null) => string;
}

const WalletContext = createContext<WalletContextType | null>(null);
export const useWallet = () => {
  const ctx = useContext(WalletContext);
  if (!ctx) throw new Error("useWallet must be used within WalletProvider");
  return ctx;
};

const LOCAL_KEY = "wallet_connected_v1";

export const CRONOS_MAINNET = {
  chainIdDecimal: 25,
  chainIdHex: "0x19",
  chainName: "Cronos Mainnet",
  rpcUrls: ["https://evm.cronos.org"],
  nativeCurrency: { name: "CRO", symbol: "CRO", decimals: 18 },
  blockExplorerUrls: ["https://cronoscan.com/"],
};

export function WalletProvider({ children }: { children: ReactNode }) {
  const [provider, setProvider] = useState<BrowserProvider | null>(null);
  const [signer, setSigner] = useState<Signer | null>(null);
  const [account, setAccount] = useState<string | null>(null);
  const [chainId, setChainId] = useState<bigint | null>(null);
  const [balance, setBalance] = useState<string | null>(null);
  const [connecting, setConnecting] = useState(false);

  const shorten = (addr: string | null) => {
    if (!addr) return "";
    return addr.slice(0, 6) + "..." + addr.slice(-4);
  };

  const fetchBalance = useCallback(async (bProvider: BrowserProvider, address: string) => {
    try {
      const bal = await bProvider.getBalance(address);
      setBalance(ethers.formatUnits(bal, 18));
    } catch (e) {
      console.error("Failed to fetch balance", e);
      setBalance(null);
    }
  }, []);

  const initializeFromWindow = useCallback(async (ethereum: typeof window.ethereum) => {
    if (!ethereum) return;
    try {
      const bProvider = new ethers.BrowserProvider(ethereum);
      setProvider(bProvider);
      const s = await bProvider.getSigner();
      setSigner(s);
      const address = await s.getAddress();
      setAccount(address);
      const net = await bProvider.getNetwork();
      setChainId(net.chainId);
      await fetchBalance(bProvider, address);
    } catch (e) {
      console.error("initializeFromWindow failed", e);
      // Don't throw here, just log - let the connect function handle errors
    }
  }, [fetchBalance]);

  const connect = useCallback(async () => {
    if (!window.ethereum) {
      throw new Error("No wallet found. Please install MetaMask or another Web3 wallet.");
    }
    setConnecting(true);
    try {
      // Request account access
      await window.ethereum.request({ method: "eth_requestAccounts" });
      
      // Try to switch to Cronos first (before initializing)
      try {
        await window.ethereum.request({
          method: "wallet_switchEthereumChain",
          params: [{ chainId: CRONOS_MAINNET.chainIdHex }],
        });
      } catch (switchError: any) {
        // This error code indicates that the chain has not been added to MetaMask
        if (switchError?.code === 4902) {
          try {
            await window.ethereum.request({
              method: "wallet_addEthereumChain",
              params: [{
                chainId: CRONOS_MAINNET.chainIdHex,
                chainName: CRONOS_MAINNET.chainName,
                rpcUrls: CRONOS_MAINNET.rpcUrls,
                nativeCurrency: CRONOS_MAINNET.nativeCurrency,
                blockExplorerUrls: CRONOS_MAINNET.blockExplorerUrls
              }],
            });
          } catch (addError) {
            console.error("Failed to add Cronos chain", addError);
            throw new Error("Failed to add Cronos network to wallet");
          }
        } else if (switchError?.code === 4001) {
          // User rejected the request
          throw new Error("Please switch to Cronos network to continue");
        } else {
          console.error("Failed to switch to Cronos", switchError);
          // Continue anyway - user might want to use a different chain
        }
      }
      
      // Initialize provider after chain switch
      await initializeFromWindow(window.ethereum);
      
      localStorage.setItem(LOCAL_KEY, "1");
    } catch (error: any) {
      console.error("Wallet connection failed", error);
      // Re-throw with a user-friendly message
      if (error?.message) {
        throw error;
      }
      throw new Error("Failed to connect wallet. Please try again.");
    } finally {
      setConnecting(false);
    }
  }, [initializeFromWindow]);

  const disconnect = useCallback(() => {
    setProvider(null);
    setSigner(null);
    setAccount(null);
    setBalance(null);
    setChainId(null);
    localStorage.removeItem(LOCAL_KEY);
  }, []);

  useEffect(() => {
    const tryAuto = async () => {
      if (localStorage.getItem(LOCAL_KEY) && window.ethereum) {
        try {
          // Check if we have permission to access accounts
          const accounts = await window.ethereum.request({ method: "eth_accounts" });
          if (accounts && accounts.length > 0) {
            await initializeFromWindow(window.ethereum);
          } else {
            // No accounts available, clear the stored connection
            localStorage.removeItem(LOCAL_KEY);
          }
        } catch (e) {
          console.error("Auto-connect failed", e);
          localStorage.removeItem(LOCAL_KEY);
        }
      }
    };
    tryAuto();

    const ethereum = window.ethereum;
    if (ethereum?.on) {
      const handleAccountsChanged = async (accounts: string[]) => {
        if (!accounts.length) {
          disconnect();
        } else {
          // Account changed, update account and refresh balance
          setAccount(accounts[0]);
          if (provider) {
            const address = accounts[0];
            await fetchBalance(provider, address);
          } else if (window.ethereum) {
            // Re-initialize if provider is not set
            await initializeFromWindow(window.ethereum);
          }
        }
      };
      
      const handleChainChanged = async () => {
        // Chain changed, re-initialize to get new chain ID and balance
        if (window.ethereum) {
          await initializeFromWindow(window.ethereum);
        }
        // Optionally reload page for a clean state
        // window.location.reload();
      };
      
      ethereum.on("accountsChanged", handleAccountsChanged);
      ethereum.on("chainChanged", handleChainChanged);
      
      return () => {
        if (ethereum.removeListener) {
          ethereum.removeListener("accountsChanged", handleAccountsChanged);
          ethereum.removeListener("chainChanged", handleChainChanged);
        }
      };
    }
  }, [initializeFromWindow, disconnect, provider, fetchBalance]);

  return (
    <WalletContext.Provider value={{ provider, signer, account, chainId, balance, connecting, connect, disconnect, shorten }}>
      {children}
    </WalletContext.Provider>
  );
}
