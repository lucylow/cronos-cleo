
# liquidity_monitor.py

import asyncio

from web3 import AsyncWeb3

from redis import Redis

from typing import Dict, List

import aiohttp

class LiquidityMonitor:

def __init__(self, cronos_rpc: str):

self.w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(cronos_rpc))

self.redis = Redis(host=\'localhost\', port=6379,
decode_responses=True)

self.dex_configs = {

\'vvs_finance\': {

\'factory\': \'0x3B44B2...\',

\'router\': \'0x145863...\',

\'subgraph\':
\'https://api.thegraph.com/subgraphs/name/vvs-finance/vvs-dex\'

},

# Add other DEXs

}

async def get_all_pools(self, dex_id: str) -\> List\[Dict\]:

\"\"\"Fetch all pools for a DEX with real-time liquidity\"\"\"

config = self.dex_configs\[dex_id\]

# Method 1: Subgraph query (historical, efficient)

async with aiohttp.ClientSession() as session:

query = {

\"query\": \"\"\"

{

pairs(first: 1000, where: {reserveUSD_gt: 10000}) {

id

token0 { id symbol decimals }

token1 { id symbol decimals }

reserve0 reserve1 reserveUSD

volumeUSD

}

}

\"\"\"

}

async with session.post(config\[\'subgraph\'\], json=query) as resp:

data = await resp.json()

pools = data\[\'data\'\]\[\'pairs\'\]

# Method 2: Real-time on-chain updates

realtime_pools = \[\]

for pool in pools\[:50\]: # Limit for demo

contract = self.w3.eth.contract(

address=pool\[\'id\'\],

abi=UNISWAP_V2_PAIR_ABI

)

reserves = await contract.functions.getReserves().call()

pool\[\'real_reserves\'\] = reserves

realtime_pools.append(pool)

# Cache with 5-second TTL

self.redis.setex(

f\"pool:{dex_id}:{pool\[\'id\'\]}\",

5,

json.dumps(pool)

)

return realtime_pools

async def get_optimal_split(

self,

token_in: str,

token_out: str,

amount_in: float

) -\> Dict:

\"\"\"Calculate optimal split across all available pools\"\"\"

all_pools = \[\]

for dex_id in self.dex_configs:

pools = await self.get_all_pools(dex_id)

relevant_pools = \[

p for p in pools

if (p\[\'token0\'\]\[\'id\'\] == token_in and p\[\'token1\'\]\[\'id\'\]
== token_out)

or (p\[\'token1\'\]\[\'id\'\] == token_in and p\[\'token0\'\]\[\'id\'\]
== token_out)

\]

all_pools.extend(relevant_pools)

# Use AI model to calculate optimal split

split = await self.ai_optimizer.predict_optimal_split(

pools=all_pools,

amount_in=amount_in,

token_in=token_in,

token_out=token_out

)

return split

