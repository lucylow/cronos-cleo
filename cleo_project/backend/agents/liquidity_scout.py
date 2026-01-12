"""
Liquidity Scout Agent - Discovers liquidity across Cronos DEXs
Implements the liquidity discovery phase of the orchestration workflow
"""
import asyncio
import logging
import aiohttp
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from decimal import Decimal

from .base_agent import BaseAgent
from .message_bus import AgentMessage

logger = logging.getLogger(__name__)


@dataclass
class DEXPool:
    """DEX Pool data structure"""
    dex_id: str
    router: str
    reserve_in: int
    reserve_out: int
    depth: float
    impact_50k: float
    last_updated: float


class LiquidityScoutAgent(BaseAgent):
    """Agent responsible for discovering liquidity across Cronos DEXs"""
    
    def __init__(self):
        super().__init__("liquidity_scout", "Liquidity Scout")
        
        # Cronos DEX configurations
        self.cronos_dexes = {
            "VVS": {
                "router": "0x145863Eb42Cf62847A6Ca784e6416C1682b1b2Ae",
                "subgraph": "https://api.thegraph.com/subgraphs/name/vvsfinance/vvs-subgraph-v2"
            },
            "CRONA": {
                "router": "0x9b5dE07D0e07f98D257dC5786C765C0dC922e5a8",
                "subgraph": "https://api.thegraph.com/subgraphs/name/cronaswap/cronaswap"
            },
            "MMF": {
                "router": "0x4e352cf164E64AD5708Bb33E52fB4d9cd9F3bF82",
                "subgraph": "https://api.thegraph.com/subgraphs/name/mmfinance/v1"
            }
        }
        
        # Common Cronos token addresses
        self.CRO = "0x5C7F8A570d578B91F22530C0dbE9b54e18D7c019"
        self.USDC = "0xc21223249CA28397B4B6541dfFaEcC539BfF0c59"
    
    async def execute(self, request: Dict) -> Dict:
        """
        Execute liquidity discovery for a token pair
        
        Args:
            request: Dict with 'input_token' and 'output_token'
            
        Returns:
            Dict with pools, timestamp, and market_summary
        """
        input_token = request.get("input_token", self.CRO)
        output_token = request.get("output_token", self.USDC)
        
        # Query all DEXs in parallel
        tasks = []
        for dex_id, config in self.cronos_dexes.items():
            tasks.append(self._query_dex_liquidity(dex_id, config, input_token, output_token))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        pools = []
        for i, result in enumerate(results):
            if isinstance(result, dict) and result:
                pools.append(result)
            elif isinstance(result, Exception):
                logger.warning(f"Error querying {list(self.cronos_dexes.keys())[i]}: {result}")
        
        # Sort by depth (best liquidity first)
        pools.sort(key=lambda x: x.get("depth", 0), reverse=True)
        
        # Calculate market summary
        total_depth = sum(p.get("depth", 0) for p in pools[:3])  # Top 3
        best_single_dex = pools[0].get("dex_id") if pools else None
        
        # Estimate best split for a typical amount (75k CRO)
        estimated_amount = request.get("amount_in", 75000)
        predicted_best_split = self._estimate_best_split(pools, estimated_amount)
        
        market_summary = {
            "total_depth": total_depth,
            "best_single_dex": best_single_dex,
            "predicted_best_split": predicted_best_split
        }
        
        return {
            "pools": pools,
            "timestamp": datetime.now().isoformat(),
            "market_summary": market_summary
        }
    
    async def _query_dex_liquidity(self, dex_id: str, config: Dict, 
                                  token_in: str, token_out: str) -> Optional[Dict]:
        """Query liquidity from a DEX subgraph"""
        subgraph_url = config.get("subgraph")
        if not subgraph_url:
            return None
        
        # GraphQL query for pairs
        query = """
        {
          pairs(where: {
            or: [
              {token0: "%s", token1: "%s"},
              {token0: "%s", token1: "%s"}
            ]
          }, first: 5, orderBy: reserveUSD, orderDirection: desc) {
            id
            reserve0
            reserve1
            reserveUSD
            token0 { id symbol decimals }
            token1 { id symbol decimals }
            token0Price
            token1Price
          }
        }
        """ % (token_in, token_out, token_out, token_in)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    subgraph_url,
                    json={"query": query},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        pairs = data.get('data', {}).get('pairs', [])
                        
                        if pairs:
                            pair = pairs[0]  # Use best pair
                            
                            # Determine which token is which
                            if pair['token0']['id'].lower() == token_in.lower():
                                reserve_in = int(float(pair['reserve0']))
                                reserve_out = int(float(pair['reserve1']))
                            else:
                                reserve_in = int(float(pair['reserve1']))
                                reserve_out = int(float(pair['reserve0']))
                            
                            # Calculate depth (10% of reserve)
                            depth = reserve_in * 0.1
                            
                            # Calculate impact for 50k swap
                            impact_50k = self._calculate_slippage(
                                reserve_in, reserve_out, 50000
                            )
                            
                            return {
                                "dex_id": dex_id,
                                "router": config["router"],
                                "reserve_in": reserve_in,
                                "reserve_out": reserve_out,
                                "depth": depth,
                                "impact_50k": impact_50k,
                                "last_updated": datetime.now().timestamp(),
                                "pool_address": pair['id'],
                                "reserve_usd": float(pair.get('reserveUSD', 0))
                            }
        except Exception as e:
            logger.error(f"Error querying {dex_id}: {e}")
            return None
    
    def _calculate_slippage(self, reserve_in: int, reserve_out: int, amount_in: int) -> float:
        """Calculate slippage percentage for a given swap amount"""
        if reserve_in <= 0 or reserve_out <= 0:
            return 100.0  # 100% slippage if no liquidity
        
        # Constant product formula: k = reserve_in * reserve_out
        k = reserve_in * reserve_out
        
        # Calculate output without fee
        amount_out_ideal = (amount_in * reserve_out) / reserve_in
        
        # Calculate actual output with fee (0.3% = 997/1000)
        amount_in_with_fee = amount_in * 997 / 1000
        amount_out_actual = (amount_in_with_fee * reserve_out) / (reserve_in + amount_in_with_fee)
        
        # Calculate slippage
        if amount_out_ideal > 0:
            slippage = ((amount_out_ideal - amount_out_actual) / amount_out_ideal) * 100
            return max(0.0, slippage)
        
        return 0.0
    
    def _estimate_best_split(self, pools: List[Dict], amount_in: int) -> Dict:
        """Estimate best split allocation across pools"""
        if not pools:
            return {}
        
        # Simple heuristic: allocate based on depth
        total_depth = sum(p.get("depth", 0) for p in pools[:3])
        if total_depth <= 0:
            return {}
        
        split = {}
        for pool in pools[:3]:
            depth = pool.get("depth", 0)
            if depth > 0:
                weight = depth / total_depth
                split[pool.get("dex_id")] = {
                    "weight": weight,
                    "amount": amount_in * weight
                }
        
        return split
    
    async def handle_message(self, message: AgentMessage):
        """Handle incoming messages"""
        if message.message_type == "discover_liquidity":
            request_id = message.payload.get("request_id")
            
            result = await self.execute({
                "input_token": message.payload.get("input_token"),
                "output_token": message.payload.get("output_token"),
                "amount_in": message.payload.get("amount_in", 75000)
            })
            
            response = AgentMessage(
                message_id=f"resp_{message.message_id}",
                sender=self.agent_id,
                receiver=message.sender,
                message_type="liquidity_discovered",
                payload={
                    "result": result,
                    "request_id": request_id
                }
            )
            await self.send_message(response)
