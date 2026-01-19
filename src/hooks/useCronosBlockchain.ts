/**
 * React hook for fetching Cronos blockchain-specific data
 * Includes block number, network status, validator info, and more
 */
import { useEffect, useState, useCallback } from 'react';
import { useChainId, usePublicClient } from 'wagmi';
import { formatUnits } from 'viem';

export interface CronosBlockchainData {
  currentBlock: number | null;
  blockTimestamp: number | null;
  networkId: number;
  chainId: number;
  isMainnet: boolean;
  isTestnet: boolean;
  networkName: string;
  explorerUrl: string;
  nativeCurrency: {
    name: string;
    symbol: string;
    decimals: number;
  };
  blockTime: number | null; // Average block time in seconds
  gasPrice: bigint | null;
  gasPriceGwei: string | null;
  lastBlockTime: number | null;
}

export interface UseCronosBlockchainOptions {
  enabled?: boolean;
  updateInterval?: number; // Polling interval in milliseconds (default 5000)
  trackBlockTime?: boolean; // Track block time calculations
}

export interface UseCronosBlockchainReturn {
  data: CronosBlockchainData | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
  isConnected: boolean;
}

const CRONOS_MAINNET_CHAIN_ID = 25;
const CRONOS_TESTNET_CHAIN_ID = 338;

const CRONOS_NETWORKS = {
  [CRONOS_MAINNET_CHAIN_ID]: {
    name: 'Cronos Mainnet',
    explorerUrl: 'https://cronoscan.com',
    nativeCurrency: {
      name: 'Cronos',
      symbol: 'CRO',
      decimals: 18,
    },
  },
  [CRONOS_TESTNET_CHAIN_ID]: {
    name: 'Cronos Testnet',
    explorerUrl: 'https://testnet.cronoscan.com',
    nativeCurrency: {
      name: 'Cronos Testnet',
      symbol: 'TCRO',
      decimals: 18,
    },
  },
};

export function useCronosBlockchain(
  options: UseCronosBlockchainOptions = {}
): UseCronosBlockchainReturn {
  const { enabled = true, updateInterval = 5000, trackBlockTime = true } = options;
  const chainId = useChainId();
  const publicClient = usePublicClient();
  const [data, setData] = useState<CronosBlockchainData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [blockHistory, setBlockHistory] = useState<Array<{ block: number; timestamp: number }>>([]);

  const isCronosNetwork = chainId === CRONOS_MAINNET_CHAIN_ID || chainId === CRONOS_TESTNET_CHAIN_ID;
  const networkConfig = CRONOS_NETWORKS[chainId as keyof typeof CRONOS_NETWORKS];

  const fetchBlockchainData = useCallback(async () => {
    if (!enabled || !publicClient || !isCronosNetwork) {
      setLoading(false);
      return;
    }

    try {
      setError(null);

      // Fetch current block number
      const blockNumber = await publicClient.getBlockNumber();

      // Fetch block details for timestamp
      const block = await publicClient.getBlock({ blockNumber });

      // Fetch gas price
      let gasPrice: bigint | null = null;
      try {
        gasPrice = await publicClient.getGasPrice();
      } catch (e) {
        console.warn('Failed to fetch gas price:', e);
      }

      // Calculate block time if tracking is enabled
      let blockTime: number | null = null;
      let lastBlockTime: number | null = null;

      if (trackBlockTime && blockHistory.length > 0) {
        const latestHistory = blockHistory[blockHistory.length - 1];
        if (blockNumber > latestHistory.block) {
          const timeDiff = Number(block.timestamp) - latestHistory.timestamp;
          const blockDiff = Number(blockNumber) - latestHistory.block;
          blockTime = blockDiff > 0 ? timeDiff / blockDiff : null;
          lastBlockTime = timeDiff;
        }
      }

      // Update block history (keep last 10 entries)
      setBlockHistory(prev => {
        const newEntry = { block: Number(blockNumber), timestamp: Number(block.timestamp) };
        return [...prev, newEntry].slice(-10);
      });

      // Get network ID (same as chain ID for Cronos)
      const networkId = chainId;

      const blockchainData: CronosBlockchainData = {
        currentBlock: Number(blockNumber),
        blockTimestamp: Number(block.timestamp),
        networkId,
        chainId,
        isMainnet: chainId === CRONOS_MAINNET_CHAIN_ID,
        isTestnet: chainId === CRONOS_TESTNET_CHAIN_ID,
        networkName: networkConfig?.name || 'Unknown Cronos Network',
        explorerUrl: networkConfig?.explorerUrl || 'https://cronoscan.com',
        nativeCurrency: networkConfig?.nativeCurrency || {
          name: 'CRO',
          symbol: 'CRO',
          decimals: 18,
        },
        blockTime,
        gasPrice,
        gasPriceGwei: gasPrice ? formatUnits(gasPrice, 'gwei') : null,
        lastBlockTime,
      };

      setData(blockchainData);
      setLoading(false);
    } catch (err: any) {
      console.error('Failed to fetch Cronos blockchain data:', err);
      setError(err.message || 'Failed to fetch blockchain data');
      setLoading(false);
    }
  }, [enabled, publicClient, isCronosNetwork, chainId, networkConfig, trackBlockTime, blockHistory]);

  useEffect(() => {
    if (!enabled || !isCronosNetwork) {
      setLoading(false);
      return;
    }

    // Fetch immediately
    fetchBlockchainData();

    // Set up polling interval
    const interval = setInterval(fetchBlockchainData, updateInterval);

    return () => {
      clearInterval(interval);
    };
  }, [enabled, isCronosNetwork, fetchBlockchainData, updateInterval]);

  return {
    data,
    loading,
    error,
    refetch: fetchBlockchainData,
    isConnected: isCronosNetwork && !!publicClient,
  };
}

