"""
Example usage of C.L.E.O. AI Data Pipeline

This demonstrates how to initialize and use the complete AI data pipeline system.
"""

import asyncio
import os
from ai.ai_data_pipeline import CLEODataPipeline, DataSource, DataType

async def main():
    """Example: Initialize and start the AI data pipeline"""
    
    # Configuration
    config = {
        'cronos_rpc': os.getenv('CRONOS_RPC', 'https://evm-t3.cronos.org'),
        'redis_url': os.getenv('REDIS_URL', 'redis://localhost:6379'),
        'crypto_com_api_key': os.getenv('CRYPTO_COM_API_KEY', ''),
        'x402_facilitator': os.getenv('X402_FACILITATOR', ''),
        'kafka_bootstrap_servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', None),
        'enable_prometheus': os.getenv('ENABLE_PROMETHEUS', 'false').lower() == 'true',
        'prometheus_port': int(os.getenv('PROMETHEUS_PORT', 8000))
    }
    
    # Initialize pipeline
    pipeline = CLEODataPipeline(config)
    await pipeline.initialize()
    
    # Start pipeline (runs in background)
    print("Starting AI data pipeline...")
    pipeline_task = asyncio.create_task(pipeline.start())
    
    # Example: Access data serving layer
    await asyncio.sleep(5)  # Wait for pipeline to start
    
    # Get market data
    market_data = await pipeline.data_serving.get_market_data('CRO', 'coingecko')
    if market_data:
        print(f"CRO Price: ${market_data.get('price_usd', 0)}")
    
    # Get gas data
    gas_data = await pipeline.data_serving.get_gas_data()
    print(f"Current Gas Price: {gas_data.get('price_gwei', 0)} Gwei")
    
    # Get recent swap events
    swap_events = await pipeline.data_collector.get_recent_data(
        DataSource.VVS_FINANCE,
        DataType.SWAP_EVENT,
        limit=10
    )
    print(f"Recent swap events: {len(swap_events)}")
    
    # Get data quality report
    quality_report = await pipeline.quality_monitor.get_quality_report(hours=1)
    print(f"Data Quality Score: {quality_report.get('overall_quality', 0)}%")
    
    # Get pipeline health
    health = await pipeline.get_health_status()
    print(f"Pipeline Health: {health.get('overall', 'unknown')}")
    
    # Keep running
    try:
        await pipeline_task
    except KeyboardInterrupt:
        print("\nStopping pipeline...")
        await pipeline.stop()

if __name__ == "__main__":
    asyncio.run(main())
