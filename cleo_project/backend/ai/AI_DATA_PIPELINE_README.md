# C.L.E.O. AI Data Pipeline

Complete implementation of the AI data pipeline for the Cronos Liquidity Execution Orchestrator.

## Overview

The AI Data Pipeline is a comprehensive system for collecting, processing, and serving data to AI agents. It consists of 8 main components:

1. **On-chain Data Collectors** - Collects data from Cronos blockchain and DEXs
2. **Market Data Streamers** - Streams market data from Crypto.com MCP and external APIs
3. **Feature Engineering Pipeline** - Generates ML features from raw data
4. **Label Generation System** - Creates labels for supervised learning
5. **Data Validation & Quality Monitoring** - Monitors and validates data quality
6. **Feature Store & Vector Database** - Stores and indexes features for ML models
7. **Real-time Data Serving Layer** - Serves data to AI agents in real-time
8. **Data Versioning & Lineage Tracking** - Tracks data lineage and versions

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    C.L.E.O. AI Data Pipeline                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ On-Chain      │  │ Market Data │  │ Feature      │     │
│  │ Collectors    │  │ Streamers    │  │ Engineering  │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                  │                  │             │
│         └──────────────────┼──────────────────┘             │
│                            │                                 │
│                   ┌────────▼────────┐                        │
│                   │   Redis Store   │                        │
│                   └────────┬────────┘                        │
│                            │                                 │
│         ┌──────────────────┼──────────────────┐             │
│         │                  │                  │             │
│  ┌──────▼──────┐  ┌────────▼────────┐  ┌──────▼──────┐     │
│  │ Label       │  │ Quality Monitor │  │ Feature     │     │
│  │ Generation  │  │                 │  │ Store       │     │
│  └─────────────┘  └─────────────────┘  └─────────────┘     │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Real-time Data Serving Layer                  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Data Versioning & Lineage Tracking             │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Installation

### Dependencies

Install required dependencies:

```bash
pip install -r requirements.txt
```

### Optional Dependencies

For Kafka support:
```bash
pip install kafka-python
```

For Prometheus metrics:
```bash
pip install prometheus-client
```

### Redis Setup

The pipeline requires Redis for data storage. Install and start Redis:

```bash
# Using Docker
docker run -d -p 6379:6379 redis:latest

# Or install locally
# macOS: brew install redis
# Ubuntu: sudo apt-get install redis-server
```

## Configuration

Set environment variables:

```bash
# Required
export CRONOS_RPC="https://evm-t3.cronos.org"
export REDIS_URL="redis://localhost:6379"

# Optional
export CRYPTO_COM_API_KEY="your_api_key"
export X402_FACILITATOR="0x..."
export KAFKA_BOOTSTRAP_SERVERS="localhost:9092"
export ENABLE_PROMETHEUS="true"
export PROMETHEUS_PORT="8000"
```

## Usage

### Basic Usage

```python
import asyncio
from ai.ai_data_pipeline import CLEODataPipeline

async def main():
    config = {
        'cronos_rpc': 'https://evm-t3.cronos.org',
        'redis_url': 'redis://localhost:6379',
    }
    
    pipeline = CLEODataPipeline(config)
    await pipeline.initialize()
    await pipeline.start()
    
    # Pipeline runs in background
    # Access data through pipeline components
    
    # Get market data
    market_data = await pipeline.data_serving.get_market_data('CRO')
    
    # Get gas data
    gas_data = await pipeline.data_serving.get_gas_data()
    
    # Get quality report
    quality = await pipeline.quality_monitor.get_quality_report()

asyncio.run(main())
```

### Integration with Main Application

Add to `main.py`:

