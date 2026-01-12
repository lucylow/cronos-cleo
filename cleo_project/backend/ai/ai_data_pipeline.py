"""
C.L.E.O. AI Data Pipeline
Cronos Liquidity Execution Orchestrator

Data Pipeline Components:
1. On-chain Data Collectors (Cronos, DEXs, x402)
2. Market Data Streamers (Crypto.com MCP, External APIs)
3. Feature Engineering Pipeline
4. Label Generation System
5. Data Validation & Quality Monitoring
6. Feature Store & Vector Database
7. Real-time Data Serving Layer
8. Data Versioning & Lineage Tracking
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any, Set, Deque
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
import pandas as pd
from decimal import Decimal
import aiohttp
from web3 import Web3, AsyncHTTPProvider
from web3.contract import AsyncContract
from web3.datastructures import AttributeDict
from web3.exceptions import BlockNotFound, TransactionNotFound
import redis.asyncio as aioredis
try:
    from kafka import KafkaProducer, KafkaConsumer
    from kafka.admin import KafkaAdminClient, NewTopic
    HAS_KAFKA = True
except ImportError:
    HAS_KAFKA = False
import pickle
import hashlib
from contextlib import asynccontextmanager
import gc
from collections import defaultdict, deque
import zlib
import msgpack
from pydantic import BaseModel, Field, validator
try:
    from prometheus_client import Counter, Gauge, Histogram, start_http_server
    HAS_PROMETHEUS = True
except ImportError:
    HAS_PROMETHEUS = False
import time
from typing_extensions import Literal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cleo_data_pipeline.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Prometheus metrics
if HAS_PROMETHEUS:
    DATA_POINTS_COLLECTED = Counter(
        'cleo_data_points_collected', 
        'Number of data points collected', 
        ['source', 'type']
    )
    DATA_PROCESSING_TIME = Histogram(
        'cleo_data_processing_time_seconds',
        'Time spent processing data',
        ['operation']
    )
    FEATURE_STORE_SIZE = Gauge(
        'cleo_feature_store_size_mb',
        'Size of feature store in MB'
    )
    DATA_QUALITY_SCORE = Gauge(
        'cleo_data_quality_score',
        'Data quality score (0-100)'
    )
else:
    # Mock metrics if prometheus not available
    class MockMetric:
        def labels(self, **kwargs): return self
        def inc(self, n=1): pass
        def observe(self, value): pass
        def set(self, value): pass
    DATA_POINTS_COLLECTED = MockMetric()
    DATA_PROCESSING_TIME = MockMetric()
    FEATURE_STORE_SIZE = MockMetric()
    DATA_QUALITY_SCORE = MockMetric()

# ============================================================================
# Data Models
# ============================================================================

class DataSource(Enum):
    """Data source enumeration"""
    CRONOS_BLOCKCHAIN = "cronos_blockchain"
    VVS_FINANCE = "vvs_finance"
    CRONASWAP = "cronaswap"
    MM_FINANCE = "mm_finance"
    CRYPTOCOM_MCP = "crypto_com_mcp"
    COINGECKO = "coingecko"
    DEXT_IO = "dext_io"
    CHAINLINK = "chainlink"
    X402_FACILITATOR = "x402_facilitator"
    INTERNAL_ANALYTICS = "internal_analytics"

class DataType(Enum):
    """Data type enumeration"""
    BLOCK = "block"
    TRANSACTION = "transaction"
    SWAP_EVENT = "swap_event"
    LIQUIDITY_EVENT = "liquidity_event"
    PRICE_FEED = "price_feed"
    GAS_PRICE = "gas_price"
    TOKEN_METADATA = "token_metadata"
    POOL_METADATA = "pool_metadata"
    USER_POSITION = "user_position"
    AGENT_DECISION = "agent_decision"
    EXECUTION_RESULT = "execution_result"

class RawDataPoint(BaseModel):
    """Raw data point from any source"""
    data_id: str = Field(default_factory=lambda: f"data_{int(time.time() * 1000)}")
    source: DataSource
    data_type: DataType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    raw_data: Dict[str, Any]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    data_hash: str = ""
    
    @validator('data_hash', always=True)
    def compute_data_hash(cls, v, values):
        """Compute hash of raw data for integrity checking"""
        if 'raw_data' in values:
            data_str = json.dumps(values['raw_data'], sort_keys=True, default=str)
            return hashlib.sha256(data_str.encode()).hexdigest()
        return ""

class ProcessedFeature(BaseModel):
    """Processed feature for ML models"""
    feature_id: str
    timestamp: datetime
    entity_id: str  # e.g., "pool:0x123", "token:USDC", "user:0xabc"
    feature_set: str  # e.g., "slippage_prediction", "risk_assessment"
    feature_vector: List[float]
    feature_names: List[str]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    version: str = "1.0.0"
    
    class Config:
        arbitrary_types_allowed = True

class DataLabel(BaseModel):
    """Label for supervised learning"""
    label_id: str
    timestamp: datetime
    entity_id: str
    label_type: str  # e.g., "actual_slippage", "execution_success"
    label_value: float
    confidence: float = 1.0
    source_data_ids: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class FeatureStoreRecord(BaseModel):
    """Record in feature store"""
    record_id: str
    entity_id: str
    timestamp: datetime
    features: Dict[str, float]
    labels: Dict[str, float] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    def to_vector(self, feature_order: List[str]) -> List[float]:
        """Convert to feature vector in specified order"""
        return [self.features.get(f, 0.0) for f in feature_order]

class DataQualityMetric(BaseModel):
    """Data quality metric"""
    metric_id: str
    timestamp: datetime
    metric_name: str  # e.g., "completeness", "freshness", "accuracy"
    metric_value: float
    source: DataSource
    data_type: DataType
    details: Dict[str, Any] = Field(default_factory=dict)

# ============================================================================
# 1. On-chain Data Collectors
# ============================================================================

class OnChainDataCollector:
    """Collects data from Cronos blockchain and DEXs"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.w3 = Web3(AsyncHTTPProvider(config['cronos_rpc']))
        self.redis = None
        self.kafka_producer = None
        self.running = False
        
        # Contract ABIs
        self.contract_abis = self._load_contract_abis()
        
        # Known DEX addresses
        self.dex_addresses = {
            'vvs_finance': {
                'factory': '0x3B44B2a187b7Fc6c3a90cF00fA6d5b6C31E35eD8',
                'router': '0x145863Eb42Cf62847A6Ca784e6416C1682b1b2Ae',
                'vvs_token': '0x2D03bECE6747ADC00E1a131BBA1469C15fD11e03'
            },
            'cronaswap': {
                'factory': '0x73A48f8f521EB31c55c0e1274dB0898dE599Cb11',
                'router': '0xcd7d16fB918511BF7269eC4f48d61D79Fb26f918',
                'crona_token': '0xadbd1231fb360047525BEdF962581F3eee7b49fe'
            },
            'mm_finance': {
                'factory': '0xd590cC180601AEcD6eeADD9B7f2B7611519544f4',
                'router': '0x145677FC4d9b8F19B5D56d1820c48e0443049a30',
                'mmf_token': '0x97749c9B61F878a880DfE312d2594AE07AEd7656'
            }
        }
        
        # Event signatures
        self.event_signatures = {
            'Swap': '0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822',
            'Mint': '0x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f',
            'Burn': '0xdccd412f0b1252819cb1fd330b93224ca42612892bb3f4f789976e6d81936496',
            'Sync': '0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1'
        }
        
        # Data buffers
        self.data_buffer: Dict[str, Deque] = defaultdict(lambda: deque(maxlen=1000))
        
        logger.info("OnChainDataCollector initialized")
    
    def _load_contract_abis(self) -> Dict[str, List]:
        """Load contract ABIs"""
        uniswap_v2_pair_abi = [
            {
                "constant": True,
                "inputs": [],
                "name": "getReserves",
                "outputs": [
                    {"internalType": "uint112", "name": "reserve0", "type": "uint112"},
                    {"internalType": "uint112", "name": "reserve1", "type": "uint112"},
                    {"internalType": "uint32", "name": "blockTimestampLast", "type": "uint32"}
                ],
                "payable": False,
                "stateMutability": "view",
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "token0",
                "outputs": [{"internalType": "address", "name": "", "type": "address"}],
                "payable": False,
                "stateMutability": "view",
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "token1",
                "outputs": [{"internalType": "address", "name": "", "type": "address"}],
                "payable": False,
                "stateMutability": "view",
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "totalSupply",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "payable": False,
                "stateMutability": "view",
                "type": "function"
            }
        ]
        
        return {
            'uniswap_v2_pair': uniswap_v2_pair_abi,
            'erc20': [
                {
                    "constant": True,
                    "inputs": [],
                    "name": "decimals",
                    "outputs": [{"internalType": "uint8", "name": "", "type": "uint8"}],
                    "payable": False,
                    "stateMutability": "view",
                    "type": "function"
                },
                {
                    "constant": True,
                    "inputs": [],
                    "name": "symbol",
                    "outputs": [{"internalType": "string", "name": "", "type": "string"}],
                    "payable": False,
                    "stateMutability": "view",
                    "type": "function"
                }
            ]
        }
    
    async def initialize(self):
        """Initialize connections"""
        # Redis
        self.redis = await aioredis.from_url(
            self.config.get('redis_url', 'redis://localhost:6379'),
            decode_responses=True
        )
        
        # Kafka (if configured)
        if self.config.get('kafka_bootstrap_servers') and HAS_KAFKA:
            self.kafka_producer = KafkaProducer(
                bootstrap_servers=self.config['kafka_bootstrap_servers'],
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                acks='all',
                retries=3
            )
        
        # Test connections
        try:
            if not await self.w3.is_connected():
                raise ConnectionError("Failed to connect to Cronos RPC")
        except Exception as e:
            logger.warning(f"Web3 connection check failed: {e}")
        
        logger.info("OnChainDataCollector initialized successfully")
    
    async def start_collection(self):
        """Start continuous data collection"""
        self.running = True
        
        # Start collection tasks
        tasks = [
            asyncio.create_task(self._collect_blocks()),
            asyncio.create_task(self._collect_dex_events()),
            asyncio.create_task(self._monitor_gas_prices()),
            asyncio.create_task(self._track_liquidity_changes()),
            asyncio.create_task(self._collect_x402_executions())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("Data collection stopped")
        except Exception as e:
            logger.error(f"Data collection error: {e}")
            raise
    
    async def stop_collection(self):
        """Stop data collection"""
        self.running = False
    
    async def _collect_blocks(self):
        """Continuously collect new blocks"""
        last_block = await self.w3.eth.block_number
        
        while self.running:
            try:
                current_block = await self.w3.eth.block_number
                
                if current_block > last_block:
                    for block_num in range(last_block + 1, min(current_block + 1, last_block + 10)):  # Limit batch size
                        try:
                            block = await self.w3.eth.get_block(block_num, full_transactions=True)
                            
                            # Create data point
                            data_point = RawDataPoint(
                                source=DataSource.CRONOS_BLOCKCHAIN,
                                data_type=DataType.BLOCK,
                                raw_data={
                                    'block_number': block.number,
                                    'timestamp': block.timestamp,
                                    'transactions_count': len(block.transactions),
                                    'gas_used': block.gasUsed,
                                    'gas_limit': block.gasLimit,
                                    'miner': block.miner,
                                    'base_fee_per_gas': block.get('baseFeePerGas', 0)
                                },
                                metadata={
                                    'collected_at': datetime.utcnow().isoformat()
                                }
                            )
                            
                            # Store and publish
                            await self._store_data_point(data_point)
                            await self._publish_to_kafka('blocks', data_point.dict())
                            
                            DATA_POINTS_COLLECTED.labels(
                                source='cronos_blockchain',
                                type='block'
                            ).inc()
                            
                            # Process transactions in block
                            await self._process_transactions(block.transactions, block.number, block.timestamp)
                            
                        except BlockNotFound:
                            logger.warning(f"Block {block_num} not found")
                            continue
                    
                    last_block = current_block
                
                await asyncio.sleep(1)  # Cronos block time ~0.8s
                
            except Exception as e:
                logger.error(f"Block collection error: {e}")
                await asyncio.sleep(5)
    
    async def _process_transactions(self, transactions: List, block_number: int, block_timestamp: int):
        """Process transactions in a block"""
        for tx in transactions:
            try:
                # Create transaction data point
                tx_data = RawDataPoint(
                    source=DataSource.CRONOS_BLOCKCHAIN,
                    data_type=DataType.TRANSACTION,
                    raw_data={
                        'hash': tx.hash.hex() if hasattr(tx.hash, 'hex') else str(tx.hash),
                        'from': tx.get('from', ''),
                        'to': tx.get('to', ''),
                        'value': str(tx.value),
                        'gas': tx.gas,
                        'gas_price': tx.gasPrice,
                        'nonce': tx.nonce,
                        'input': tx.input.hex() if hasattr(tx.input, 'hex') else str(tx.input),
                        'block_number': block_number,
                        'block_timestamp': block_timestamp
                    },
                    metadata={'processed_at': datetime.utcnow().isoformat()}
                )
                
                await self._store_data_point(tx_data)
                await self._publish_to_kafka('transactions', tx_data.dict())
                
                DATA_POINTS_COLLECTED.labels(
                    source='cronos_blockchain',
                    type='transaction'
                ).inc()
                
                # Check if it's a DEX transaction
                await self._analyze_dex_transaction(tx)
                
            except Exception as e:
                logger.error(f"Transaction processing error: {e}")
    
    async def _analyze_dex_transaction(self, tx):
        """Analyze if transaction is a DEX swap"""
        if not tx.to:
            return
        
        for dex_name, dex_info in self.dex_addresses.items():
            if tx.to.lower() == dex_info['router'].lower():
                await self._decode_swap_transaction(tx, dex_name)
                break
    
    async def _decode_swap_transaction(self, tx, dex_name: str):
        """Decode swap transaction"""
        try:
            if len(tx.input) > 10:  # Has function call
                func_sig = tx.input[:10].hex() if hasattr(tx.input, 'hex') else str(tx.input)[:10]
                
                if func_sig == '0x7ff36ab5':  # swapExactETHForTokens
                    decoded = {
                        'function': 'swapExactETHForTokens',
                        'dex': dex_name,
                        'amount_in': str(tx.value),
                        'min_amount_out': '0',
                        'path': [],
                        'to': Web3.to_checksum_address('0x' + str(tx.input)[34:74]) if len(str(tx.input)) > 74 else '',
                        'deadline': int(str(tx.input)[74:138], 16) if len(str(tx.input)) > 138 else 0
                    }
                    
                    swap_data = RawDataPoint(
                        source=getattr(DataSource, dex_name.upper(), DataSource.CRONOS_BLOCKCHAIN),
                        data_type=DataType.SWAP_EVENT,
                        raw_data=decoded,
                        metadata={
                            'tx_hash': tx.hash.hex() if hasattr(tx.hash, 'hex') else str(tx.hash),
                            'block_number': getattr(tx, 'blockNumber', 0),
                            'decoded_at': datetime.utcnow().isoformat()
                        }
                    )
                    
                    await self._store_data_point(swap_data)
                    await self._publish_to_kafka('swap_events', swap_data.dict())
                    
                    DATA_POINTS_COLLECTED.labels(
                        source=dex_name,
                        type='swap_event'
                    ).inc()
                    
        except Exception as e:
            logger.error(f"Swap decoding error: {e}")
    
    async def _collect_dex_events(self):
        """Collect DEX events from subgraphs"""
        while self.running:
            try:
                for dex_name in self.dex_addresses.keys():
                    await self._fetch_dex_subgraph_data(dex_name)
                
                await asyncio.sleep(10)  # Fetch every 10 seconds
                
            except Exception as e:
                logger.error(f"DEX events collection error: {e}")
                await asyncio.sleep(30)
    
    async def _fetch_dex_subgraph_data(self, dex_name: str):
        """Fetch data from DEX subgraph"""
        subgraph_urls = {
            'vvs_finance': 'https://api.thegraph.com/subgraphs/name/vvs-finance/vvs-dex',
            'cronaswap': 'https://api.thegraph.com/subgraphs/name/cronaswap/exchange',
            'mm_finance': 'https://api.thegraph.com/subgraphs/name/mm-finance/cronos'
        }
        
        if dex_name not in subgraph_urls:
            return
        
        queries = {
            'swaps': """
            {
                swaps(
                    first: 100,
                    orderBy: timestamp,
                    orderDirection: desc,
                    where: {timestamp_gt: %d}
                ) {
                    id
                    transaction {
                        id
                    }
                    timestamp
                    pair {
                        id
                        token0 { id symbol decimals }
                        token1 { id symbol decimals }
                    }
                    amount0In amount0Out
                    amount1In amount1Out
                    amountUSD
                }
            }
            """,
            'pairs': """
            {
                pairs(
                    first: 200,
                    orderBy: reserveUSD,
                    orderDirection: desc
                ) {
                    id
                    token0 { id symbol decimals }
                    token1 { id symbol decimals }
                    reserve0 reserve1
                    reserveUSD
                    volumeUSD
                    txCount
                }
            }
            """
        }
        
        try:
            # Get last timestamp from Redis
            last_timestamp_key = f"last_timestamp:{dex_name}:swaps"
            last_timestamp = await self.redis.get(last_timestamp_key)
            if not last_timestamp:
                last_timestamp = int(time.time()) - 3600  # 1 hour ago
            else:
                last_timestamp = int(last_timestamp)
            
            async with aiohttp.ClientSession() as session:
                # Fetch swaps
                query = queries['swaps'] % last_timestamp
                async with session.post(subgraph_urls[dex_name], json={'query': query}) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        swaps = data.get('data', {}).get('swaps', [])
                        
                        for swap in swaps:
                            swap_data = RawDataPoint(
                                source=getattr(DataSource, dex_name.upper(), DataSource.CRONOS_BLOCKCHAIN),
                                data_type=DataType.SWAP_EVENT,
                                raw_data=swap,
                                metadata={
                                    'from_subgraph': True,
                                    'dex': dex_name
                                }
                            )
                            
                            await self._store_data_point(swap_data)
                            
                            # Update last timestamp
                            swap_timestamp = int(swap['timestamp'])
                            if swap_timestamp > last_timestamp:
                                last_timestamp = swap_timestamp
                        
                        # Update Redis
                        await self.redis.set(last_timestamp_key, last_timestamp)
                        
                        DATA_POINTS_COLLECTED.labels(
                            source=dex_name,
                            type='swap_event_subgraph'
                        ).inc(len(swaps))
                
                # Fetch pairs data periodically
                if int(time.time()) % 60 < 10:  # Every minute
                    async with session.post(subgraph_urls[dex_name], 
                                         json={'query': queries['pairs']}) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            pairs = data.get('data', {}).get('pairs', [])
                            
                            for pair in pairs:
                                pool_data = RawDataPoint(
                                    source=getattr(DataSource, dex_name.upper(), DataSource.CRONOS_BLOCKCHAIN),
                                    data_type=DataType.POOL_METADATA,
                                    raw_data=pair,
                                    metadata={'from_subgraph': True}
                                )
                                
                                await self._store_data_point(pool_data)
                            
                            DATA_POINTS_COLLECTED.labels(
                                source=dex_name,
                                type='pool_metadata'
                            ).inc(len(pairs))
                
        except Exception as e:
            logger.error(f"Subgraph fetch error for {dex_name}: {e}")
    
    async def _monitor_gas_prices(self):
        """Monitor gas prices"""
        while self.running:
            try:
                # Get current gas price
                gas_price = await self.w3.eth.gas_price
                
                gas_data = RawDataPoint(
                    source=DataSource.CRONOS_BLOCKCHAIN,
                    data_type=DataType.GAS_PRICE,
                    raw_data={
                        'gas_price_gwei': float(Web3.from_wei(gas_price, 'gwei')),
                        'gas_price_wei': str(gas_price),
                        'timestamp': int(time.time())
                    },
                    metadata={'collected_at': datetime.utcnow().isoformat()}
                )
                
                await self._store_data_point(gas_data)
                await self._publish_to_kafka('gas_prices', gas_data.dict())
                
                # Store in buffer for analysis
                self.data_buffer['gas_prices'].append({
                    'timestamp': datetime.utcnow(),
                    'gas_price_gwei': float(Web3.from_wei(gas_price, 'gwei'))
                })
                
                # Store in Redis for quick access
                await self.redis.set('current_gas_price', str(Web3.from_wei(gas_price, 'gwei')))
                await self.redis.set('latest_block_timestamp', str(time.time()))
                
                DATA_POINTS_COLLECTED.labels(
                    source='cronos_blockchain',
                    type='gas_price'
                ).inc()
                
                await asyncio.sleep(5)  # Every 5 seconds
                
            except Exception as e:
                logger.error(f"Gas price monitoring error: {e}")
                await asyncio.sleep(10)
    
    async def _track_liquidity_changes(self):
        """Track liquidity changes in major pools"""
        major_pools = [
            '0xe61Db569E231B3f5530168Aa2C9D50246525b6d6',  # VVS
            '0xbf62c67eA509E86F07c8c69d0286C0636C50270b',  # CronaSwap
        ]
        
        while self.running:
            try:
                for pool_address in major_pools:
                    await self._get_pool_reserves(pool_address)
                
                await asyncio.sleep(30)  # Every 30 seconds
                
            except Exception as e:
                logger.error(f"Liquidity tracking error: {e}")
                await asyncio.sleep(60)
    
    async def _get_pool_reserves(self, pool_address: str):
        """Get current reserves for a pool"""
        try:
            contract = self.w3.eth.contract(
                address=pool_address,
                abi=self.contract_abis['uniswap_v2_pair']
            )
            
            reserves = await contract.functions.getReserves().call()
            token0 = await contract.functions.token0().call()
            token1 = await contract.functions.token1().call()
            
            liquidity_data = RawDataPoint(
                source=DataSource.CRONOS_BLOCKCHAIN,
                data_type=DataType.LIQUIDITY_EVENT,
                raw_data={
                    'pool_address': pool_address,
                    'token0': token0,
                    'token1': token1,
                    'reserve0': str(reserves[0]),
                    'reserve1': str(reserves[1]),
                    'block_timestamp_last': reserves[2],
                    'timestamp': int(time.time())
                },
                metadata={'collected_at': datetime.utcnow().isoformat()}
            )
            
            await self._store_data_point(liquidity_data)
            
            DATA_POINTS_COLLECTED.labels(
                source='cronos_blockchain',
                type='liquidity_event'
            ).inc()
            
        except Exception as e:
            logger.error(f"Pool reserves error for {pool_address}: {e}")
    
    async def _collect_x402_executions(self):
        """Collect x402 execution data"""
        if 'x402_facilitator' not in self.config:
            return
        
        facilitator_address = self.config['x402_facilitator']
        
        while self.running:
            try:
                # Check for recent x402 transactions
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"x402 collection error: {e}")
                await asyncio.sleep(120)
    
    async def _store_data_point(self, data_point: RawDataPoint):
        """Store data point in Redis"""
        try:
            # Store in Redis with TTL (7 days)
            key = f"data:{data_point.source.value}:{data_point.data_type.value}:{data_point.data_id}"
            
            await self.redis.setex(
                key,
                604800,  # 7 days in seconds
                data_point.json()
            )
            
            # Add to time-series sorted set for temporal queries
            timestamp_score = int(data_point.timestamp.timestamp() * 1000)
            await self.redis.zadd(
                f"data_timeline:{data_point.source.value}:{data_point.data_type.value}",
                {key: timestamp_score}
            )
            
            # Update data buffer
            buffer_key = f"{data_point.source.value}:{data_point.data_type.value}"
            self.data_buffer[buffer_key].append(data_point)
            
        except Exception as e:
            logger.error(f"Data storage error: {e}")
    
    async def _publish_to_kafka(self, topic: str, data: Dict):
        """Publish data to Kafka"""
        if not self.kafka_producer:
            return
        
        try:
            future = self.kafka_producer.send(topic, data)
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: future.get(timeout=10)
            )
        except Exception as e:
            logger.error(f"Kafka publish error: {e}")
    
    async def get_recent_data(self, source: DataSource, data_type: DataType, 
                            limit: int = 100) -> List[RawDataPoint]:
        """Get recent data points"""
        key_pattern = f"data:{source.value}:{data_type.value}:*"
        
        # Get keys from sorted set (most recent first)
        keys = await self.redis.zrevrange(
            f"data_timeline:{source.value}:{data_type.value}",
            0, limit - 1
        )
        
        if not keys:
            return []
        
        # Fetch data points
        data_points = []
        for key in keys:
            data_json = await self.redis.get(key)
            if data_json:
                try:
                    data_dict = json.loads(data_json)
                    data_points.append(RawDataPoint(**data_dict))
                except Exception as e:
                    logger.error(f"Error parsing data point: {e}")
        
        return data_points
    
    async def get_data_range(self, source: DataSource, data_type: DataType,
                           start_time: datetime, end_time: datetime) -> List[RawDataPoint]:
        """Get data points within time range"""
        start_score = int(start_time.timestamp() * 1000)
        end_score = int(end_time.timestamp() * 1000)
        
        keys = await self.redis.zrangebyscore(
            f"data_timeline:{source.value}:{data_type.value}",
            start_score, end_score
        )
        
        data_points = []
        for key in keys:
            data_json = await self.redis.get(key)
            if data_json:
                try:
                    data_dict = json.loads(data_json)
                    data_points.append(RawDataPoint(**data_dict))
                except Exception as e:
                    logger.error(f"Error parsing data point: {e}")
        
        return data_points

