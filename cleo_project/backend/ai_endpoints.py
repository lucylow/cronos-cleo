"""
AI Model API Endpoints for C.L.E.O.
Add these endpoints to main.py
"""

from fastapi import HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Initialize AI model orchestrator (lazy initialization)
ai_orchestrator = None

async def get_ai_orchestrator():
    """Get or initialize AI model orchestrator"""
    global ai_orchestrator
    if ai_orchestrator is None:
        try:
            from ai.model_orchestrator import AIModelOrchestrator
            ai_orchestrator = AIModelOrchestrator()
            await ai_orchestrator.initialize()
        except Exception as e:
            logger.error(f"Failed to initialize AI orchestrator: {e}")
            return None
    return ai_orchestrator

class TradeAnalysisRequest(BaseModel):
    """Request for AI trade analysis"""
    trade_id: Optional[str] = None
    amount_in_usd: float
    token_pair: str
    max_slippage_percent: float = 1.0
    historical_data: Optional[Dict] = None
    historical_gas_prices: Optional[List[float]] = None
    network_conditions: Optional[Dict] = None
    available_liquidity_usd: Optional[float] = None
    volatility: Optional[float] = None
    current_gas_price: Optional[float] = None
    average_gas_price: Optional[float] = None
    available_dexes: Optional[int] = None

async def analyze_trade_ai_endpoint(request: TradeAnalysisRequest):
    """Run comprehensive AI analysis for a trade"""
    try:
        orchestrator = await get_ai_orchestrator()
        if not orchestrator:
            raise HTTPException(status_code=503, detail="AI model orchestrator not available")
        
        # Convert request to trade data format
        import pandas as pd
        import numpy as np
        
        historical_data = request.historical_data
        if historical_data:
            historical_df = pd.DataFrame(historical_data)
        else:
            # Generate mock data if not provided
            historical_df = pd.DataFrame({
                'price': np.random.normal(0.08, 0.001, 100),
                'liquidity': np.random.normal(1000000, 100000, 100),
                'volume': np.random.exponential(10000, 100)
            })
        
        historical_gas = request.historical_gas_prices
        if not historical_gas:
            historical_gas = np.random.normal(10, 2, 50).tolist()
        
        trade_data = {
            'trade_id': request.trade_id or f'trade_{datetime.now().timestamp()}',
            'amount_in_usd': request.amount_in_usd,
            'token_pair': request.token_pair,
            'max_slippage_percent': request.max_slippage_percent,
            'historical_data': historical_df,
            'historical_gas_prices': np.array(historical_gas),
            'network_conditions': request.network_conditions or {'congestion': 0.3, 'pending_txs': 1500},
            'available_liquidity_usd': request.available_liquidity_usd or request.amount_in_usd * 200,
            'volatility': request.volatility or 0.15,
            'current_gas_price': request.current_gas_price or 12.5,
            'average_gas_price': request.average_gas_price or 10.0,
            'available_dexes': request.available_dexes or 3
        }
        
        # Run AI analysis
        analysis = await orchestrator.analyze_trade(trade_data)
        
        return analysis
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI trade analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def get_ai_models_status_endpoint():
    """Get status of AI models"""
    try:
        orchestrator = await get_ai_orchestrator()
        if not orchestrator:
            return {
                "available": False,
                "message": "AI model orchestrator not initialized"
            }
        
        models_status = {}
        for name, model in orchestrator.models.items():
            models_status[name] = {
                "is_trained": model.is_trained,
                "version": model.version,
                "model_name": model.model_name
            }
        
        return {
            "available": True,
            "initialized": orchestrator.is_initialized,
            "models": models_status
        }
    except Exception as e:
        return {
            "available": False,
            "error": str(e)
        }
