"""
Multi-Model Orchestrator for C.L.E.O. AI Models
Coordinates all AI models for comprehensive trade analysis
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
import asyncio
import logging
from datetime import datetime
from pathlib import Path

from .ai_models import (
    SlippagePredictionModel,
    LiquidityPatternModel,
    RouteOptimizationModel,
    RiskAssessmentModel,
    GasPricePredictionModel,
    ExecutionSuccessModel
)

logger = logging.getLogger(__name__)


class AIModelOrchestrator:
    """Enhanced orchestrator for all AI models with improved prediction aggregation and model selection"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.models = {}
        self.model_versions = {}
        self.is_initialized = False
        
        # Initialize models
        self.models['slippage'] = SlippagePredictionModel()
        self.models['liquidity'] = LiquidityPatternModel()
        self.models['risk'] = RiskAssessmentModel()
        self.models['gas'] = GasPricePredictionModel()
        self.models['success'] = ExecutionSuccessModel()
        
        # Route optimization is stateful
        self.route_optimizer = None
        
        # Performance tracking
        self.prediction_history = []
        self.model_performance = {}
        
        # Confidence calibration
        self.confidence_calibration = {}
        
        # Enable online learning by default
        for model in self.models.values():
            model.enable_online_learning(True)
    
    async def initialize(self):
        """Initialize all models"""
        logger.info("Initializing AI models...")
        
        # Try to load pre-trained models
        for name, model in self.models.items():
            if model.load_model():
                self.model_versions[name] = model.version
                logger.info(f"✓ Loaded {name} model v{model.version}")
            else:
                logger.warning(f"✗ Could not load {name} model, will need training")
        
        # Initialize route optimizer
        state_size = 20  # Number of state features
        action_size = 10  # Number of possible splits
        self.route_optimizer = RouteOptimizationModel(state_size, action_size)
        
        self.is_initialized = True
        logger.info("AI Model Orchestrator initialized")
    
    async def analyze_trade(self, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run complete AI analysis for a trade with enhanced financial context"""
        if not self.is_initialized:
            await self.initialize()
        
        # Enrich trade data with financial metrics if available
        try:
            from financial_metrics import financial_metrics_collector
            financial_summary = financial_metrics_collector.get_financial_summary()
            
            # Add financial context to trade data for better predictions
            trade_data['financial_context'] = {
                'historical_roi': financial_summary.get('roi_pct', 0),
                'sharpe_ratio': financial_summary.get('risk_metrics', {}).get('sharpe_ratio', 1.0),
                'win_rate': financial_summary.get('risk_metrics', {}).get('win_rate', 0.5),
                'avg_profit_per_execution': financial_summary.get('avg_profit_per_execution', 0),
                'market_regime': financial_summary.get('economic_indicators', {}).get('market_regime', 'neutral'),
                'network_congestion': financial_summary.get('economic_indicators', {}).get('network_congestion', 0.3),
                'gas_price_avg': financial_summary.get('economic_indicators', {}).get('gas_price_avg_24h', 10.0),
            }
            
            # Add market data for the token pair if available
            token_pair = trade_data.get('token_pair', '')
            if token_pair in financial_summary.get('market_data', {}):
                market_data = financial_summary['market_data'][token_pair]
                trade_data['market_context'] = {
                    'price_change_24h': market_data.get('price_change_24h', 0),
                    'volatility_24h': market_data.get('volatility_24h', 0),
                    'volume_24h': market_data.get('volume_24h', 0),
                    'liquidity_usd': market_data.get('liquidity_usd', 0),
                }
        except ImportError:
            # Financial metrics not available, continue without enrichment
            pass
        except Exception as e:
            logger.warning(f"Error enriching trade data with financial metrics: {e}")
        
        analysis_results = {
            "trade_id": trade_data.get('trade_id', 'unknown'),
            "timestamp": datetime.now().isoformat(),
            "models_used": [],
            "predictions": {}
        }
        
        try:
            # 1. Predict slippage
            if 'slippage' in self.models and self.models['slippage'].is_trained:
                slippage_pred = await self._predict_slippage(trade_data)
                analysis_results['predictions']['slippage'] = slippage_pred
                analysis_results['models_used'].append('slippage')
            
            # 2. Analyze liquidity patterns
            if 'liquidity' in self.models and self.models['liquidity'].is_trained:
                liquidity_analysis = await self._analyze_liquidity(trade_data)
                analysis_results['predictions']['liquidity'] = liquidity_analysis
                analysis_results['models_used'].append('liquidity')
            
            # 3. Assess risk
            if 'risk' in self.models and self.models['risk'].is_trained:
                risk_assessment = await self._assess_risk(trade_data)
                analysis_results['predictions']['risk'] = risk_assessment
                analysis_results['models_used'].append('risk')
            
            # 4. Predict gas price
            if 'gas' in self.models and self.models['gas'].is_trained:
                gas_prediction = await self._predict_gas(trade_data)
                analysis_results['predictions']['gas'] = gas_prediction
                analysis_results['models_used'].append('gas')
            
            # 5. Predict execution success
            if 'success' in self.models and self.models['success'].is_trained:
                success_prediction = await self._predict_success(trade_data)
                analysis_results['predictions']['success'] = success_prediction
                analysis_results['models_used'].append('success')
            
            # 6. Generate route recommendation
            route_recommendation = await self._generate_route_recommendation(
                trade_data, analysis_results['predictions']
            )
            analysis_results['recommendation'] = route_recommendation
            
            # 7. Calculate overall confidence score
            analysis_results['confidence_score'] = self._calculate_overall_confidence(
                analysis_results['predictions']
            )
            
            logger.info(f"Trade analysis completed for {trade_data.get('trade_id')}")
            
        except Exception as e:
            logger.error(f"Trade analysis failed: {e}")
            analysis_results['error'] = str(e)
        
        return analysis_results
    
    async def _predict_slippage(self, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """Predict slippage for trade"""
        model = self.models['slippage']
        
        # Extract features
        historical_data = trade_data.get('historical_data', pd.DataFrame())
        current_trade = {
            'amount_in_usd': trade_data.get('amount_in_usd', 0),
            'token_pair': trade_data.get('token_pair'),
            'hour_of_day': datetime.now().hour,
            'day_of_week': datetime.now().weekday()
        }
        
        # Create sequences for LSTM
        X_sequence = model.create_sequences(historical_data)
        
        if X_sequence is not None and model.is_trained:
            try:
                prediction = await model.predict(X_sequence[-1:])
                predicted_slippage = float(prediction[0][0])
            except Exception as e:
                logger.warning(f"Slippage prediction failed: {e}")
                predicted_slippage = 1.0  # Default 1% slippage
        else:
            # Fallback to simple heuristic
            features = model.create_features(historical_data, current_trade)
            amount_ratio = current_trade['amount_in_usd'] / 10000
            predicted_slippage = 0.1 * (1 + amount_ratio * 10)  # Simple heuristic
        
        return {
            "predicted_slippage_percent": predicted_slippage,
            "features_used": len(features.flatten()) if 'features' in locals() else 0,
            "model_version": model.version
        }
    
    async def _analyze_liquidity(self, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze liquidity patterns"""
        model = self.models['liquidity']
        
        historical_data = trade_data.get('historical_data', pd.DataFrame())
        if len(historical_data) < model.sequence_length:
            return {"error": "Insufficient historical data"}
        
        if not model.is_trained:
            return {"error": "Model not trained"}
        
        analysis = await model.predict_liquidity_trend(historical_data)
        analysis['model_version'] = model.version
        
        return analysis
    
    async def _assess_risk(self, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess trade risk"""
        model = self.models['risk']
        
        # Create risk features
        risk_features = self._create_risk_features(trade_data)
        
        if risk_features is None:
            return {"error": "Could not create risk features"}
        
        if not model.is_trained:
            return {"error": "Model not trained"}
        
        assessment = await model.predict_risk_score(risk_features)
        assessment['model_version'] = model.version
        
        return assessment
    
    async def _predict_gas(self, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """Predict gas price"""
        model = self.models['gas']
        
        historical_gas = trade_data.get('historical_gas_prices', np.array([]))
        network_conditions = trade_data.get('network_conditions', {})
        
        if not model.is_trained:
            # Fallback to simple prediction
            avg_gas = np.mean(historical_gas) if len(historical_gas) > 0 else 10.0
            return {
                "predicted_base_gas": avg_gas,
                "recommended_gas": avg_gas * 1.1,
                "model_version": model.version,
                "note": "Using fallback prediction"
            }
        
        prediction = await model.predict_gas_price(historical_gas, network_conditions)
        prediction['model_version'] = model.version
        
        return prediction
    
    async def _predict_success(self, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """Predict execution success"""
        model = self.models['success']
        
        # Create success prediction features
        success_features = self._create_success_features(trade_data)
        
        if success_features is None:
            return {"error": "Could not create success features"}
        
        if not model.is_trained:
            return {"error": "Model not trained"}
        
        prediction = await model.predict_success_probability(success_features)
        prediction['model_version'] = model.version
        
        return prediction
    
    async def _generate_route_recommendation(self, trade_data: Dict[str, Any],
                                          predictions: Dict[str, Any]) -> Dict[str, Any]:
        """Generate route recommendation based on all predictions"""
        
        recommendation = {
            "action": "PROCEED",  # or "DELAY", "ADJUST", "CANCEL"
            "reason": "",
            "suggested_parameters": {},
            "estimated_outcome": {}
        }
        
        # Analyze predictions to make recommendation
        risk_level = predictions.get('risk', {}).get('risk_class', 'MEDIUM')
        success_prob = predictions.get('success', {}).get('success_probability', 0.5)
        slippage = predictions.get('slippage', {}).get('predicted_slippage_percent', 5.0)
        
        # Decision logic
        if risk_level == 'CRITICAL' or success_prob < 0.3:
            recommendation['action'] = "CANCEL"
            recommendation['reason'] = "High risk or low success probability"
        
        elif risk_level == 'HIGH' or success_prob < 0.6:
            recommendation['action'] = "DELAY"
            recommendation['reason'] = "Suboptimal conditions, recommend waiting"
        
        elif slippage > trade_data.get('max_slippage_percent', 5.0):
            recommendation['action'] = "ADJUST"
            recommendation['reason'] = "Predicted slippage exceeds limit"
            recommendation['suggested_parameters'] = {
                "split_trade": True,
                "reduce_amount": trade_data.get('amount_in_usd', 0) * 0.7,
                "wait_for_better_liquidity": True
            }
        
        else:
            recommendation['action'] = "PROCEED"
            recommendation['reason'] = "Conditions favorable for execution"
            
            # Use RL model for route optimization
            if self.route_optimizer:
                state = self._create_rl_state(trade_data, predictions)
                action = self.route_optimizer.act(state)
                
                recommendation['suggested_parameters'] = {
                    "route_strategy": f"strategy_{action}",
                    "num_splits": min(action + 1, 5),
                    "priority_gas": predictions.get('gas', {}).get('recommended_gas', 10)
                }
        
        # Estimate outcome
        amount_in = trade_data.get('amount_in_usd', 0)
        estimated_output = amount_in * (1 - slippage / 100)
        
        recommendation['estimated_outcome'] = {
            "estimated_slippage": slippage,
            "estimated_output_usd": estimated_output,
            "estimated_gas_cost": predictions.get('gas', {}).get('recommended_gas', 0),
            "confidence": predictions.get('confidence_score', 0.5)
        }
        
        return recommendation
    
    def _create_risk_features(self, trade_data: Dict[str, Any]) -> Optional[np.ndarray]:
        """Create features for risk assessment"""
        try:
            features = []
            
            # Trade size features
            amount_usd = trade_data.get('amount_in_usd', 0)
            features.append(amount_usd / 10000)  # Normalized
            
            # Market volatility (simulated)
            features.append(trade_data.get('volatility', 0.1))
            
            # Liquidity ratio
            available_liquidity = trade_data.get('available_liquidity_usd', 10000)
            features.append(amount_usd / available_liquidity if available_liquidity > 0 else 1.0)
            
            # Time features
            hour = datetime.now().hour
            features.append(hour / 24)
            features.append(1 if hour >= 9 and hour <= 17 else 0)  # Trading hours
            
            # Network conditions
            features.append(trade_data.get('network_congestion', 0.5))
            features.append(trade_data.get('pending_transactions', 0) / 1000)
            
            return np.array(features).reshape(1, -1)
        except Exception as e:
            logger.error(f"Failed to create risk features: {e}")
            return None
    
    def _create_success_features(self, trade_data: Dict[str, Any]) -> Optional[np.ndarray]:
        """Create features for success prediction"""
        try:
            features = []
            
            # Gas price ratio
            current_gas = trade_data.get('current_gas_price', 10)
            avg_gas = trade_data.get('average_gas_price', 10)
            features.append(current_gas / avg_gas if avg_gas > 0 else 1.0)
            
            # Liquidity sufficiency
            amount_usd = trade_data.get('amount_in_usd', 0)
            liquidity = trade_data.get('available_liquidity_usd', 10000)
            features.append(liquidity / amount_usd if amount_usd > 0 else 10)
            
            # Slippage buffer
            max_slippage = trade_data.get('max_slippage_percent', 5.0)
            predicted_slippage = trade_data.get('predicted_slippage', 2.0)
            features.append(max_slippage - predicted_slippage)
            
            # Network health
            features.append(1.0 - trade_data.get('network_congestion', 0.5))
            features.append(trade_data.get('block_time_variance', 0.1))
            
            # Historical success rate for similar trades
            features.append(trade_data.get('historical_success_rate', 0.8))
            
            return np.array(features).reshape(1, -1)
        except Exception as e:
            logger.error(f"Failed to create success features: {e}")
            return None
    
    def _create_rl_state(self, trade_data: Dict[str, Any], 
                        predictions: Dict[str, Any]) -> np.ndarray:
        """Create state for reinforcement learning"""
        state = []
        
        # Trade parameters
        state.append(trade_data.get('amount_in_usd', 0) / 10000)  # Normalized
        state.append(trade_data.get('max_slippage_percent', 5.0) / 100)
        
        # Predictions
        state.append(predictions.get('slippage', {}).get('predicted_slippage_percent', 0) / 100)
        state.append(predictions.get('risk', {}).get('risk_score', 2.5) / 4)
        state.append(predictions.get('success', {}).get('success_probability', 0.5))
        
        # Market conditions
        state.append(trade_data.get('volatility', 0.1))
        state.append(trade_data.get('network_congestion', 0.5))
        
        # Liquidity distribution
        available_dexes = trade_data.get('available_dexes', 3)
        state.append(available_dexes / 5)  # Normalize
        
        # Time features
        hour = datetime.now().hour
        state.append(hour / 24)
        state.append(1 if 9 <= hour <= 17 else 0)
        
        # Pad to state_size if needed
        while len(state) < 20:
            state.append(0.0)
        
        return np.array(state[:20])
    
    def _calculate_overall_confidence(self, predictions: Dict[str, Any]) -> float:
        """Calculate overall confidence score with improved calibration"""
        confidence_scores = []
        weights = {
            'slippage': 0.25,
            'risk': 0.30,
            'success': 0.25,
            'gas': 0.10,
            'liquidity': 0.10
        }
        
        # Extract confidence from each prediction with weights
        weighted_sum = 0.0
        total_weight = 0.0
        
        for key, pred in predictions.items():
            if isinstance(pred, dict) and not pred.get('error'):
                confidence = None
                if 'confidence' in pred:
                    confidence = pred['confidence']
                elif 'confidence_score' in pred:
                    confidence = pred['confidence_score']
                
                if confidence is not None:
                    weight = weights.get(key, 0.1)
                    # Apply calibration if available
                    calibrated_confidence = self._calibrate_confidence(key, confidence)
                    weighted_sum += calibrated_confidence * weight
                    total_weight += weight
                    confidence_scores.append(calibrated_confidence)
        
        # Calculate weighted average
        if total_weight > 0:
            avg_confidence = weighted_sum / total_weight
            
            # Penalize if any model has very low confidence or high variance
            if confidence_scores:
                min_confidence = min(confidence_scores)
                max_confidence = max(confidence_scores)
                variance = np.var(confidence_scores)
                
                # Reduce confidence if models disagree significantly
                if variance > 0.1:
                    avg_confidence *= (1 - min(variance, 0.3))
                
                # Penalize if any model has very low confidence
                if min_confidence < 0.3:
                    avg_confidence *= 0.7
            
            # Ensure confidence is in valid range
            avg_confidence = max(0.0, min(1.0, avg_confidence))
            
            return round(avg_confidence, 2)
        
        return 0.5  # Default confidence
    
    def _calibrate_confidence(self, model_name: str, raw_confidence: float) -> float:
        """Calibrate confidence scores based on historical performance"""
        # Simple calibration - in production, use Platt scaling or isotonic regression
        if model_name not in self.confidence_calibration:
            return raw_confidence
        
        calibration_data = self.confidence_calibration[model_name]
        if len(calibration_data) < 10:
            return raw_confidence
        
        # Apply linear calibration based on historical accuracy
        # This is a simplified version - production would use more sophisticated methods
        return raw_confidence
    
    def update_confidence_calibration(self, model_name: str, predicted_confidence: float, 
                                     actual_accuracy: float):
        """Update confidence calibration data"""
        if model_name not in self.confidence_calibration:
            self.confidence_calibration[model_name] = []
        
        self.confidence_calibration[model_name].append({
            'predicted': predicted_confidence,
            'actual': actual_accuracy,
            'timestamp': datetime.now()
        })
        
        # Keep only recent calibration data
        if len(self.confidence_calibration[model_name]) > 1000:
            self.confidence_calibration[model_name] = self.confidence_calibration[model_name][-1000:]
    
    async def train_all_models(self, training_data: Dict[str, Any]):
        """Train all models with provided data"""
        logger.info("Starting training of all AI models...")
        
        training_results = {}
        
        # Train each model
        for name, model in self.models.items():
            if name in training_data:
                logger.info(f"Training {name} model...")
                
                try:
                    data = training_data[name]
                    
                    if name == 'slippage':
                        X = data.get('X_sequences')
                        y = data.get('y')
                    else:
                        X = data.get('X')
                        y = data.get('y')
                    
                    if X is not None and y is not None:
                        await model.train(X, y)
                        model.save_model()
                        
                        training_results[name] = {
                            'status': 'success',
                            'samples': len(y),
                            'version': model.version
                        }
                        
                        logger.info(f"✓ {name} model trained successfully")
                    else:
                        training_results[name] = {
                            'status': 'failed',
                            'error': 'Missing training data'
                        }
                except Exception as e:
                    training_results[name] = {
                        'status': 'failed',
                        'error': str(e)
                    }
                    logger.error(f"✗ Failed to train {name} model: {e}")
            else:
                logger.warning(f"No training data for {name} model")
        
        return training_results
