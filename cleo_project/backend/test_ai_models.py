"""
Test script for C.L.E.O. AI Models
Quick test to verify models are working correctly
"""

import asyncio
import numpy as np
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ai.model_orchestrator import AIModelOrchestrator
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_ai_models():
    """Test the AI models with sample data"""
    
    print("🧪 Testing C.L.E.O. AI Models...")
    print("=" * 60)
    
    # Initialize orchestrator
    orchestrator = AIModelOrchestrator()
    await orchestrator.initialize()
    
    # Create sample trade data
    test_trade = {
        'trade_id': 'test_001',
        'amount_in_usd': 5000.0,
        'token_pair': 'CRO/USDC',
        'max_slippage_percent': 1.0,
        'historical_data': pd.DataFrame({
            'price': np.random.normal(0.08, 0.001, 100).cumsum() + 0.08,
            'liquidity': np.random.normal(1000000, 100000, 100),
            'volume': np.random.exponential(10000, 100)
        }),
        'historical_gas_prices': np.random.normal(10, 2, 50),
        'network_conditions': {
            'congestion': 0.3,
            'pending_txs': 1500
        },
        'available_liquidity_usd': 2000000,
        'volatility': 0.15,
        'current_gas_price': 12.5,
        'average_gas_price': 10.0,
        'available_dexes': 3
    }
    
    # Run AI analysis
    print("\n🔍 Running trade analysis...")
    analysis = await orchestrator.analyze_trade(test_trade)
    
    # Print results
    print("\n" + "="*60)
    print("C.L.E.O. AI TRADE ANALYSIS REPORT")
    print("="*60)
    
    print(f"\n📊 Trade ID: {analysis['trade_id']}")
    print(f"⏰ Timestamp: {analysis['timestamp']}")
    print(f"🎯 Confidence Score: {analysis.get('confidence_score', 'N/A')}")
    
    print("\n🔮 PREDICTIONS:")
    for model_name, prediction in analysis.get('predictions', {}).items():
        print(f"\n  {model_name.upper()}:")
        if isinstance(prediction, dict):
            for key, value in prediction.items():
                if key != 'model_version':
                    print(f"    {key}: {value}")
        else:
            print(f"    {prediction}")
    
    print("\n💡 RECOMMENDATION:")
    rec = analysis.get('recommendation', {})
    print(f"  Action: {rec.get('action', 'N/A')}")
    print(f"  Reason: {rec.get('reason', 'N/A')}")
    
    if rec.get('suggested_parameters'):
        print("\n  Suggested Parameters:")
        for param, value in rec['suggested_parameters'].items():
            print(f"    {param}: {value}")
    
    print("\n📈 ESTIMATED OUTCOME:")
    outcome = rec.get('estimated_outcome', {})
    for metric, value in outcome.items():
        print(f"  {metric}: {value}")
    
    print("\n" + "="*60)
    print("✅ Analysis Complete")
    print("="*60)
    
    return analysis


if __name__ == "__main__":
    asyncio.run(test_ai_models())
