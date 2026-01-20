/**
 * Hook for monitoring backend connection status
 * Features:
 * - Health check polling
 * - Connection state management
 * - Automatic reconnection detection
 */

import { useEffect, useState, useCallback, useRef, createContext, useContext, ReactNode } from 'react';
import { checkHealth } from '@/lib/api';

export interface ConnectionStatus {
  isConnected: boolean;
  isChecking: boolean;
  lastCheck: Date | null;
  lastConnected: Date | null;
  consecutiveFailures: number;
  latency?: number;
}

export interface UseConnectionStatusOptions {
  checkInterval?: number;
  timeout?: number;
  enabled?: boolean;
  onStatusChange?: (status: ConnectionStatus) => void;
}

const DEFAULT_CHECK_INTERVAL = 30000; // 30 seconds
const DEFAULT_TIMEOUT = 5000; // 5 seconds

export function useConnectionStatus(
  options: UseConnectionStatusOptions = {}
): ConnectionStatus & { checkConnection: () => Promise<void> } {
  const {
    checkInterval = DEFAULT_CHECK_INTERVAL,
    timeout = DEFAULT_TIMEOUT,
    enabled = true,
    onStatusChange,
  } = options;

  const [status, setStatus] = useState<ConnectionStatus>({
    isConnected: false,
    isChecking: false,
    lastCheck: null,
    lastConnected: null,
    consecutiveFailures: 0,
  });

  const checkTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const isMountedRef = useRef(true);

  const checkConnection = useCallback(async () => {
    if (!isMountedRef.current) return;

    setStatus((prev) => ({ ...prev, isChecking: true }));

    const startTime = Date.now();
    let isConnected = false;
    let latency: number | undefined;

    try {
      isConnected = await checkHealth({ timeout });
      latency = Date.now() - startTime;

      setStatus((prev) => {
        const newStatus: ConnectionStatus = {
          isConnected,
          isChecking: false,
          lastCheck: new Date(),
          lastConnected: isConnected ? new Date() : prev.lastConnected,
          consecutiveFailures: isConnected ? 0 : prev.consecutiveFailures + 1,
          latency,
        };

        if (onStatusChange) {
          onStatusChange(newStatus);
        }

        return newStatus;
      });
    } catch (error) {
      latency = Date.now() - startTime;
      setStatus((prev) => {
        const newStatus: ConnectionStatus = {
          isConnected: false,
          isChecking: false,
          lastCheck: new Date(),
          lastConnected: prev.lastConnected,
          consecutiveFailures: prev.consecutiveFailures + 1,
          latency,
        };

        if (onStatusChange) {
          onStatusChange(newStatus);
        }

        return newStatus;
      });
    }
  }, [timeout, onStatusChange]);

  useEffect(() => {
    isMountedRef.current = true;

    if (enabled) {
      // Initial check
      checkConnection();

      // Set up polling
      checkTimerRef.current = setInterval(() => {
        checkConnection();
      }, checkInterval);
    }

    return () => {
      isMountedRef.current = false;
      if (checkTimerRef.current) {
        clearInterval(checkTimerRef.current);
        checkTimerRef.current = null;
      }
    };
  }, [enabled, checkInterval, checkConnection]);

  return {
    ...status,
    checkConnection,
  };
}

// Context provider for global connection status

interface ConnectionStatusContextValue {
  status: ConnectionStatus;
  checkConnection: () => Promise<void>;
}

const ConnectionStatusContext = createContext<ConnectionStatusContextValue | null>(null);

export function ConnectionStatusProvider({ children }: { children: ReactNode }) {
  const connectionStatus = useConnectionStatus({
    checkInterval: 30000,
    timeout: 5000,
    enabled: true,
  });

  return (
    <ConnectionStatusContext.Provider
      value={{
        status: connectionStatus,
        checkConnection: connectionStatus.checkConnection,
      }}
    >
      {children}
    </ConnectionStatusContext.Provider>
  );
}

export function useConnectionStatusContext(): ConnectionStatusContextValue {
  const context = useContext(ConnectionStatusContext);
  if (!context) {
    throw new Error('useConnectionStatusContext must be used within ConnectionStatusProvider');
  }
  return context;
}
