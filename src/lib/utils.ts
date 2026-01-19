import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function copyToClipboard(text: string) {
  if (!text) return;
  navigator.clipboard?.writeText(text).catch(() => {});
}

export function formatWeiTo(numStr: string, decimals = 18, digits = 6) {
  try {
    // Using ethers is better but keep a safe fallback
    const n = Number(numStr) / Math.pow(10, decimals);
    return n.toFixed(Math.min(digits, 8));
  } catch {
    return '0';
  }
}

export function explorerTxUrl(chain = 'cronos', txHash: string) {
  if (!txHash) return '#';
  // Cronos explorer base
  if (chain === 'cronos') return `https://cronos.org/explorer/tx/${txHash}`;
  // Fallback Etherscan for mainnet
  return `https://etherscan.io/tx/${txHash}`;
}

export function explorerAddressUrl(chain = 'cronos', addr: string) {
  if (!addr) return '#';
  if (chain === 'cronos') return `https://cronos.org/explorer/address/${addr}`;
  return `https://etherscan.io/address/${addr}`;
}
