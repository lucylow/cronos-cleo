"""
Slippage Predictor Agent - ML-based slippage prediction
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from decimal import Decimal

from .base_agent import BaseAgent
from .message_bus import AgentMessage

logger = logging.getLogger(__name__)


class SlippagePredictorAgent(BaseAgent):
    """ML agent for predicting slippage based on historical data"""
    
    def __init__(self):
        super().__init__("slippage_predictor", "Slippage Predictor")
        self.model = None
        self.historical_data = []
        self.training_interval = 3600  # 1 hour
        
    async def start(self):
        """Start the slippage predictor"""
        await super().start()
        await self._load_or_train_model()
        asyncio.create_task(self._continuous_training())
    
    async def _load_or_train_model(self):
        """Load or train the ML model"""
        # For hackathon demo, we'll use a simple heuristic model
        # In production, this would be a trained ML model (XGBoost, LightGBM, etc.)
        logger.info("Initializing slippage prediction model")
        
        # Simple heuristic: slippage = base_rate * (amount / liquidity)^exponent
        self.model = {
            "base_rate": 0.002,  # 0.2% base slippage
            "exponent": 1.5,     # Non-linear relationship
            "volatility_factor": 0.1,
            "time_of_day_weights": {
                "0-6": 1.2,    # Low liquidity hours
                "6-12": 0.9,
                "12-18": 0.8,  # High activity
                "18-24": 1.0
            }
        }
    
    async def _continuous_training(self):
        """Continuously train the model with new data"""
        while self.is_running:
            try:
                if len(self.historical_data) > 100:
                    await self._retrain_model()
                await asyncio.sleep(self.training_interval)
            except Exception as e:
                logger.error(f"Model training error: {e}")
    
    async def _retrain_model(self):
        """Retrain the model with historical data"""
        logger.info("Retraining slippage prediction model...")
        # In production: actual ML training here
        # For demo: just update heuristics based on recent data
    
    async def predict_slippage(self, amount: Decimal, liquidity: Decimal, 
                             volatility: float, hour_of_day: int) -> Decimal:
        """Predict slippage percentage"""
        # Simple heuristic prediction
        if liquidity <= 0:
            return Decimal('0.1')  # 10% if no liquidity
        
        # Calculate base slippage
        amount_ratio = float(amount / liquidity)
        base_slippage = self.model["base_rate"] * (amount_ratio ** self.model["exponent"])
        
        # Adjust for volatility
        volatility_adj = base_slippage * volatility * self.model["volatility_factor"]
        
        # Adjust for time of day
        time_key = self._get_time_key(hour_of_day)
        time_multiplier = self.model["time_of_day_weights"].get(time_key, 1.0)
        
        total_slippage = (base_slippage + volatility_adj) * time_multiplier
        
        # Cap at 50%
        return Decimal(min(total_slippage, 0.5))
    
    def _get_time_key(self, hour: int) -> str:
        """Get time of day key for weights"""
        if 0 <= hour < 6:
            return "0-6"
        elif 6 <= hour < 12:
            return "6-12"
        elif 12 <= hour < 18:
            return "12-18"
        else:
            return "18-24"
    
    async def handle_message(self, message: AgentMessage):
        """Handle incoming messages"""
        if message.message_type == "predict_slippage":
            amount = Decimal(str(message.payload.get("amount", 0)))
            liquidity = Decimal(str(message.payload.get("liquidity", 0)))
            volatility = message.payload.get("volatility", 0.1)
            request_id = message.payload.get("request_id")
            
            # Get current hour
            current_hour = datetime.now().hour
            
            # Predict slippage
            predicted_slippage = await self.predict_slippage(
                amount, liquidity, volatility, current_hour
            )
            
            response = AgentMessage(
                message_id=f"resp_{message.message_id}",
                sender=self.agent_id,
                receiver=message.sender,
                message_type="slippage_prediction",
                payload={
                    "predicted_slippage": float(predicted_slippage),
                    "confidence": 0.85,  # Mock confidence score
                    "request_id": request_id
                }
            )
            await self.send_message(response)
