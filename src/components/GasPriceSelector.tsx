/**
 * Gas Price Selector Component
 * Provides Slow/Normal/Fast presets with live gas price recommendations
 */
import { useState, useEffect } from 'react';
import { useGas } from '../hooks/useGas';
import { Button } from './ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Loader2, Zap, Gauge, Turtle } from 'lucide-react';
import { formatUnits, parseUnits } from 'ethers';

export type GasPreset = 'slow' | 'normal' | 'fast';

export interface GasPriceSelectorProps {
  onPresetChange?: (preset: GasPreset) => void;
  onGasParamsChange?: (params: GasParams) => void;
  selectedPreset?: GasPreset;
  showDetails?: boolean;
}

export interface GasParams {
  maxFeePerGas: bigint | null;
  maxPriorityFeePerGas: bigint | null;
  gasPrice: bigint | null;
  supports1559: boolean;
}

const PRESET_MULTIPLIERS = {
  slow: { priorityMultiplier: 0.8, feeMarginGwei: 0 },
  normal: { priorityMultiplier: 1.0, feeMarginGwei: 1 },
  fast: { priorityMultiplier: 1.3, feeMarginGwei: 3 },
};

const PRESET_LABELS = {
  slow: { label: 'Slow', icon: Turtle, color: 'bg-blue-500' },
  normal: { label: 'Normal', icon: Gauge, color: 'bg-green-500' },
  fast: { label: 'Fast', icon: Zap, color: 'bg-orange-500' },
};

export function GasPriceSelector({
  onPresetChange,
  onGasParamsChange,
  selectedPreset = 'normal',
  showDetails = true,
}: GasPriceSelectorProps) {
  const { gas, loading, error } = useGas({ interval: 10000 });
  const [preset, setPreset] = useState<GasPreset>(selectedPreset);

  useEffect(() => {
    if (gas && onGasParamsChange) {
      const params = calculateGasParams(gas, preset);
      onGasParamsChange(params);
    }
  }, [gas, preset, onGasParamsChange]);

  const calculateGasParams = (gasRec: any, selectedPreset: GasPreset): GasParams => {
    const multipliers = PRESET_MULTIPLIERS[selectedPreset];

    if (gasRec.supports1559 && gasRec.maxPriorityFeePerGasGwei) {
      const basePriority = parseFloat(gasRec.maxPriorityFeePerGasGwei);
      const adjustedPriority = basePriority * multipliers.priorityMultiplier;
      const maxPriorityFeePerGas = parseUnits(adjustedPriority.toFixed(9), 'gwei');

      let maxFeePerGas: bigint;
      if (gasRec.maxFeePerGasGwei) {
        const baseMaxFee = parseFloat(gasRec.maxFeePerGasGwei);
        const adjustedMaxFee = baseMaxFee + multipliers.feeMarginGwei;
        maxFeePerGas = parseUnits(adjustedMaxFee.toFixed(9), 'gwei');
      } else {
        // Estimate maxFeePerGas from priority fee
        const estimatedBaseFee = parseFloat(gasRec.maxPriorityFeePerGasGwei || '1');
        maxFeePerGas = parseUnits((estimatedBaseFee + adjustedPriority + multipliers.feeMarginGwei).toFixed(9), 'gwei');
      }

      return {
        maxFeePerGas,
        maxPriorityFeePerGas,
        gasPrice: null,
        supports1559: true,
      };
    } else if (gasRec.legacyGasPriceGwei) {
      const baseGasPrice = parseFloat(gasRec.legacyGasPriceGwei);
      const adjustedGasPrice = baseGasPrice * multipliers.priorityMultiplier;
      const gasPrice = parseUnits(adjustedGasPrice.toFixed(9), 'gwei');

      return {
        maxFeePerGas: null,
        maxPriorityFeePerGas: null,
        gasPrice,
        supports1559: false,
      };
    }

    // Fallback
    return {
      maxFeePerGas: parseUnits('1', 'gwei'),
      maxPriorityFeePerGas: parseUnits('1', 'gwei'),
      gasPrice: null,
      supports1559: true,
    };
  };

  const handlePresetChange = (newPreset: GasPreset) => {
    setPreset(newPreset);
    onPresetChange?.(newPreset);
  };

  const formatGwei = (gwei: string | null): string => {
    if (!gwei) return 'N/A';
    const num = parseFloat(gwei);
    return num.toFixed(2);
  };

  const getEstimatedCost = (gasLimit: bigint = BigInt(21000)): string => {
    if (!gas) return 'N/A';
    
    try {
      let costWei: bigint;
      if (gas.supports1559 && gas.maxFeePerGasGwei) {
        const maxFee = parseUnits(gas.maxFeePerGasGwei, 'gwei');
        costWei = gasLimit * maxFee;
      } else if (gas.legacyGasPriceGwei) {
        const gasPrice = parseUnits(gas.legacyGasPriceGwei, 'gwei');
        costWei = gasLimit * gasPrice;
      } else {
        return 'N/A';
      }
      
      // Convert to CRO (assuming 18 decimals)
      const costCro = formatUnits(costWei, 18);
      return parseFloat(costCro).toFixed(6);
    } catch {
      return 'N/A';
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          Gas Price Settings
          {loading && <Loader2 className="h-4 w-4 animate-spin" />}
        </CardTitle>
        <CardDescription>
          Select transaction speed. Higher fees = faster confirmation.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && (
          <div className="rounded-md bg-red-50 p-3 text-sm text-red-800 dark:bg-red-900/20 dark:text-red-200">
            Error loading gas prices: {error}
          </div>
        )}

        <div className="grid grid-cols-3 gap-2">
          {(['slow', 'normal', 'fast'] as GasPreset[]).map((presetOption) => {
            const presetInfo = PRESET_LABELS[presetOption];
            const Icon = presetInfo.icon;
            const isSelected = preset === presetOption;

            return (
              <Button
                key={presetOption}
                variant={isSelected ? 'default' : 'outline'}
                className="flex flex-col items-center gap-2 h-auto py-3"
                onClick={() => handlePresetChange(presetOption)}
              >
                <Icon className="h-5 w-5" />
                <span className="font-medium">{presetInfo.label}</span>
                {isSelected && (
                  <Badge variant="secondary" className="text-xs">
                    Selected
                  </Badge>
                )}
              </Button>
            );
          })}
        </div>

        {showDetails && gas && (
          <div className="space-y-2 rounded-lg border p-3 bg-muted/50">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Current Gas Price:</span>
              <span className="font-mono font-medium">
                {gas.supports1559
                  ? `${formatGwei(gas.maxPriorityFeePerGasGwei)} gwei`
                  : `${formatGwei(gas.legacyGasPriceGwei)} gwei`}
              </span>
            </div>
            {gas.supports1559 && (
              <>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Max Fee:</span>
                  <span className="font-mono">{formatGwei(gas.maxFeePerGasGwei)} gwei</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Priority Fee:</span>
                  <span className="font-mono">{formatGwei(gas.maxPriorityFeePerGasGwei)} gwei</span>
                </div>
              </>
            )}
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Est. Cost (21k gas):</span>
              <span className="font-mono">{getEstimatedCost()} CRO</span>
            </div>
            <div className="flex items-center justify-between text-xs text-muted-foreground pt-1 border-t">
              <span>Source:</span>
              <span>{gas.source}</span>
            </div>
          </div>
        )}

        {showDetails && loading && !gas && (
          <div className="flex items-center justify-center py-4">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            <span className="ml-2 text-sm text-muted-foreground">Loading gas prices...</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