# ============================================================================
# 2. Market Data Streamer (Crypto.com MCP Integration)
# ============================================================================

class MarketDataStreamer:
    """Streams market data from Crypto.com MCP and other sources"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.redis = None
        self.mcp_session = None
        self.running = False
        
        # Crypto.com MCP configuration
        self.mcp_base_url = config.get('mcp_base_url', "https://mcp.crypto.com")
        self.api_key = config.get('crypto_com_api_key', '')
        
        # External data sources
        self.data_sources = {
            'coingecko': {
                'base_url': 'https://api.coingecko.com/api/v3',
                'endpoints': {
                    'price': '/simple/price',
                    'market_chart': '/coins/{id}/market_chart'
                }
            }
        }
        
        # Market data cache
        self.market_cache = {}
        self.cache_ttl = 300  # 5 minutes
        
        logger.info("MarketDataStreamer initialized")
    
    async def initialize(self):
        """Initialize connections"""
        self.redis = await aioredis.from_url(
            self.config.get('redis_url', 'redis://localhost:6379'),
            decode_responses=True
        )
        
        logger.info("MarketDataStreamer initialized successfully")
    
    async def start_streaming(self):
        """Start market data streaming"""
        self.running = True
        
        tasks = [
            asyncio.create_task(self._stream_external_price_feeds()),
            asyncio.create_task(self._update_token_metadata())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("Market data streaming stopped")
        except Exception as e:
            logger.error(f"Market data streaming error: {e}")
            raise
    
    async def stop_streaming(self):
        """Stop market data streaming"""
        self.running = False
    
    async def _stream_external_price_feeds(self):
        """Stream price feeds from external sources"""
        while self.running:
            try:
                # CoinGecko data
                await self._fetch_coingecko_data()
                
                await asyncio.sleep(60)  # Every minute
                
            except Exception as e:
                logger.error(f"External price feeds error: {e}")
                await asyncio.sleep(120)
    
    async def _fetch_coingecko_data(self):
        """Fetch data from CoinGecko"""
        try:
            token_ids = {
                'crypto-com-chain': 'CRO',
                'usd-coin': 'USDC',
                'tether': 'USDT',
                'wrapped-bitcoin': 'WBTC',
                'ethereum': 'ETH',
            }
            
            token_list = ','.join(token_ids.keys())
            url = f"{self.data_sources['coingecko']['base_url']}/simple/price"
            
            params = {
                'ids': token_list,
                'vs_currencies': 'usd',
                'include_market_cap': 'true',
                'include_24hr_vol': 'true',
                'include_24hr_change': 'true',
                'include_last_updated_at': 'true'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        for coin_id, token_symbol in token_ids.items():
                            if coin_id in data:
                                coin_data = data[coin_id]
                                
                                price_data = RawDataPoint(
                                    source=DataSource.COINGECKO,
                                    data_type=DataType.PRICE_FEED,
                                    raw_data={
                                        'token': token_symbol,
                                        'price_usd': coin_data.get('usd', 0),
                                        'market_cap_usd': coin_data.get('usd_market_cap', 0),
                                        'volume_24h_usd': coin_data.get('usd_24h_vol', 0),
                                        'price_change_24h': coin_data.get('usd_24h_change', 0),
                                        'last_updated': coin_data.get('last_updated_at', 0)
                                    },
                                    metadata={'source': 'coingecko', 'token_id': coin_id}
                                )
                                
                                await self._store_market_data(price_data)
                                
                                # Update cache
                                await self.redis.set('latest_price_timestamp', str(time.time()))
                                
                                DATA_POINTS_COLLECTED.labels(
                                    source='coingecko',
                                    type='price_feed'
                                ).inc()
                        
        except Exception as e:
            logger.error(f"CoinGecko data error: {e}")
    
    async def _update_token_metadata(self):
        """Update token metadata"""
        while self.running:
            try:
                await asyncio.sleep(3600)  # Every hour
            except Exception as e:
                logger.error(f"Token metadata update error: {e}")
                await asyncio.sleep(7200)
    
    async def _store_market_data(self, data_point: RawDataPoint):
        """Store market data"""
        try:
            key = f"market_data:{data_point.source.value}:{data_point.data_id}"
            
            await self.redis.setex(
                key,
                self.cache_ttl,
                data_point.json()
            )
            
            timestamp_score = int(data_point.timestamp.timestamp() * 1000)
            await self.redis.zadd(
                f"market_timeline:{data_point.source.value}",
                {key: timestamp_score}
            )
            
        except Exception as e:
            logger.error(f"Market data storage error: {e}")

# ============================================================================
# 3. Feature Engineering Pipeline
# ============================================================================

class FeatureEngineeringPipeline:
    """Pipeline for feature engineering"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.redis = None
        self.feature_registry = {}
        self.feature_sets = {}
        self.window_sizes = {
            'short': 60,
            'medium': 3600,
            'long': 86400,
        }
        
        self._initialize_feature_definitions()
        logger.info("FeatureEngineeringPipeline initialized")
    
    def _initialize_feature_definitions(self):
        """Initialize feature definitions"""
        self.feature_sets['slippage_prediction'] = {
            'features': [
                {'name': 'amount_usd', 'type': 'numerical', 'source': 'trade'},
                {'name': 'amount_to_liquidity_ratio', 'type': 'numerical', 'source': 'calculated'},
                {'name': 'market_volatility_1h', 'type': 'numerical', 'source': 'market'},
                {'name': 'market_volatility_24h', 'type': 'numerical', 'source': 'market'},
                {'name': 'total_liquidity_usd', 'type': 'numerical', 'source': 'onchain'},
                {'name': 'gas_price_gwei', 'type': 'numerical', 'source': 'onchain'},
                {'name': 'hour_of_day', 'type': 'categorical', 'source': 'time'},
                {'name': 'day_of_week', 'type': 'categorical', 'source': 'time'},
            ],
            'window_sizes': ['short', 'medium', 'long']
        }
    
    async def initialize(self):
        """Initialize pipeline"""
        self.redis = await aioredis.from_url(
            self.config.get('redis_url', 'redis://localhost:6379'),
            decode_responses=True
        )
        logger.info("FeatureEngineeringPipeline initialized successfully")
    
    async def generate_features(self, entity_id: str, feature_set: str,
                              timestamp: datetime) -> Optional[ProcessedFeature]:
        """Generate features for an entity"""
        if feature_set not in self.feature_sets:
            logger.error(f"Unknown feature set: {feature_set}")
            return None
        
        try:
            start_time = time.time()
            
            entity_type, identifier = entity_id.split(':', 1) if ':' in entity_id else ('unknown', entity_id)
            
            if entity_type == 'trade':
                features = await self._generate_trade_features(identifier, feature_set, timestamp)
            else:
                features = {}
            
            feature_defs = self.feature_sets[feature_set]['features']
            feature_names = [f['name'] for f in feature_defs]
            feature_vector = [features.get(name, 0.0) for name in feature_names]
            
            processed_feature = ProcessedFeature(
                feature_id=f"feature_{entity_id}_{feature_set}_{int(timestamp.timestamp())}",
                timestamp=timestamp,
                entity_id=entity_id,
                feature_set=feature_set,
                feature_vector=feature_vector,
                feature_names=feature_names,
                metadata={
                    'generation_time_ms': int((time.time() - start_time) * 1000),
                    'feature_count': len(feature_vector),
                    'entity_type': entity_type
                }
            )
            
            await self._store_feature(processed_feature)
            DATA_PROCESSING_TIME.labels(operation='feature_generation').observe(
                time.time() - start_time
            )
            
            return processed_feature
            
        except Exception as e:
            logger.error(f"Feature generation error: {e}")
            return None
    
    async def _generate_trade_features(self, trade_id: str, feature_set: str,
                                     timestamp: datetime) -> Dict[str, float]:
        """Generate features for a trade"""
        features = {}
        
        if feature_set == 'slippage_prediction':
            features['amount_usd'] = 5000.0  # Mock
            features['amount_to_liquidity_ratio'] = 0.0025
            features['market_volatility_1h'] = 0.05
            features['market_volatility_24h'] = 0.15
            features['total_liquidity_usd'] = 2000000.0
            features['gas_price_gwei'] = 10.0
            features['hour_of_day'] = timestamp.hour / 24
            features['day_of_week'] = timestamp.weekday() / 7
        
        return features
    
    async def _store_feature(self, feature: ProcessedFeature):
        """Store feature in feature store"""
        try:
            key = f"feature:{feature.entity_id}:{feature.feature_set}:{feature.timestamp.timestamp()}"
            
            await self.redis.setex(
                key,
                604800,
                feature.json()
            )
            
            await self.redis.zadd(
                f"feature_store:{feature.entity_id}:{feature.feature_set}",
                {key: feature.timestamp.timestamp()}
            )
            
        except Exception as e:
            logger.error(f"Feature storage error: {e}")

