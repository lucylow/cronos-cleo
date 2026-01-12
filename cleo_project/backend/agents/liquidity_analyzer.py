"""
Liquidity Analyzer Agent - Monitors liquidity across Cronos DEXs
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal
import aiohttp
from web3 import Web3, AsyncHTTPProvider
from web3.contract import AsyncContract

from .base_agent import BaseAgent
from .message_bus import AgentMessage
from .models import Token, DEXPool

logger = logging.getLogger(__name__)


class LiquidityAnalyzerAgent(BaseAgent):
    """Agent responsible for monitoring liquidity across Cronos DEXs"""
    
    def __init__(self, cronos_rpc: str, redis_url: Optional[str] = None):
        super().__init__("liquidity_analyzer", "Liquidity Analyzer")
        self.w3 = Web3(AsyncHTTPProvider(cronos_rpc))
        self.redis = None
        self.redis_url = redis_url
        self.pools: Dict[str, DEXPool] = {}
        self.update_interval = 5  # seconds
        
        # DEX configurations
        self.dex_configs = {
            "vvs_finance": {
                "factory": "0x3B44B2a187b7Fc6c3a90cF00fA6d5b6C31E35eD8",
                "router": "0x145863Eb42Cf62847A6Ca784e6416C1682b1b2Ae",
                "subgraph": "https://api.thegraph.com/subgraphs/name/vvs-finance/vvs-dex"
            },
            "cronaswap": {
                "factory": "0x73A48f8f521EB31c55c0e1274dB0898dE599Cb11",
                "router": "0xcd7d16fB918511BF7269eC4f48d61D79Fb26f918",
                "subgraph": "https://api.thegraph.com/subgraphs/name/cronaswap/exchange"
            },
            "mm_finance": {
                "factory": "0xd590cC180601AEcD6eeADD9B7f2B7611519544f4",
                "router": "0x145677FC4d9b8F19B5D56d1820c48e0443049a30",
                "subgraph": "https://api.thegraph.com/subgraphs/name/mm-finance/cronos"
            }
        }
        
        # Pending requests tracking
        self._pending_requests: Dict[str, Dict] = {}
    
    async def start(self):
        """Start the liquidity analyzer"""
        await super().start()
        
        # Initialize Redis if URL provided
        if self.redis_url:
            try:
                from redis import asyncio as aioredis
                self.redis = await aioredis.from_url(self.redis_url, decode_responses=True)
                logger.info("Redis connection established")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}, continuing without cache")
        
        asyncio.create_task(self._continuous_monitoring())
    
    async def stop(self):
        """Stop the agent and close connections"""
        await super().stop()
        if self.redis:
            await self.redis.close()
    
    async def _continuous_monitoring(self):
        """Continuously monitor DEX liquidity"""
        while self.is_running:
            try:
                await self._update_all_pools()
                await self._broadcast_liquidity_update()
                await asyncio.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"Liquidity monitoring error: {e}")
                await asyncio.sleep(10)  # Backoff on error
    
    async def _update_all_pools(self):
        """Update liquidity for all pools"""
        for dex_name, config in self.dex_configs.items():
            try:
                pools = await self._fetch_pools_from_subgraph(dex_name, config["subgraph"])
                for pool_data in pools:
                    pool_id = f"{dex_name}:{pool_data['id']}"
                    
                    # Get real-time reserves
                    reserves = await self._get_pool_reserves(pool_data['id'])
                    if reserves:
                        pool = DEXPool(
                            dex_name=dex_name,
                            pool_address=pool_data['id'],
                            token0=Token(
                                address=pool_data['token0']['id'],
                                symbol=pool_data['token0']['symbol'],
                                decimals=int(pool_data['token0']['decimals']),
                                name=pool_data['token0'].get('name', '')
                            ),
                            token1=Token(
                                address=pool_data['token1']['id'],
                                symbol=pool_data['token1']['symbol'],
                                decimals=int(pool_data['token1']['decimals']),
                                name=pool_data['token1'].get('name', '')
                            ),
                            reserve0=Decimal(str(reserves[0])) / Decimal(10**int(pool_data['token0']['decimals'])),
                            reserve1=Decimal(str(reserves[1])) / Decimal(10**int(pool_data['token1']['decimals'])),
                            reserve_usd=Decimal(pool_data.get('reserveUSD', '0'))
                        )
                        self.pools[pool_id] = pool
                        
                        # Cache in Redis with 5-second TTL
                        if self.redis:
                            try:
                                await self.redis.setex(
                                    f"pool:{pool_id}",
                                    5,
                                    pool.json()
                                )
                            except Exception as e:
                                logger.debug(f"Redis cache error: {e}")
            except Exception as e:
                logger.warning(f"Error updating pools for {dex_name}: {e}")
    
    async def _fetch_pools_from_subgraph(self, dex_name: str, subgraph_url: str) -> List[Dict]:
        """Fetch pools from subgraph"""
        query = {
            "query": """
            {
                pairs(first: 200, where: {reserveUSD_gt: 1000}, orderBy: reserveUSD, orderDirection: desc) {
                    id
                    token0 { id symbol decimals name }
                    token1 { id symbol decimals name }
                    reserve0
                    reserve1
                    reserveUSD
                    volumeUSD
                    txCount
                }
            }
            """
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(subgraph_url, json=query, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('data', {}).get('pairs', [])
                    else:
                        logger.warning(f"Subgraph query failed for {dex_name}: {response.status}")
                        return []
        except Exception as e:
            logger.warning(f"Error fetching pools from {dex_name}: {e}")
            return []
    
    async def _get_pool_reserves(self, pool_address: str) -> Optional[Tuple[int, int]]:
        """Get real-time reserves from on-chain"""
        try:
            # Uniswap V2 Pair ABI for getReserves
            pair_abi = [{
                "constant": True,
                "inputs": [],
                "name": "getReserves",
                "outputs": [
                    {"internalType": "uint112", "name": "_reserve0", "type": "uint112"},
                    {"internalType": "uint112", "name": "_reserve1", "type": "uint112"},
                    {"internalType": "uint32", "name": "_blockTimestampLast", "type": "uint32"}
                ],
                "payable": False,
                "stateMutability": "view",
                "type": "function"
            }]
            contract = self.w3.eth.contract(address=pool_address, abi=pair_abi)
            reserves = await contract.functions.getReserves().call()
            return reserves[0], reserves[1]
        except Exception as e:
            logger.debug(f"Failed to get reserves for {pool_address}: {e}")
            return None
    
    async def _broadcast_liquidity_update(self):
        """Broadcast liquidity update to other agents"""
        total_liquidity = sum(pool.reserve_usd for pool in self.pools.values())
        
        await self.broadcast_event(
            "liquidity_update",
            {
                "total_pools": len(self.pools),
                "total_liquidity_usd": float(total_liquidity),
                "timestamp": datetime.now().isoformat()
            }
        )
    
    async def handle_message(self, message: AgentMessage):
        """Handle incoming messages"""
        if message.message_type == "get_liquidity":
            # Return liquidity for specific token pair
            token_in = message.payload.get("token_in")
            token_out = message.payload.get("token_out")
            request_id = message.payload.get("request_id")
            
            relevant_pools = []
            for pool in self.pools.values():
                if (pool.token0.address.lower() == token_in.lower() and pool.token1.address.lower() == token_out.lower()) or \
                   (pool.token1.address.lower() == token_in.lower() and pool.token0.address.lower() == token_out.lower()):
                    relevant_pools.append(pool)
            
            response = AgentMessage(
                message_id=f"resp_{message.message_id}",
                sender=self.agent_id,
                receiver=message.sender,
                message_type="liquidity_response",
                payload={
                    "pools": [pool.dict() for pool in relevant_pools],
                    "request_id": request_id
                }
            )
            await self.send_message(response)
        
        elif message.message_type == "get_best_price":
            # Get best price for token pair
            token_in = message.payload.get("token_in")
            token_out = message.payload.get("token_out")
            amount_in = Decimal(str(message.payload.get("amount_in", 0)))
            request_id = message.payload.get("request_id")
            
            best_price = await self._calculate_best_price(token_in, token_out, amount_in)
            
            response = AgentMessage(
                message_id=f"resp_{message.message_id}",
                sender=self.agent_id,
                receiver=message.sender,
                message_type="price_response",
                payload={
                    "best_price": float(best_price) if best_price else None,
                    "request_id": request_id
                }
            )
            await self.send_message(response)
    
    async def _calculate_best_price(self, token_in: str, token_out: str, amount_in: Decimal) -> Optional[Decimal]:
        """Calculate best price across all pools"""
        best_output = Decimal('0')
        
        for pool in self.pools.values():
            if (pool.token0.address.lower() == token_in.lower() and pool.token1.address.lower() == token_out.lower()):
                # Token0 -> Token1
                output = self._calculate_output_amount(
                    amount_in, pool.reserve0, pool.reserve1, pool.fee_tier
                )
                best_output = max(best_output, output)
            
            elif (pool.token1.address.lower() == token_in.lower() and pool.token0.address.lower() == token_out.lower()):
                # Token1 -> Token0
                output = self._calculate_output_amount(
                    amount_in, pool.reserve1, pool.reserve0, pool.fee_tier
                )
                best_output = max(best_output, output)
        
        return best_output if best_output > 0 else None
    
    def _calculate_output_amount(self, amount_in: Decimal, reserve_in: Decimal, 
                               reserve_out: Decimal, fee: int) -> Decimal:
        """Calculate output amount using constant product formula"""
        if amount_in <= 0 or reserve_in <= 0 or reserve_out <= 0:
            return Decimal('0')
        
        # Apply fee (0.3% = 997/1000)
        amount_in_with_fee = amount_in * Decimal('997') / Decimal('1000')
        numerator = amount_in_with_fee * reserve_out
        denominator = reserve_in + amount_in_with_fee
        
        return numerator / denominator
