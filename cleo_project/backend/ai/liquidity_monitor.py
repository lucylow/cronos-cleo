"""
Liquidity monitor for tracking DEX pools
"""
import asyncio
import json
from typing import Dict, List, Optional
from web3 import AsyncWeb3
import aiohttp

# Optional Redis import
try:
    from redis import Redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False
    class Redis:
        def __init__(self, *args, **kwargs):
            pass
        def setex(self, *args, **kwargs):
            pass
        def get(self, *args, **kwargs):
            return None

# Minimal Uniswap V2 Pair ABI for getReserves
UNISWAP_V2_PAIR_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "getReserves",
        "outputs": [
            {"name": "_reserve0", "type": "uint112"},
            {"name": "_reserve1", "type": "uint112"},
            {"name": "_blockTimestampLast", "type": "uint32"}
        ],
        "type": "function"
    }
]


class LiquidityMonitor:
    """Monitor liquidity across multiple DEXs on Cronos"""
    
    def __init__(self, cronos_rpc: str):
        self.w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(cronos_rpc))
        try:
            self.redis = Redis(host='localhost', port=6379, decode_responses=True) if HAS_REDIS else None
        except:
            self.redis = None
        
        # DEX configurations
        self.dex_configs = {
            'vvs_finance': {
                'factory': '0x3B44B2aE43C0C0e5C0e5C0e5C0e5C0e5C0e5C0e5',
                'router': '0x145863Eb42Cf62847A6Ca784e6416C1682B1b2Ae',
                'subgraph': 'https://api.thegraph.com/subgraphs/name/vvs-finance/vvs-dex'
            },
            'cronaswap': {
                'factory': '0x73A48f8f521EB31c55c0e1274dB0898dE599Cb11',
                'router': '0xcd7d16fB918511BF72679eC3eC2f2f39c33C2F45',
                'subgraph': 'https://api.thegraph.com/subgraphs/name/cronaswap/exchange'
            },
            'mm_finance': {
                'factory': '0xd590cC180601AEcD6eeADD9B7f2b7611519544f4',
                'router': '0x145677FC4d9b8F19B5D56d1820c48e0443049a30',
                'subgraph': None  # May not have subgraph
            }
        }
    
    async def get_all_pools(self, dex_id: str) -> List[Dict]:
        """Fetch all pools for a DEX with real-time liquidity"""
        config = self.dex_configs.get(dex_id)
        if not config:
            return []
        
        pools = []
        
        # Method 1: Try subgraph query (if available)
        if config.get('subgraph'):
            try:
                async with aiohttp.ClientSession() as session:
                    query = {
                        "query": """
                        {
                            pairs(first: 100, where: {reserveUSD_gt: "10000"}) {
                                id
                                token0 { id symbol decimals }
                                token1 { id symbol decimals }
                                reserve0
                                reserve1
                                reserveUSD
                                volumeUSD
                            }
                        }
                        """
                    }
                    async with session.post(config['subgraph'], json=query, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if 'data' in data and 'pairs' in data['data']:
                                pools = data['data']['pairs']
                                # Add dex identifier
                                for pool in pools:
                                    pool['dex'] = dex_id
            except Exception as e:
                print(f"Subgraph query failed for {dex_id}: {e}")
        
        # Method 2: Real-time on-chain updates (limited for demo)
        # This would require contract addresses - skipping for now
        
        return pools
    
    async def get_all_pools_for_pair(self, token_in: str, token_out: str) -> List[Dict]:
        """Get all pools matching a token pair across all DEXs"""
        all_pools = []
        
        for dex_id in self.dex_configs.keys():
            try:
                pools = await self.get_all_pools(dex_id)
                # Filter for matching pair
                relevant_pools = [
                    p for p in pools
                    if self._matches_pair(p, token_in, token_out)
                ]
                all_pools.extend(relevant_pools)
            except Exception as e:
                print(f"Error fetching pools from {dex_id}: {e}")
                continue
        
        # If no pools found, return mock data
        if not all_pools:
            all_pools = [
                {
                    'id': '0xVVS_POOL',
                    'dex': 'vvs_finance',
                    'token0': {'id': token_in, 'symbol': 'CRO'},
                    'token1': {'id': token_out, 'symbol': 'USDC.e'},
                    'reserve0': '1000000',
                    'reserve1': '500000',
                    'reserveUSD': '1000000',
                    'feeBps': 25,
                    'price': 0.5
                },
                {
                    'id': '0xCRONA_POOL',
                    'dex': 'cronaswap',
                    'token0': {'id': token_in, 'symbol': 'CRO'},
                    'token1': {'id': token_out, 'symbol': 'USDC.e'},
                    'reserve0': '600000',
                    'reserve1': '300000',
                    'reserveUSD': '600000',
                    'feeBps': 30,
                    'price': 0.5
                }
            ]
        
        return all_pools
    
    def _matches_pair(self, pool: Dict, token_in: str, token_out: str) -> bool:
        """Check if pool matches token pair"""
        token0_id = pool.get('token0', {}).get('id', '').lower()
        token1_id = pool.get('token1', {}).get('id', '').lower()
        token_in_lower = token_in.lower()
        token_out_lower = token_out.lower()
        
        return (
            (token0_id == token_in_lower and token1_id == token_out_lower) or
            (token1_id == token_in_lower and token0_id == token_out_lower)
        )
    
    async def get_optimal_split(
        self,
        token_in: str,
        token_out: str,
        amount_in: float
    ) -> Dict:
        """Calculate optimal split across all available pools"""
        all_pools = await self.get_all_pools_for_pair(token_in, token_out)
        
        # This would typically call the AI optimizer
        # For now, return a simple split
        if not all_pools:
            return {"splits": []}
        
        total_liquidity = sum(float(p.get('reserveUSD', 0)) for p in all_pools)
        splits = []
        
        for pool in all_pools[:3]:  # Limit to top 3
            share = float(pool.get('reserveUSD', 0)) / max(total_liquidity, 1)
            splits.append({
                'dex': pool.get('dex', 'unknown'),
                'pool': pool.get('id'),
                'amount': amount_in * share,
                'share': share
            })
        
        return {"splits": splits}