# ============================================================================
# 4. Label Generation System
# ============================================================================

class LabelGenerationSystem:
    """Generates labels for supervised learning"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.redis = None
        self.label_definitions = self._initialize_label_definitions()
        logger.info("LabelGenerationSystem initialized")
    
    def _initialize_label_definitions(self):
        """Initialize label definitions"""
        return {
            'slippage': {
                'type': 'regression',
                'description': 'Actual slippage percentage',
                'range': (0, 0.5),
            },
            'execution_success': {
                'type': 'binary',
                'description': 'Whether execution was successful',
                'values': [0, 1]
            }
        }
    
    async def initialize(self):
        """Initialize system"""
        self.redis = await aioredis.from_url(
            self.config.get('redis_url', 'redis://localhost:6379'),
            decode_responses=True
        )
        logger.info("LabelGenerationSystem initialized successfully")
    
    async def generate_label(self, execution_result: Dict[str, Any]) -> Optional[DataLabel]:
        """Generate labels from execution result"""
        if not execution_result.get('success'):
            return await self._generate_failure_labels(execution_result)
        
        try:
            label_id = f"label_{execution_result.get('result_id', 'unknown')}"
            timestamp = datetime.utcnow()
            
            trade_data = execution_result.get('trade_data', {})
            expected_output = trade_data.get('expected_output', 0)
            actual_output = execution_result.get('actual_amount_out', 0)
            
            if expected_output > 0 and actual_output > 0:
                slippage = abs(actual_output / expected_output - 1)
                slippage_label = DataLabel(
                    label_id=f"{label_id}_slippage",
                    timestamp=timestamp,
                    entity_id=trade_data.get('entity_id', 'unknown'),
                    label_type='slippage',
                    label_value=float(slippage),
                    confidence=0.9,
                    source_data_ids=[execution_result.get('result_id', '')],
                    metadata={'calculation_method': 'actual_vs_expected'}
                )
                
                await self._store_label(slippage_label)
                return slippage_label
            
        except Exception as e:
            logger.error(f"Label generation error: {e}")
            return None
    
    async def _generate_failure_labels(self, execution_result: Dict[str, Any]) -> Optional[DataLabel]:
        """Generate labels for failed execution"""
        try:
            label_id = f"label_{execution_result.get('result_id', 'unknown')}_failure"
            timestamp = datetime.utcnow()
            trade_data = execution_result.get('trade_data', {})
            
            failure_label = DataLabel(
                label_id=label_id,
                timestamp=timestamp,
                entity_id=trade_data.get('entity_id', 'unknown'),
                label_type='execution_success',
                label_value=0.0,
                confidence=1.0,
                source_data_ids=[execution_result.get('result_id', '')],
                metadata={
                    'outcome': 'failure',
                    'error': execution_result.get('error', 'unknown')
                }
            )
            
            await self._store_label(failure_label)
            return failure_label
            
        except Exception as e:
            logger.error(f"Failure label generation error: {e}")
            return None
    
    async def _store_label(self, label: DataLabel):
        """Store label in Redis"""
        try:
            key = f"label:{label.entity_id}:{label.label_type}:{label.label_id}"
            
            await self.redis.setex(
                key,
                604800,
                label.json()
            )
            
            await self.redis.zadd(
                f"label_index:{label.entity_id}:{label.label_type}",
                {key: label.timestamp.timestamp()}
            )
            
        except Exception as e:
            logger.error(f"Label storage error: {e}")

# ============================================================================
# 5. Data Validation & Quality Monitoring
# ============================================================================

class DataQualityMonitor:
    """Monitors data quality and validates incoming data"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.redis = None
        self.quality_thresholds = self._initialize_quality_thresholds()
        self.quality_metrics = {}
        logger.info("DataQualityMonitor initialized")
    
    def _initialize_quality_thresholds(self):
        """Initialize data quality thresholds"""
        return {
            'freshness': {
                'block_data': 10,
                'price_data': 30,
                'liquidity_data': 60,
            },
            'completeness': {
                'required_fields': 0.95,
                'data_points': 0.90,
            }
        }
    
    async def initialize(self):
        """Initialize monitor"""
        self.redis = await aioredis.from_url(
            self.config.get('redis_url', 'redis://localhost:6379'),
            decode_responses=True
        )
        asyncio.create_task(self._continuous_quality_monitoring())
        logger.info("DataQualityMonitor initialized successfully")
    
    async def _continuous_quality_monitoring(self):
        """Continuously monitor data quality"""
        while True:
            try:
                await self._check_all_quality_metrics()
                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"Quality monitoring error: {e}")
                await asyncio.sleep(300)
    
    async def _check_all_quality_metrics(self):
        """Check all quality metrics"""
        metrics = {}
        
        freshness_metrics = await self._check_freshness()
        metrics.update(freshness_metrics)
        
        overall_score = self._calculate_overall_quality(metrics)
        metrics['overall_quality_score'] = overall_score
        
        DATA_QUALITY_SCORE.set(overall_score)
        self.quality_metrics = metrics
        
        return metrics
    
    async def _check_freshness(self) -> Dict[str, float]:
        """Check data freshness"""
        metrics = {}
        
        try:
            latest_block_key = await self.redis.get('latest_block_timestamp')
            if latest_block_key:
                latest_block_time = float(latest_block_key)
                current_time = time.time()
                block_age = current_time - latest_block_time
                
                freshness_score = max(0, 100 - (block_age / self.quality_thresholds['freshness']['block_data']) * 100)
                metrics['block_freshness_score'] = freshness_score
        except Exception as e:
            logger.error(f"Block freshness check error: {e}")
        
        return metrics
    
    def _calculate_overall_quality(self, metrics: Dict[str, float]) -> float:
        """Calculate overall data quality score"""
        if not metrics:
            return 50.0
        
        weights = {
            'block_freshness_score': 0.3,
            'price_freshness_score': 0.3,
            'completeness_score': 0.4
        }
        
        total_score = 0
        total_weight = 0
        
        for metric_name, weight in weights.items():
            if metric_name in metrics:
                total_score += metrics[metric_name] * weight
                total_weight += weight
        
        if total_weight > 0:
            overall_score = total_score / total_weight
        else:
            overall_score = 50.0
        
        return round(overall_score, 2)
    
    async def validate_data_point(self, data_point: RawDataPoint) -> Dict[str, Any]:
        """Validate a single data point"""
        validation_result = {
            'is_valid': True,
            'warnings': [],
            'errors': [],
            'score': 100
        }
        
        try:
            required_fields = ['source', 'data_type', 'timestamp', 'raw_data']
            for field in required_fields:
                if not hasattr(data_point, field) or getattr(data_point, field) is None:
                    validation_result['errors'].append(f"Missing required field: {field}")
                    validation_result['is_valid'] = False
            
            data_age = (datetime.utcnow() - data_point.timestamp).total_seconds()
            if data_age > 3600:
                validation_result['warnings'].append(f"Data is {data_age:.0f} seconds old")
                validation_result['score'] *= max(0, 1 - data_age / 86400)
            
            validation_result['score'] = round(validation_result['score'], 2)
            return validation_result
            
        except Exception as e:
            logger.error(f"Data validation error: {e}")
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"Validation error: {str(e)}")
            validation_result['score'] = 0
            return validation_result
    
    async def get_quality_report(self, hours: int = 24) -> Dict[str, Any]:
        """Get quality report for specified time period"""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        report = {
            'time_period': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat(),
                'hours': hours
            },
            'overall_quality': self.quality_metrics.get('overall_quality_score', 0),
            'metrics': {},
            'issues': [],
            'recommendations': []
        }
        
        overall_quality = report['overall_quality']
        if overall_quality < 70:
            report['issues'].append(f"Low overall data quality: {overall_quality}%")
            report['recommendations'].append("Check data sources and collection processes")
        
        return report

