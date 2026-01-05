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

  const initializeFromWindow = useCallback(async (ethereum: any) => {
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
      const bal = await bProvider.getBalance(address);
      setBalance(ethers.formatUnits(bal, 18));
    } catch (e) {
      console.error("initializeFromWindow failed", e);
    }
  }, []);

  const connect = useCallback(async () => {
    if (!(window as any)?.ethereum) {
      throw new Error("No wallet found. Please install MetaMask.");
    }
    setConnecting(true);
    try {
      await (window as any).ethereum.request({ method: "eth_requestAccounts" });
      await initializeFromWindow((window as any).ethereum);

      // Try to switch to Cronos
      try {
        await (window as any).ethereum.request({
          method: "wallet_switchEthereumChain",
          params: [{ chainId: CRONOS_MAINNET.chainIdHex }],
        });
      } catch (switchError: any) {
        if (switchError?.code === 4902) {
          await (window as any).ethereum.request({
            method: "wallet_addEthereumChain",
            params: [{
              chainId: CRONOS_MAINNET.chainIdHex,
              chainName: CRONOS_MAINNET.chainName,
              rpcUrls: CRONOS_MAINNET.rpcUrls,
              nativeCurrency: CRONOS_MAINNET.nativeCurrency,
              blockExplorerUrls: CRONOS_MAINNET.blockExplorerUrls
            }],
          });
        }
      }
      localStorage.setItem(LOCAL_KEY, "1");
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
      if (localStorage.getItem(LOCAL_KEY) && (window as any)?.ethereum) {
        try {
          await initializeFromWindow((window as any).ethereum);
        } catch (e) {
          localStorage.removeItem(LOCAL_KEY);
        }
      }
    };
    tryAuto();

    const ethereum = (window as any)?.ethereum;
    if (ethereum?.on) {
      const handleAccountsChanged = (accounts: string[]) => {
        if (!accounts.length) disconnect();
        else setAccount(accounts[0]);
      };
      const handleChainChanged = () => window.location.reload();
      ethereum.on("accountsChanged", handleAccountsChanged);
      ethereum.on("chainChanged", handleChainChanged);
      return () => {
        ethereum.removeListener?.("accountsChanged", handleAccountsChanged);
        ethereum.removeListener?.("chainChanged", handleChainChanged);
      };
    }
  }, [initializeFromWindow, disconnect]);

  return (
    <WalletContext.Provider value={{ provider, signer, account, chainId, balance, connecting, connect, disconnect, shorten }}>
      {children}
    </WalletContext.Provider>
  );
}
