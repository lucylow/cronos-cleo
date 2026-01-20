/**
 * Connection Status Component
 * Displays backend connection status with visual indicators
 */

import { useConnectionStatus } from '@/hooks/useConnectionStatus';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from '@/components/ui/tooltip';
import { Wifi, WifiOff, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ConnectionStatusProps {
  className?: string;
  showLabel?: boolean;
  showLatency?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export function ConnectionStatus({
  className,
  showLabel = true,
  showLatency = false,
  size = 'md',
}: ConnectionStatusProps) {
  const status = useConnectionStatus({
    checkInterval: 30000,
    timeout: 5000,
    enabled: true,
  });

  const iconSize = {
    sm: 'h-3 w-3',
    md: 'h-4 w-4',
    lg: 'h-5 w-5',
  }[size];

  const textSize = {
    sm: 'text-xs',
    md: 'text-sm',
    lg: 'text-base',
  }[size];

  const getStatusColor = () => {
    if (status.isChecking) return 'text-yellow-500';
    if (status.isConnected) return 'text-green-500';
    return 'text-red-500';
  };

  const getStatusText = () => {
    if (status.isChecking) return 'Checking...';
    if (status.isConnected) return 'Connected';
    return 'Disconnected';
  };

  const getTooltipContent = () => {
    const parts: string[] = [];

    if (status.isConnected) {
      parts.push('Backend is connected');
    } else {
      parts.push('Backend is disconnected');
      if (status.consecutiveFailures > 0) {
        parts.push(`${status.consecutiveFailures} consecutive failures`);
      }
    }

    if (status.lastCheck) {
      const timeAgo = Math.floor((Date.now() - status.lastCheck.getTime()) / 1000);
      parts.push(`Last check: ${timeAgo}s ago`);
    }

    if (status.latency && showLatency) {
      parts.push(`Latency: ${status.latency}ms`);
    }

    if (status.lastConnected && !status.isConnected) {
      const timeAgo = Math.floor((Date.now() - status.lastConnected.getTime()) / 1000);
      parts.push(`Last connected: ${timeAgo}s ago`);
    }

    return parts.join('\n');
  };

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div
            className={cn(
              'flex items-center gap-2 cursor-pointer',
              className
            )}
          >
            {status.isChecking ? (
              <Loader2 className={cn(iconSize, 'text-yellow-500 animate-spin')} />
            ) : status.isConnected ? (
              <Wifi className={cn(iconSize, getStatusColor())} />
            ) : (
              <WifiOff className={cn(iconSize, getStatusColor())} />
            )}
            {showLabel && (
              <span className={cn(textSize, 'text-muted-foreground')}>
                {getStatusText()}
              </span>
            )}
            {showLatency && status.latency && status.isConnected && (
              <Badge variant="outline" className="text-xs">
                {status.latency}ms
              </Badge>
            )}
          </div>
        </TooltipTrigger>
        <TooltipContent>
          <div className="space-y-1">
            <p className="font-semibold">{getStatusText()}</p>
            <div className="text-xs text-muted-foreground whitespace-pre-line">
              {getTooltipContent()}
            </div>
            {!status.isConnected && status.consecutiveFailures > 3 && (
              <p className="text-xs text-yellow-500 mt-2">
                Consider checking if the backend is running
              </p>
            )}
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

export default ConnectionStatus;