# ============================================================================
# 6. Feature Store & Vector Database
# ============================================================================

class FeatureStore:
    """Feature store with vector database capabilities"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.redis = None
        self.feature_schemas = {}
        logger.info("FeatureStore initialized")
    
    async def initialize(self):
        """Initialize feature store"""
        self.redis = await aioredis.from_url(
            self.config.get('redis_url', 'redis://localhost:6379'),
            decode_responses=False
        )
        asyncio.create_task(self._monitor_store_size())
        logger.info("FeatureStore initialized successfully")
    
    async def _monitor_store_size(self):
        """Monitor feature store size"""
        while True:
            try:
                info = await self.redis.info('memory')
                used_memory = info.get('used_memory', 0)
                used_memory_mb = used_memory / (1024 * 1024)
                
                FEATURE_STORE_SIZE.set(used_memory_mb)
                
                if used_memory_mb > 1000:
                    logger.warning(f"Feature store size: {used_memory_mb:.1f}MB")
                
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Store size monitoring error: {e}")
                await asyncio.sleep(300)
    
    async def store_feature_vector(self, feature: ProcessedFeature, 
                                 metadata: Optional[Dict] = None) -> str:
        """Store feature vector in feature store"""
        try:
            record_id = f"feature_vec_{feature.feature_id}"
            
            features_dict = dict(zip(feature.feature_names, feature.feature_vector))
            
            record = FeatureStoreRecord(
                record_id=record_id,
                entity_id=feature.entity_id,
                timestamp=feature.timestamp,
                features=features_dict,
                metadata={
                    'feature_set': feature.feature_set,
                    'version': feature.version,
                    **(metadata or {})
                }
            )
            
            await self._store_record(record)
            await self._update_feature_schema(feature.feature_set, feature.feature_names)
            
            return record_id
            
        except Exception as e:
            logger.error(f"Feature vector storage error: {e}")
            raise
    
    async def _store_record(self, record: FeatureStoreRecord):
        """Store record in Redis"""
        try:
            record_bytes = pickle.dumps(record.dict())
            
            if len(record_bytes) > 1000:
                record_bytes = zlib.compress(record_bytes)
            
            key = f"feature_store:record:{record.record_id}"
            await self.redis.setex(key, 2592000, record_bytes)
            
            entity_key = f"feature_store:entity:{record.entity_id}"
            await self.redis.zadd(entity_key, {record.record_id: record.timestamp.timestamp()})
            
        except Exception as e:
            logger.error(f"Record storage error: {e}")
    
    async def _update_feature_schema(self, feature_set: str, feature_names: List[str]):
        """Update feature schema"""
        if feature_set not in self.feature_schemas:
            self.feature_schemas[feature_set] = {
                'feature_names': feature_names,
                'first_seen': datetime.utcnow().isoformat(),
                'last_updated': datetime.utcnow().isoformat(),
                'sample_count': 1
            }
        else:
            schema = self.feature_schemas[feature_set]
            schema['last_updated'] = datetime.utcnow().isoformat()
            schema['sample_count'] += 1

# ============================================================================
# 7. Real-time Data Serving Layer
# ============================================================================

class DataServingLayer:
    """Serves data to AI agents in real-time"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.redis = None
        self.data_cache = {}
        self.subscriptions = defaultdict(set)
        logger.info("DataServingLayer initialized")
    
    async def initialize(self):
        """Initialize serving layer"""
        self.redis = await aioredis.from_url(
            self.config.get('redis_url', 'redis://localhost:6379'),
            decode_responses=True
        )
        asyncio.create_task(self._warm_cache())
        logger.info("DataServingLayer initialized successfully")
    
    async def _warm_cache(self):
        """Warm up data cache"""
        while True:
            try:
                await self._cache_market_data()
                await self._cache_gas_data()
                await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"Cache warming error: {e}")
                await asyncio.sleep(60)
    
    async def _cache_market_data(self):
        """Cache market data"""
        tokens = ['CRO', 'USDC', 'USDT', 'WETH', 'WBTC']
        
        for token in tokens:
            sources = ['coingecko']
            
            for source in sources:
                key = f"market_data:{source}:price:{token}"
                data_json = await self.redis.get(key)
                
                if data_json:
                    data = json.loads(data_json)
                    cache_key = f"market:{token}:{source}"
                    self.data_cache[cache_key] = {
                        'data': data,
                        'timestamp': time.time()
                    }
    
    async def _cache_gas_data(self):
        """Cache gas data"""
        key = 'current_gas_price'
        gas_price = await self.redis.get(key)
        
        if gas_price:
            self.data_cache['gas:current'] = {
                'price_gwei': float(gas_price),
                'timestamp': time.time()
            }
    
    async def get_market_data(self, token: str, source: str = 'any') -> Optional[Dict[str, Any]]:
        """Get market data for a token"""
        cache_key = f"market:{token}" if source == 'any' else f"market:{token}:{source}"
        
        cached = self.data_cache.get(cache_key)
        if cached and time.time() - cached['timestamp'] < 30:
            return cached.get('data', cached)
        
        return None
    
    async def get_gas_data(self) -> Dict[str, Any]:
        """Get current gas data"""
        cache_key = 'gas:current'
        cached = self.data_cache.get(cache_key)
        
        if cached and time.time() - cached['timestamp'] < 10:
            return cached
        
        gas_price = await self.redis.get('current_gas_price')
        
        if gas_price:
            data = {
                'price_gwei': float(gas_price),
                'timestamp': time.time(),
                'source': 'cronos_rpc'
            }
            self.data_cache[cache_key] = data
            return data
        
        return {
            'price_gwei': 10.0,
            'timestamp': time.time(),
            'source': 'default'
        }

