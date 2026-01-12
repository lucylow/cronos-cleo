/**
 * React hook for polling gas price recommendations from backend
 */
import { useEffect, useState } from 'react';
import { getGasRecommendation, type GasRecommendation } from '../lib/api';

export interface UseGasOptions {
  interval?: number; // Polling interval in milliseconds (default 10000)
  enabled?: boolean; // Whether to enable polling (default true)
}

export interface UseGasReturn {
  gas: GasRecommendation | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useGas(options: UseGasOptions = {}): UseGasReturn {
  const { interval = 10000, enabled = true } = options;
  const [gas, setGas] = useState<GasRecommendation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchGas = async () => {
    try {
      setError(null);
      const data = await getGasRecommendation();
      setGas(data);
      setLoading(false);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch gas recommendation');
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!enabled) {
      setLoading(false);
      return;
    }

    // Fetch immediately
    fetchGas();

    // Set up polling interval
    const handle = setInterval(fetchGas, interval);

    return () => {
      clearInterval(handle);
    };
  }, [interval, enabled]);

  return {
    gas,
    loading,
    error,
    refetch: fetchGas,
  };
}
