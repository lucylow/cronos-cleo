import { ethers } from 'ethers';
import type { TokenMeta } from '../lib/mock-data';

// Router addresses - update these with actual deployed router addresses
export const ROUTER_ADDRESSES: Record<string, string> = {
  "VVS Finance": import.meta.env.VITE_VVS_ROUTER || "0xVVS_ROUTER_PLACEHOLDER",
  "CronaSwap": import.meta.env.VITE_CRONA_ROUTER || "0xCRONA_ROUTER_PLACEHOLDER",
  "MM Finance": import.meta.env.VITE_MM_ROUTER || "0xMM_ROUTER_PLACEHOLDER",
};

const FACILITATOR_ADDRESS = import.meta.env.VITE_X402_FACILITATOR || "0xFACILITATOR_PLACEHOLDER";

const FACILITATOR_ABI = [
  'function executeConditionalBatch(address[] targets, bytes[] data, string condition) external returns (bytes32)'
];

const ROUTER_SWAP_ABI = [
  'function swapExactTokensForTokens(uint256,uint256,address[],address,uint256) external returns (uint256[] memory)'
];

type Route = {
  dex: string;
  amountIn: number;
  estimatedOut?: number;
  minOut?: number;
  path: (string | TokenMeta)[];
};

export function buildX402BatchData(
  routes: Route[], 
  routerMap: Record<string, string>, 
  finalRecipient: string
) {
  const iface = new ethers.Interface(ROUTER_SWAP_ABI);
  const targets: string[] = [];
  const data: string[] = [];
  const deadline = Math.floor(Date.now() / 1000) + 60 * 10; // 10 minutes from now

  for (const r of routes) {
    const router = routerMap[r.dex] || ROUTER_ADDRESSES[r.dex] || Object.values(ROUTER_ADDRESSES)[0];
    
    if (!router || router.includes('PLACEHOLDER')) {
      console.warn(`Router address not set for DEX: ${r.dex}`);
      continue;
    }

    // Convert amount inputs to proper format
    // Assume 18 decimals for input tokens, adjust based on your token setup
    const amountInScaled = ethers.parseUnits(String(r.amountIn), 18);
    
    // Calculate minimum output with slippage tolerance
    const minOut = r.minOut || (r.estimatedOut ? Math.floor(r.estimatedOut * 0.995) : 0);
    // Assume 6 decimals for USDC output, adjust based on your token setup
    const outMinScaled = ethers.parseUnits(String(minOut), 6);
    
    // Convert path symbols to addresses
    const path = r.path.map((s) => {
      if (typeof s === 'string') {
        // Handle symbol strings
        if (s === 'CRO' || s === 'WETH') {
          return import.meta.env.VITE_CRO_ADDRESS || import.meta.env.VITE_WETH_ADDRESS || '0xCRO';
        }
        if (s === 'USDC' || s === 'USDC.e') {
          return import.meta.env.VITE_USDC_ADDRESS || '0xUSDCe';
        }
        return s; // Assume it's already an address
      } else {
        // TokenMeta object
        return s.address;
      }
    });

    const encoded = iface.encodeFunctionData('swapExactTokensForTokens', [
      amountInScaled,
      outMinScaled,
      path,
      finalRecipient,
      deadline
    ]);
    
    targets.push(router);
    data.push(encoded);
  }

  // Build condition string - ensure total output meets minimum
  const totalOut = routes.reduce((sum, r) => sum + (r.estimatedOut || 0), 0);
  const condition = `outputs_sum >= ${Math.floor(totalOut * 0.995)}`; // 0.5% slippage tolerance

  return { targets, data, condition };
}

export async function submitX402Batch(
  signer: ethers.Signer,
  routes: Route[],
  routerMap: Record<string, string>,
  finalRecipient: string
): Promise<ethers.TransactionResponse> {
  if (!FACILITATOR_ADDRESS || FACILITATOR_ADDRESS.includes('PLACEHOLDER')) {
    throw new Error('x402 Facilitator address not configured. Please set VITE_X402_FACILITATOR environment variable.');
  }

  const facilitator = new ethers.Contract(FACILITATOR_ADDRESS, FACILITATOR_ABI, signer);
  const { targets, data, condition } = buildX402BatchData(routes, routerMap, finalRecipient);

  if (targets.length === 0) {
    throw new Error('No valid routes to execute. Please check router addresses.');
  }

  try {
    // Estimate gas first
    const gasEstimate = await facilitator.executeConditionalBatch.estimateGas(targets, data, condition);
    
    // Execute with buffer
    return await facilitator.executeConditionalBatch(targets, data, condition, {
      gasLimit: gasEstimate * BigInt(120) / BigInt(100) // 20% buffer
    });
  } catch (error: any) {
    console.error('x402 batch execution error:', error);
    throw new Error(`Batch execution failed: ${error?.message || 'Unknown error'}`);
  }
}


