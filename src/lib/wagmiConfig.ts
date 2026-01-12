import { http, createConfig } from 'wagmi';
import { injected } from 'wagmi/connectors';

// Cronos mainnet chain
export const cronos = {
  id: 25,
  name: 'Cronos',
  nativeCurrency: { name: 'Cronos', symbol: 'CRO', decimals: 18 },
  rpcUrls: {
    default: { http: ['https://evm.cronos.org'] },
    public: { http: ['https://evm.cronos.org'] },
  },
  blockExplorers: {
    default: { name: 'Cronoscan', url: 'https://cronoscan.com' },
  },
} as const;

// Cronos testnet chain
export const cronosTestnet = {
  id: 338,
  name: 'Cronos Testnet',
  nativeCurrency: { name: 'Cronos Test', symbol: 'TCRO', decimals: 18 },
  rpcUrls: {
    default: { http: ['https://evm-t3.cronos.org'] },
    public: { http: ['https://evm-t3.cronos.org'] },
  },
  blockExplorers: {
    default: { name: 'Cronoscan Testnet', url: 'https://testnet.cronoscan.com' },
  },
} as const;

export const config = createConfig({
  chains: [cronosTestnet, cronos],
  connectors: [injected()],
  transports: {
    [cronos.id]: http(cronos.rpcUrls.default.http[0]),
    [cronosTestnet.id]: http(cronosTestnet.rpcUrls.default.http[0]),
  },
});
