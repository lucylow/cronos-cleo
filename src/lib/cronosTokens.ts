/**
 * Cronos Token Utilities
 * Real token addresses on Cronos Mainnet and Testnet
 * Updated with verified contract addresses from Cronos ecosystem
 */

export interface CronosToken {
  symbol: string;
  name: string;
  address: string;
  decimals: number;
  logoURI?: string;
  isNative?: boolean;
  isStablecoin?: boolean;
  tags?: string[];
}

/**
 * Cronos Mainnet Token Addresses
 * Sources: Cronoscan, Cronos DEXs (VVS, CronaSwap, MM Finance)
 */
export const CRONOS_MAINNET_TOKENS: CronosToken[] = [
  // Native token
  {
    symbol: 'CRO',
    name: 'Cronos',
    address: '0x0000000000000000000000000000000000000000', // Native token
    decimals: 18,
    isNative: true,
    tags: ['native'],
  },
  
  // Wrapped CRO
  {
    symbol: 'WCRO',
    name: 'Wrapped CRO',
    address: '0x5C7F8A570d578ED84E63fdFA7b1eE72dEae1AE23',
    decimals: 18,
    tags: ['wrapped', 'native'],
  },

  // Stablecoins
  {
    symbol: 'USDC',
    name: 'USD Coin',
    address: '0xc21223249CA28397B4B6541dfFaEcC539BfF0c59',
    decimals: 6,
    isStablecoin: true,
    tags: ['stablecoin', 'usd'],
  },
  {
    symbol: 'USDT',
    name: 'Tether USD',
    address: '0x66e428c3f67a68878562e79A0234c1F83c208770',
    decimals: 6,
    isStablecoin: true,
    tags: ['stablecoin', 'usd'],
  },
  {
    symbol: 'DAI',
    name: 'Dai Stablecoin',
    address: '0xF2001B145b43032AAF5Ee2884e456CCd805F677D',
    decimals: 18,
    isStablecoin: true,
    tags: ['stablecoin', 'usd'],
  },

  // Wrapped Bitcoin
  {
    symbol: 'WBTC',
    name: 'Wrapped Bitcoin',
    address: '0x062E66477Faf219F25D27dCED647BF57C3107d52',
    decimals: 8,
    tags: ['wrapped', 'bitcoin'],
  },

  // Wrapped ETH
  {
    symbol: 'WETH',
    name: 'Wrapped Ethereum',
    address: '0xe44Fd7fCb2b1581822D0c862B68222998a0c299a',
    decimals: 18,
    tags: ['wrapped', 'ethereum'],
  },

  // DEX Tokens
  {
    symbol: 'VVS',
    name: 'VVS Finance',
    address: '0x2D03bECE6747ADC00E1a131BBA1469C15fD11e03',
    decimals: 18,
    tags: ['dex', 'governance'],
  },
  {
    symbol: 'CRONA',
    name: 'CronaSwap Token',
    address: '0xadbd1231fb360047525BEdF962581F3eee7b49fe',
    decimals: 18,
    tags: ['dex', 'governance'],
  },
  {
    symbol: 'MMF',
    name: 'MM Finance',
    address: '0x97749c9B61F878a880DfE312d2594AE07AEd7656',
    decimals: 18,
    tags: ['dex', 'governance'],
  },

  // DeFi Tokens
  {
    symbol: 'LINK',
    name: 'Chainlink',
    address: '0xBc6f24649CCd67eC42342AccdCECCB2eFA27c9d9',
    decimals: 18,
    tags: ['oracle', 'defi'],
  },
  {
    symbol: 'AAVE',
    name: 'Aave Token',
    address: '0x9AA6FC71aed1130DeE06a91A487BF5eA481dE80D',
    decimals: 18,
    tags: ['defi', 'lending'],
  },
  {
    symbol: 'UNI',
    name: 'Uniswap',
    address: '0x0000000000000000000000000000000000000001', // Placeholder
    decimals: 18,
    tags: ['defi'],
  },

  // Cosmos Ecosystem
  {
    symbol: 'ATOM',
    name: 'Cosmos',
    address: '0xB888d8Dd1733d72681b30c00ee76BDE5aeD2D6C2',
    decimals: 6,
    tags: ['cosmos', 'staking'],
  },
];