```python
from ai.ai_data_pipeline import CLEODataPipeline

# In startup_event()
ai_data_pipeline = None

if os.getenv('ENABLE_AI_DATA_PIPELINE', 'false').lower() == 'true':
    config = {
        'cronos_rpc': os.getenv("CRONOS_RPC", "https://evm-t3.cronos.org"),
        'redis_url': os.getenv("REDIS_URL", "redis://localhost:6379"),
        'crypto_com_api_key': os.getenv('CRYPTO_COM_API_KEY', ''),
        'x402_facilitator': os.getenv('X402_FACILITATOR', ''),
    }
    ai_data_pipeline = CLEODataPipeline(config)
    await ai_data_pipeline.initialize()
    asyncio.create_task(ai_data_pipeline.start())
```

## Components

### 1. On-chain Data Collectors

Collects data from:
- Cronos blockchain (blocks, transactions)
- DEX events (VVS Finance, CronaSwap, MM Finance)
- Gas prices
- Liquidity pool reserves
- x402 facilitator executions

**Usage:**
```python
# Get recent swap events
swaps = await pipeline.data_collector.get_recent_data(
    DataSource.VVS_FINANCE,
    DataType.SWAP_EVENT,
    limit=100
)

# Get data in time range
from datetime import datetime, timedelta
end_time = datetime.utcnow()
start_time = end_time - timedelta(hours=24)

blocks = await pipeline.data_collector.get_data_range(
    DataSource.CRONOS_BLOCKCHAIN,
    DataType.BLOCK,
    start_time,
    end_time
)
```

### 2. Market Data Streamers

Streams market data from:
- CoinGecko API
- Crypto.com MCP (if API key provided)
- Chainlink price feeds

**Usage:**
```python
# Market data is automatically streamed
# Access cached data through serving layer
market_data = await pipeline.data_serving.get_market_data('CRO', 'coingecko')
```

### 3. Feature Engineering Pipeline

Generates ML features for:
- Slippage prediction
- Risk assessment
- Route optimization

**Usage:**
```python
# Generate features for an entity
feature = await pipeline.feature_pipeline.generate_features(
    entity_id='trade:trade_001',
    feature_set='slippage_prediction',
    timestamp=datetime.utcnow()
)

# Get latest features
features = await pipeline.feature_pipeline.get_latest_features(
    entity_id='trade:trade_001',
    feature_set='slippage_prediction',
    limit=10
)
```

### 4. Label Generation System

Generates labels from execution results:
- Actual slippage
- Execution success/failure
- Gas efficiency
- Execution speed

**Usage:**
```python
# Generate labels from execution result
execution_result = {
    'result_id': 'exec_001',
    'success': True,
    'actual_amount_out': 5000.0,
    'trade_data': {
        'entity_id': 'trade:trade_001',
        'expected_output': 5100.0
    }
}

label = await pipeline.label_system.generate_label(execution_result)
```

### 5. Data Quality Monitor

Monitors:
- Data freshness
- Data completeness
- Data accuracy
- Data consistency

**Usage:**
```python
# Get quality report
report = await pipeline.quality_monitor.get_quality_report(hours=24)
print(f"Overall Quality: {report['overall_quality']}%")

# Validate data point
validation = await pipeline.quality_monitor.validate_data_point(data_point)
if not validation['is_valid']:
    print(f"Errors: {validation['errors']}")
```

### 6. Feature Store

Stores and indexes features for ML models:
- Feature vectors
- Feature schemas
- Similarity search

**Usage:**
```python
# Store feature vector
record_id = await pipeline.feature_store.store_feature_vector(
    feature,
    metadata={'source': 'trade_optimization'}
)

# Get feature vector
record = await pipeline.feature_store.get_feature_vector(record_id)

# Search similar features
similar = await pipeline.feature_store.search_similar_features(
    query_vector=[0.1, 0.2, 0.3],
    feature_set='slippage_prediction',
    limit=10
)
```

### 7. Real-time Data Serving Layer

Serves data to AI agents with:
- Caching for fast access
- Real-time subscriptions
- Historical data queries