# ============================================================================
# 8. Data Versioning & Lineage Tracking
# ============================================================================

class DataVersioningSystem:
    """Tracks data versioning and lineage"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.redis = None
        self.lineage_graph = defaultdict(set)
        logger.info("DataVersioningSystem initialized")
    
    async def initialize(self):
        """Initialize system"""
        self.redis = await aioredis.from_url(
            self.config.get('redis_url', 'redis://localhost:6379'),
            decode_responses=True
        )
        logger.info("DataVersioningSystem initialized successfully")
    
    async def track_data_lineage(self, output_id: str, input_ids: List[str],
                               operation: str, metadata: Dict[str, Any]):
        """Track data lineage"""
        try:
            lineage_id = f"lineage_{output_id}_{int(time.time() * 1000)}"
            
            lineage_record = {
                'lineage_id': lineage_id,
                'output_id': output_id,
                'input_ids': input_ids,
                'operation': operation,
                'metadata': metadata,
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0'
            }
            
            await self._store_lineage_record(lineage_record)
            
            for input_id in input_ids:
                self.lineage_graph[input_id].add(output_id)
            
            self.lineage_graph[output_id].update(input_ids)
            
            return lineage_id
            
        except Exception as e:
            logger.error(f"Lineage tracking error: {e}")
            return None
    
    async def _store_lineage_record(self, record: Dict[str, Any]):
        """Store lineage record"""
        try:
            key = f"lineage:record:{record['lineage_id']}"
            
            await self.redis.setex(
                key,
                604800,
                json.dumps(record)
            )
            
            await self.redis.sadd(f"lineage:output:{record['output_id']}", record['lineage_id'])
            
            for input_id in record['input_ids']:
                await self.redis.sadd(f"lineage:input:{input_id}", record['lineage_id'])
            
        except Exception as e:
            logger.error(f"Lineage record storage error: {e}")

# ============================================================================
# Main Data Pipeline Orchestrator
# ============================================================================

class CLEODataPipeline:
    """Orchestrates the complete C.L.E.O. data pipeline"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.running = False
        
        # Initialize components
        self.data_collector = OnChainDataCollector(config)
        self.market_streamer = MarketDataStreamer(config)
        self.feature_pipeline = FeatureEngineeringPipeline(config)
        self.label_system = LabelGenerationSystem(config)
        self.quality_monitor = DataQualityMonitor(config)
        self.feature_store = FeatureStore(config)
        self.data_serving = DataServingLayer(config)
        self.versioning_system = DataVersioningSystem(config)
        
        # Data pipeline state
        self.pipeline_state = {
            'data_collection': 'stopped',
            'market_streaming': 'stopped',
            'feature_generation': 'stopped',
            'quality_monitoring': 'stopped',
            'data_serving': 'stopped'
        }
        
        logger.info("C.L.E.O. Data Pipeline initialized")
    
    async def initialize(self):
        """Initialize all components"""
        logger.info("Initializing C.L.E.O. Data Pipeline...")
        
        await self.data_collector.initialize()
        await self.market_streamer.initialize()
        await self.feature_pipeline.initialize()
        await self.label_system.initialize()
        await self.quality_monitor.initialize()
        await self.feature_store.initialize()
        await self.data_serving.initialize()
        await self.versioning_system.initialize()
        
        logger.info("C.L.E.O. Data Pipeline initialized successfully")
    
    async def start(self):
        """Start the complete data pipeline"""
        if self.running:
            logger.warning("Data pipeline already running")
            return
        
        logger.info("Starting C.L.E.O. Data Pipeline...")
        self.running = True
        
        tasks = []
        
        tasks.append(asyncio.create_task(self._start_data_collection()))
        tasks.append(asyncio.create_task(self._start_market_streaming()))
        tasks.append(asyncio.create_task(self._periodic_feature_generation()))
        tasks.append(asyncio.create_task(self._monitor_pipeline()))
        
        self.pipeline_state['data_collection'] = 'running'
        self.pipeline_state['market_streaming'] = 'running'
        self.pipeline_state['feature_generation'] = 'running'
        self.pipeline_state['quality_monitoring'] = 'running'
        self.pipeline_state['data_serving'] = 'running'
        
        if self.config.get('enable_prometheus', False) and HAS_PROMETHEUS:
            start_http_server(self.config.get('prometheus_port', 8000))
            logger.info(f"Prometheus metrics server started on port {self.config.get('prometheus_port', 8000)}")
        
        logger.info("C.L.E.O. Data Pipeline started successfully")
        
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("Data pipeline stopped")
        except Exception as e:
            logger.error(f"Data pipeline error: {e}")
            raise
    
    async def stop(self):
        """Stop the data pipeline"""
        logger.info("Stopping C.L.E.O. Data Pipeline...")
        self.running = False
        
        await self.data_collector.stop_collection()
        await self.market_streamer.stop_streaming()
        
        for key in self.pipeline_state:
            self.pipeline_state[key] = 'stopped'
        
        logger.info("C.L.E.O. Data Pipeline stopped")
    
    async def _start_data_collection(self):
        """Start data collection"""
        try:
            await self.data_collector.start_collection()
        except Exception as e:
            logger.error(f"Data collection failed: {e}")
            self.pipeline_state['data_collection'] = 'failed'
    
    async def _start_market_streaming(self):
        """Start market streaming"""
        try:
            await self.market_streamer.start_streaming()
        except Exception as e:
            logger.error(f"Market streaming failed: {e}")
            self.pipeline_state['market_streaming'] = 'failed'
    
    async def _periodic_feature_generation(self):
        """Periodically generate features"""
        while self.running:
            try:
                await self._generate_features_for_active_entities()
                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"Feature generation error: {e}")
                await asyncio.sleep(300)
    
    async def _generate_features_for_active_entities(self):
        """Generate features for active entities"""
        active_entities = await self._get_active_entities()
        
        for entity_id in active_entities:
            if entity_id.startswith('trade:'):
                feature_set = 'slippage_prediction'
            else:
                continue
            
            feature = await self.feature_pipeline.generate_features(
                entity_id, feature_set, datetime.utcnow()
            )
            
            if feature:
                await self.feature_store.store_feature_vector(feature)
                
                await self.versioning_system.track_data_lineage(
                    output_id=feature.feature_id,
                    input_ids=[f"trade:{entity_id.split(':')[1]}"],
                    operation='feature_generation',
                    metadata={'feature_set': feature_set}
                )
    
    async def _get_active_entities(self) -> List[str]:
        """Get active entities from Redis"""
        try:
            return [
                'trade:test_trade_001',
                'pool:0xe61Db569E231B3f5530168Aa2C9D50246525b6d6',
                'token_pair:CRO/USDC'
            ]
        except Exception as e:
            logger.error(f"Active entities retrieval error: {e}")
            return []
    
    async def _monitor_pipeline(self):
        """Monitor pipeline health"""
        while self.running:
            try:
                health = await self.get_health_status()
                
                for component, status in health['components'].items():
                    if status['status'] != 'healthy':
                        logger.warning(f"Component {component} is {status['status']}: {status.get('details', '')}")
                
                for component in self.pipeline_state:
                    if component in health['components']:
                        if health['components'][component]['status'] == 'healthy':
                            self.pipeline_state[component] = 'running'
                        else:
                            self.pipeline_state[component] = 'degraded'
                
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Pipeline monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get pipeline health status"""
        health = {
            'overall': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'components': {},
            'metrics': {}
        }
        
        # Check Redis
        try:
            await self.data_collector.redis.ping()
            health['components']['redis'] = {'status': 'healthy'}
        except:
            health['components']['redis'] = {'status': 'unhealthy', 'details': 'Connection failed'}
            health['overall'] = 'degraded'
        
        # Check Web3
        try:
            await self.data_collector.w3.eth.block_number
            health['components']['web3'] = {'status': 'healthy'}
        except:
            health['components']['web3'] = {'status': 'unhealthy', 'details': 'Connection failed'}
            health['overall'] = 'degraded'
        
        # Get quality metrics
        quality_report = await self.quality_monitor.get_quality_report(hours=1)
        health['metrics']['data_quality'] = quality_report.get('overall_quality', 0)
        
        return health