/**
 * Cronos Testnet Token Addresses
 */
export const CRONOS_TESTNET_TOKENS: CronosToken[] = [
  // Native token
  {
    symbol: 'TCRO',
    name: 'Test Cronos',
    address: '0x0000000000000000000000000000000000000000', // Native token
    decimals: 18,
    isNative: true,
    tags: ['native'],
  },
  
  // Test tokens (these are testnet-specific)
  {
    symbol: 'USDC',
    name: 'Test USDC',
    address: '0x0000000000000000000000000000000000000001', // Placeholder
    decimals: 6,
    isStablecoin: true,
    tags: ['stablecoin', 'test'],
  },
];

/**
 * Get token by symbol or address
 */
export function getCronosToken(
  symbolOrAddress: string,
  chainId: number = 25
): CronosToken | null {
  const tokens = chainId === 25 ? CRONOS_MAINNET_TOKENS : CRONOS_TESTNET_TOKENS;
  
  const token = tokens.find(
    (t) =>
      t.symbol.toLowerCase() === symbolOrAddress.toLowerCase() ||
      t.address.toLowerCase() === symbolOrAddress.toLowerCase()
  );
  
  return token || null;
}

/**
 * Get all tokens for a chain
 */
export function getCronosTokens(chainId: number = 25): CronosToken[] {
  return chainId === 25 ? CRONOS_MAINNET_TOKENS : CRONOS_TESTNET_TOKENS;
}

/**
 * Check if an address is a valid Cronos token
 */
export function isCronosToken(address: string, chainId: number = 25): boolean {
  return getCronosToken(address, chainId) !== null;
}

/**
 * Get token symbol from address
 */
export function getTokenSymbol(address: string, chainId: number = 25): string | null {
  const token = getCronosToken(address, chainId);
  return token?.symbol || null;
}

/**
 * Get token name from address
 */
export function getTokenName(address: string, chainId: number = 25): string | null {
  const token = getCronosToken(address, chainId);
  return token?.name || null;
}

/**
 * Check if address is native CRO
 */
export function isNativeCRO(address: string): boolean {
  return (
    address === '0x0000000000000000000000000000000000000000' ||
    address.toLowerCase() === '0x0000000000000000000000000000000000000000'
  );
}

/**
 * Get wrapped CRO address for a chain
 */
export function getWrappedCROAddress(chainId: number = 25): string {
  if (chainId === 25) {
    return '0x5C7F8A570d578ED84E63fdFA7b1eE72dEae1AE23'; // Mainnet WCRO
  } else if (chainId === 338) {
    return '0x0000000000000000000000000000000000000001'; // Testnet placeholder
  }
  return '0x5C7F8A570d578ED84E63fdFA7b1eE72dEae1AE23'; // Default to mainnet
}

/**
 * Popular token pairs on Cronos DEXs
 */
export const POPULAR_PAIRS = [
  ['CRO', 'USDC'],
  ['CRO', 'USDT'],
  ['USDC', 'USDT'],
  ['WCRO', 'CRO'],
  ['VVS', 'CRO'],
  ['MMF', 'CRO'],
  ['CRONA', 'CRO'],
  ['WBTC', 'USDC'],
  ['WETH', 'USDC'],
  ['LINK', 'USDC'],
];

/**
 * DEX Router Addresses on Cronos
 */
export const CRONOS_DEX_ROUTERS = {
  vvs: {
    mainnet: '0x145863Eb42Cf62847A6Ca784e6416C1682b1b2Ae',
    testnet: '0x0000000000000000000000000000000000000001', // Placeholder
  },
  cronaswap: {
    mainnet: '0xcd7d16fB918511BF7269eC4f48d61D79Fb26f918',
    testnet: '0x0000000000000000000000000000000000000001', // Placeholder
  },
  mmfinance: {
    mainnet: '0x145677FC4d9b8F19B5D56d1820c48e0443049a30',
    testnet: '0x0000000000000000000000000000000000000001', // Placeholder
  },
};

/**
 * Get DEX router address
 */
export function getDEXRouter(dex: 'vvs' | 'cronaswap' | 'mmfinance', chainId: number = 25): string {
  const isMainnet = chainId === 25;
  return CRONOS_DEX_ROUTERS[dex][isMainnet ? 'mainnet' : 'testnet'];
}


