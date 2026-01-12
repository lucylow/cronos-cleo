"""
Integration Example: Using AI Models with Existing Agents
Shows how to integrate the new AI models with the existing agent system
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any

from .model_orchestrator import AIModelOrchestrator


class EnhancedSlippagePredictor:
    """Enhanced slippage predictor using AI models"""
    
    def __init__(self):
        self.orchestrator = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize the AI model orchestrator"""
        if not self._initialized:
            self.orchestrator = AIModelOrchestrator()
            await self.orchestrator.initialize()
            self._initialized = True
    
    async def predict_slippage(self, amount: float, liquidity: float, 
                              historical_data: pd.DataFrame = None,
                              token_pair: str = "CRO/USDC") -> Dict[str, Any]:
        """Predict slippage using AI model"""
        await self.initialize()
        
        # Prepare trade data
        trade_data = {
            'trade_id': f'slippage_pred_{datetime.now().timestamp()}',
            'amount_in_usd': amount,
            'token_pair': token_pair,
            'historical_data': historical_data or pd.DataFrame({
                'price': np.random.normal(0.08, 0.001, 100),
                'liquidity': np.random.normal(liquidity, liquidity * 0.1, 100),
                'volume': np.random.exponential(10000, 100)
            }),
            'available_liquidity_usd': liquidity
        }
        
        # Get AI analysis
        analysis = await self.orchestrator.analyze_trade(trade_data)
        
        # Extract slippage prediction
        slippage_pred = analysis.get('predictions', {}).get('slippage', {})
        
        return {
            'predicted_slippage_percent': slippage_pred.get('predicted_slippage_percent', 1.0),
            'confidence': analysis.get('confidence_score', 0.5),
            'model_version': slippage_pred.get('model_version', 'unknown'),
            'recommendation': analysis.get('recommendation', {})
        }


class EnhancedRiskManager:
    """Enhanced risk manager using AI models"""
    
    def __init__(self):
        self.orchestrator = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize the AI model orchestrator"""
        if not self._initialized:
            self.orchestrator = AIModelOrchestrator()
            await self.orchestrator.initialize()
            self._initialized = True
    
    async def assess_trade_risk(self, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess trade risk using AI models"""
        await self.initialize()
        
        # Get comprehensive AI analysis
        analysis = await self.orchestrator.analyze_trade(trade_data)
        
        # Extract risk assessment
        risk_pred = analysis.get('predictions', {}).get('risk', {})
        success_pred = analysis.get('predictions', {}).get('success', {})
        
        return {
            'risk_score': risk_pred.get('risk_score', 2.5),
            'risk_class': risk_pred.get('risk_class', 'MEDIUM'),
            'success_probability': success_pred.get('success_probability', 0.5),
            'recommendation': analysis.get('recommendation', {}),
            'confidence': analysis.get('confidence_score', 0.5)
        }


async def example_usage():
    """Example of using AI models with agents"""
    
    print("🚀 C.L.E.O. AI Models Integration Example")
    print("=" * 60)
    
    # Example 1: Enhanced Slippage Prediction
    print("\n1️⃣ Enhanced Slippage Prediction")
    slippage_predictor = EnhancedSlippagePredictor()
    
    prediction = await slippage_predictor.predict_slippage(
        amount=5000.0,
        liquidity=1000000.0,
        token_pair="CRO/USDC"
    )
    
    print(f"   Predicted Slippage: {prediction['predicted_slippage_percent']:.2f}%")
    print(f"   Confidence: {prediction['confidence']:.2f}")
    print(f"   Model Version: {prediction['model_version']}")
    
    # Example 2: Risk Assessment
    print("\n2️⃣ Risk Assessment")
    risk_manager = EnhancedRiskManager()
    
    trade_data = {
        'trade_id': 'example_trade',
        'amount_in_usd': 10000.0,
        'token_pair': 'CRO/USDC',
        'max_slippage_percent': 1.0,
        'historical_data': pd.DataFrame({
            'price': np.random.normal(0.08, 0.001, 100),
            'liquidity': np.random.normal(2000000, 200000, 100),
            'volume': np.random.exponential(50000, 100)
        }),
        'available_liquidity_usd': 2000000,
        'volatility': 0.15,
        'network_congestion': 0.3
    }
    
    risk_assessment = await risk_manager.assess_trade_risk(trade_data)
    
    print(f"   Risk Score: {risk_assessment['risk_score']:.2f}")
    print(f"   Risk Class: {risk_assessment['risk_class']}")
    print(f"   Success Probability: {risk_assessment['success_probability']:.2%}")
    print(f"   Recommendation: {risk_assessment['recommendation'].get('action', 'N/A')}")
    
    # Example 3: Full Trade Analysis
    print("\n3️⃣ Full Trade Analysis")
    orchestrator = AIModelOrchestrator()
    await orchestrator.initialize()
    
    full_analysis = await orchestrator.analyze_trade(trade_data)
    
    print(f"   Models Used: {', '.join(full_analysis.get('models_used', []))}")
    print(f"   Overall Confidence: {full_analysis.get('confidence_score', 'N/A')}")
    print(f"   Recommended Action: {full_analysis.get('recommendation', {}).get('action', 'N/A')}")
    
    print("\n" + "=" * 60)
    print("✅ Integration Example Complete")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(example_usage())