**Usage:**
```python
# Get market data (cached)
market_data = await pipeline.data_serving.get_market_data('CRO')

# Get gas data
gas_data = await pipeline.data_serving.get_gas_data()

# Get historical data
historical = await pipeline.data_serving.get_historical_data(
    data_type='swap_event',
    source='vvs_finance',
    start_time=start_time,
    end_time=end_time,
    limit=1000
)
```

### 8. Data Versioning & Lineage Tracking

Tracks:
- Data lineage
- Data versions
- Data snapshots

**Usage:**
```python
# Track data lineage
lineage_id = await pipeline.versioning_system.track_data_lineage(
    output_id='feature_001',
    input_ids=['trade_001', 'pool_001'],
    operation='feature_generation',
    metadata={'feature_set': 'slippage_prediction'}
)

# Get data lineage
lineage = await pipeline.versioning_system.get_data_lineage(
    data_id='feature_001',
    depth=3
)
```

## Monitoring

### Health Status

```python
health = await pipeline.get_health_status()
print(f"Overall: {health['overall']}")
print(f"Components: {health['components']}")
print(f"Metrics: {health['metrics']}")
```

### Prometheus Metrics

If enabled, metrics are available at `http://localhost:8000/metrics`:

- `cleo_data_points_collected` - Number of data points collected
- `cleo_data_processing_time_seconds` - Processing time
- `cleo_feature_store_size_mb` - Feature store size
- `cleo_data_quality_score` - Data quality score

## Data Models

### RawDataPoint

Raw data point from any source:
```python
data_point = RawDataPoint(
    source=DataSource.CRONOS_BLOCKCHAIN,
    data_type=DataType.BLOCK,
    raw_data={'block_number': 12345, ...},
    metadata={'collected_at': '2024-01-01T00:00:00'}
)
```

### ProcessedFeature

Processed feature for ML models:
```python
feature = ProcessedFeature(
    feature_id='feature_001',
    timestamp=datetime.utcnow(),
    entity_id='trade:trade_001',
    feature_set='slippage_prediction',
    feature_vector=[0.1, 0.2, 0.3, ...],
    feature_names=['amount_usd', 'volatility', ...]
)
```

### DataLabel

Label for supervised learning:
```python
label = DataLabel(
    label_id='label_001',
    timestamp=datetime.utcnow(),
    entity_id='trade:trade_001',
    label_type='slippage',
    label_value=0.02,
    confidence=0.9
)
```

## Performance Considerations

- **Redis**: Used for fast data storage and caching
- **Batch Processing**: Blocks are processed in batches to avoid overwhelming the RPC
- **Caching**: Market data and gas prices are cached for 30 seconds
- **TTL**: Data points stored with 7-day TTL to manage memory

## Error Handling

All components include comprehensive error handling:
- Connection failures are retried with exponential backoff
- Invalid data is logged and skipped
- Component failures don't crash the entire pipeline

## Future Enhancements

- [ ] Vector database integration (Pinecone, Weaviate)
- [ ] Kafka streaming for high-throughput scenarios
- [ ] ML model training integration
- [ ] Advanced feature engineering
- [ ] Real-time anomaly detection
- [ ] Data export to data warehouses

## Troubleshooting

### Redis Connection Issues

```bash
# Check Redis is running
redis-cli ping

# Should return: PONG
```

### Web3 Connection Issues

```python
# Test Web3 connection
from web3 import Web3
w3 = Web3(Web3.HTTPProvider('https://evm-t3.cronos.org'))
print(f"Connected: {w3.is_connected()}")
```

### Data Quality Issues

Check quality report:
```python
report = await pipeline.quality_monitor.get_quality_report(hours=24)
if report['overall_quality'] < 70:
    print("Low data quality detected!")
    print(f"Issues: {report['issues']}")
    print(f"Recommendations: {report['recommendations']}")
```

## License

Part of the C.L.E.O. project.
