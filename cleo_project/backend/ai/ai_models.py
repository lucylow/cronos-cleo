"""
C.L.E.O. AI Model System
Cronos Liquidity Execution Orchestrator

Model Architecture:
1. Slippage Prediction Model (LSTM + Attention)
2. Liquidity Pattern Model (Time Series Forecasting)
3. Route Optimization Model (Reinforcement Learning)
4. Risk Assessment Model (Ensemble Classifier)
5. Gas Price Prediction Model (Transformer)
6. Execution Success Model (Binary Classifier)
"""

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import torch.nn.functional as F
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, VotingClassifier, RandomForestClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split, TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error, accuracy_score, roc_auc_score
import xgboost as xgb
import lightgbm as lgb
from typing import Dict, List, Tuple, Optional, Any
import pickle
import json
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import deque
import asyncio
from decimal import Decimal
import logging
from pathlib import Path
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set device for PyTorch
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
logger.info(f"Using device: {device}")

# Create models directory if it doesn't exist
MODELS_DIR = Path("models")
MODELS_DIR.mkdir(exist_ok=True)

# ============================================================================
# Base Model Classes
# ============================================================================

class BaseAIModel:
    """Base class for all AI models"""
    
    def __init__(self, model_name: str, version: str = "1.0.0"):
        self.model_name = model_name
        self.version = version
        self.model = None
        self.scaler = StandardScaler()
        self.feature_columns = []
        self.target_column = ""
        self.is_trained = False
        self.training_history = []
        self.model_path = MODELS_DIR / f"{model_name}_v{version}.pkl"
        
        # Performance tracking
        self.performance_metrics = {
            'total_predictions': 0,
            'successful_predictions': 0,
            'avg_prediction_time_ms': 0,
            'last_prediction_time': None,
            'prediction_errors': []
        }
        
        # Online learning buffer
        self.online_learning_buffer = deque(maxlen=1000)
        self.online_learning_enabled = False
    
    def save_model(self):
        """Save model to disk"""
        if self.model is not None:
            model_data = {
                'model': self.model,
                'scaler': self.scaler,
                'feature_columns': self.feature_columns,
                'target_column': self.target_column,
                'is_trained': self.is_trained,
                'version': self.version,
                'saved_at': datetime.now().isoformat()
            }
            with open(self.model_path, 'wb') as f:
                pickle.dump(model_data, f)
            logger.info(f"Model saved to {self.model_path}")
    
    def load_model(self):
        """Load model from disk"""
        try:
            if not self.model_path.exists():
                return False
            with open(self.model_path, 'rb') as f:
                model_data = pickle.load(f)
            
            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.feature_columns = model_data['feature_columns']
            self.target_column = model_data['target_column']
            self.is_trained = model_data['is_trained']
            logger.info(f"Model loaded from {self.model_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False
    
    async def predict(self, features: np.ndarray) -> np.ndarray:
        """Make predictions (to be implemented by subclasses)"""
        raise NotImplementedError
    
    def enable_online_learning(self, enabled: bool = True):
        """Enable or disable online learning"""
        self.online_learning_enabled = enabled
        logger.info(f"Online learning {'enabled' if enabled else 'disabled'} for {self.model_name}")
    
    def add_training_sample(self, features: np.ndarray, target: Any):
        """Add a sample to the online learning buffer"""
        if self.online_learning_enabled:
            self.online_learning_buffer.append((features, target))
    
    async def update_model_online(self, batch_size: int = 32):
        """Update model with samples from online learning buffer"""
        if not self.online_learning_enabled or len(self.online_learning_buffer) < batch_size:
            return
        
        # Extract batch from buffer
        batch = list(self.online_learning_buffer)[-batch_size:]
        features, targets = zip(*batch)
        
        # This is a placeholder - subclasses should implement specific online update logic
        logger.info(f"Online learning update triggered for {self.model_name} with {len(batch)} samples")
    
    async def train(self, X: np.ndarray, y: np.ndarray, **kwargs):
        """Train the model (to be implemented by subclasses)"""
        raise NotImplementedError
    
    def calculate_feature_importance(self) -> Dict[str, float]:
        """Calculate feature importance (if supported by model)"""
        return {}

# ============================================================================
# 1. Slippage Prediction Model (LSTM + Attention)
# ============================================================================

class SlippagePredictionModel(BaseAIModel):
    """LSTM-based model with attention for slippage prediction"""
    
    def __init__(self):
        super().__init__("slippage_predictor", "2.0.0")
        self.model = None
        self.lookback_window = 24  # Hours of historical data
        self.sequence_length = 10  # Time steps per sequence
    
    class LSTMAttentionModel(nn.Module):
        """Enhanced LSTM with multi-head attention mechanism for time series prediction"""
        
        def __init__(self, input_size: int, hidden_size: int = 128, 
                     num_layers: int = 2, dropout: float = 0.2, num_heads: int = 4):
            super().__init__()
            
            # LSTM layers with improved architecture
            self.lstm = nn.LSTM(
                input_size=input_size,
                hidden_size=hidden_size,
                num_layers=num_layers,
                batch_first=True,
                dropout=dropout if num_layers > 1 else 0,
                bidirectional=True
            )
            
            # Multi-head attention mechanism (improved)
            self.attention = nn.MultiheadAttention(
                embed_dim=hidden_size * 2,
                num_heads=num_heads,
                dropout=dropout,
                batch_first=True
            )
            
            # Alternative self-attention for time steps
            self.self_attention = nn.MultiheadAttention(
                embed_dim=hidden_size * 2,
                num_heads=num_heads,
                dropout=dropout,
                batch_first=True
            )
            
            # Feed-forward network with residual connections
            self.ffn = nn.Sequential(
                nn.Linear(hidden_size * 2, hidden_size * 4),
                nn.GELU(),  # Better activation than ReLU
                nn.Dropout(dropout),
                nn.Linear(hidden_size * 4, hidden_size * 2),
                nn.Dropout(dropout)
            )
            
            # Fully connected layers with residual connection
            self.fc = nn.Sequential(
                nn.Linear(hidden_size * 2, hidden_size),
                nn.BatchNorm1d(hidden_size),
                nn.GELU(),
                nn.Dropout(dropout),
                nn.Linear(hidden_size, hidden_size // 2),
                nn.BatchNorm1d(hidden_size // 2),
                nn.GELU(),
                nn.Dropout(dropout * 0.5),
                nn.Linear(hidden_size // 2, 1),
                nn.Sigmoid()  # Output between 0 and 1 (slippage percentage)
            )
            
            # Layer normalization with improved stability
            self.layer_norm1 = nn.LayerNorm(hidden_size * 2)
            self.layer_norm2 = nn.LayerNorm(hidden_size * 2)
            self.dropout = nn.Dropout(dropout)
        
        def forward(self, x: torch.Tensor) -> torch.Tensor:
            # x shape: (batch_size, sequence_length, input_size)
            
            # LSTM layer
            lstm_out, (hidden, cell) = self.lstm(x)
            # lstm_out shape: (batch_size, sequence_length, hidden_size * 2)
            
            # Residual connection preparation
            residual = lstm_out
            
            # Layer normalization before attention
            lstm_out = self.layer_norm1(lstm_out)
            
            # Multi-head self-attention (improved attention mechanism)
            attn_out, attn_weights = self.self_attention(lstm_out, lstm_out, lstm_out)
            attn_out = self.dropout(attn_out)
            
            # Residual connection with layer norm
            attn_out = self.layer_norm2(residual + attn_out)
            
            # Feed-forward network with residual
            ffn_out = self.ffn(attn_out)
            attn_out = self.layer_norm2(attn_out + ffn_out)
            
            # Global average pooling over sequence dimension (better than last timestep)
            context_vector = torch.mean(attn_out, dim=1)
            
            # Fully connected layers
            output = self.fc(context_vector)
            
            return output
    
    def create_features(self, historical_data: pd.DataFrame, 
                       current_trade: Dict[str, Any]) -> np.ndarray:
        """Create feature matrix from historical data and current trade"""
        
        features = []
        
        # 1. Historical price features
        if len(historical_data) >= self.sequence_length:
            price_data = historical_data['price'].values[-self.sequence_length:]
            returns = np.diff(price_data) / price_data[:-1] if len(price_data) > 1 else np.array([0])
            
            # Statistical features
            price_mean = np.mean(price_data)
            price_std = np.std(price_data)
            price_min = np.min(price_data)
            price_max = np.max(price_data)
            
            # Volatility features
            volatility = np.std(returns) if len(returns) > 0 else 0
            max_drawdown = (price_max - price_min) / price_max if price_max > 0 else 0
            
            features.extend([
                price_mean, price_std, price_min, price_max,
                volatility, max_drawdown
            ])
        else:
            features.extend([0] * 6)
        
        # 2. Liquidity features
        liquidity_data = historical_data['liquidity'].values[-self.sequence_length:] \
            if 'liquidity' in historical_data.columns and len(historical_data) > 0 else []
        
        if len(liquidity_data) > 0:
            liquidity_mean = np.mean(liquidity_data)
            liquidity_std = np.std(liquidity_data)
            liquidity_trend = np.polyfit(range(len(liquidity_data)), liquidity_data, 1)[0] if len(liquidity_data) > 1 else 0
            
            features.extend([liquidity_mean, liquidity_std, liquidity_trend])
        else:
            features.extend([0] * 3)
        
        # 3. Trade-specific features
        amount_in_usd = float(current_trade.get('amount_in_usd', 0))
        token_pair = current_trade.get('token_pair', 'unknown')
        hour_of_day = current_trade.get('hour_of_day', datetime.now().hour)
        day_of_week = current_trade.get('day_of_week', datetime.now().weekday())
        
        # Amount to liquidity ratio
        if len(liquidity_data) > 0:
            amount_to_liquidity = amount_in_usd / (liquidity_mean if liquidity_mean > 0 else 1)
        else:
            amount_to_liquidity = amount_in_usd / 10000  # Default
        
        # Time-based features
        is_trading_hours = 1 if 9 <= hour_of_day <= 17 else 0
        is_weekend = 1 if day_of_week >= 5 else 0
        
        features.extend([
            amount_in_usd,
            amount_to_liquidity,
            hour_of_day,
            day_of_week,
            is_trading_hours,
            is_weekend
        ])
        
        # 4. Market condition features
        if len(historical_data) > 1:
            volume_data = historical_data['volume'].values[-self.sequence_length:] \
                if 'volume' in historical_data.columns else []
            
            if len(volume_data) > 0:
                volume_mean = np.mean(volume_data)
                volume_ratio = volume_mean / (liquidity_mean if liquidity_mean > 0 else 1)
                features.extend([volume_mean, volume_ratio])
            else:
                features.extend([0, 0])
            
            # Price momentum
            recent_prices = historical_data['price'].values[-5:] if len(historical_data) >= 5 else []
            if len(recent_prices) >= 2:
                price_momentum = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]
                features.append(price_momentum)
            else:
                features.append(0)
        else:
            features.extend([0, 0, 0])
        
        return np.array(features).reshape(1, -1)
    
    def create_sequences(self, historical_data: pd.DataFrame) -> Optional[np.ndarray]:
        """Create sequences for LSTM input"""
        if len(historical_data) < self.sequence_length:
            return None
        
        sequences = []
        for i in range(len(historical_data) - self.sequence_length + 1):
            sequence = historical_data.iloc[i:i + self.sequence_length]
            
            seq_features = []
            for _, row in sequence.iterrows():
                features = [
                    row.get('price', 0),
                    row.get('liquidity', 0) / 1000000,  # Normalize
                    row.get('volume', 0) / 10000,  # Normalize
                ]
                seq_features.append(features)
            
            sequences.append(seq_features)
        
        return np.array(sequences) if sequences else None
    
    async def train(self, X_sequences: np.ndarray, y: np.ndarray, 
                   epochs: int = 100, batch_size: int = 32, **kwargs):
        """Train the LSTM model"""
        
        # Convert to PyTorch tensors
        X_tensor = torch.FloatTensor(X_sequences).to(device)
        y_tensor = torch.FloatTensor(y).to(device).reshape(-1, 1)
        
        # Create model
        input_size = X_sequences.shape[2]
        self.model = self.LSTMAttentionModel(input_size=input_size, num_heads=4).to(device)
        
        # Improved loss function with Huber loss for robustness
        criterion = nn.HuberLoss(delta=1.0)  # More robust to outliers
        
        # Improved optimizer with better learning rate scheduling
        optimizer = optim.AdamW(
            self.model.parameters(), 
            lr=0.001, 
            weight_decay=0.01,
            betas=(0.9, 0.999),
            eps=1e-8
        )
        
        # Cosine annealing with warm restarts for better convergence
        scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(
            optimizer, T_0=20, T_mult=2, eta_min=1e-6
        )
        
        # Training loop
        train_loader = DataLoader(
            list(zip(X_tensor, y_tensor)),
            batch_size=batch_size,
            shuffle=True
        )
        
        self.model.train()
        for epoch in range(epochs):
            epoch_loss = 0
            for batch_X, batch_y in train_loader:
                optimizer.zero_grad()
                
                predictions = self.model(batch_X)
                loss = criterion(predictions, batch_y)
                
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                optimizer.step()
                
                epoch_loss += loss.item()
            
            avg_loss = epoch_loss / len(train_loader)
            scheduler.step()
            
            # Calculate validation metrics if validation set available
            if epoch % 10 == 0:
                # Evaluate on a subset for monitoring
                self.model.eval()
                val_loss = 0
                with torch.no_grad():
                    val_subset = list(zip(X_tensor[:batch_size], y_tensor[:batch_size]))
                    for val_X, val_y in val_subset:
                        val_X = val_X.unsqueeze(0)
                        val_pred = self.model(val_X)
                        val_loss += criterion(val_pred, val_y.unsqueeze(0)).item()
                val_loss /= len(val_subset) if val_subset else 1
                self.model.train()
                
                logger.info(f"Epoch {epoch}: Train Loss = {avg_loss:.6f}, Val Loss = {val_loss:.6f}, LR = {optimizer.param_groups[0]['lr']:.6f}")
            
            self.training_history.append({
                'epoch': epoch,
                'loss': avg_loss,
                'lr': optimizer.param_groups[0]['lr']
            })
        
        self.is_trained = True
        logger.info("Slippage prediction model training completed")
    
    async def predict(self, X_sequence: np.ndarray) -> np.ndarray:
        """Predict slippage percentage"""
        if not self.is_trained or self.model is None:
            raise ValueError("Model not trained")
        
        self.model.eval()
        with torch.no_grad():
            X_tensor = torch.FloatTensor(X_sequence).to(device)
            predictions = self.model(X_tensor)
        
        # Convert to slippage percentage (0-100%)
        return predictions.cpu().numpy() * 100

# ============================================================================
# 2. Liquidity Pattern Model (Transformer-based Time Series)
# ============================================================================

class LiquidityPatternModel(BaseAIModel):
    """Transformer-based model for liquidity pattern recognition"""
    
    def __init__(self):
        super().__init__("liquidity_pattern", "1.0.0")
        self.model = None
        self.sequence_length = 24  # Hours
        self.prediction_horizon = 6  # Predict next 6 hours
    
    class PositionalEncoding(nn.Module):
        """Positional encoding for transformer"""
        
        def __init__(self, d_model: int, dropout: float = 0.1, max_len: int = 5000):
            super().__init__()
            self.dropout = nn.Dropout(p=dropout)
            
            position = torch.arange(max_len).unsqueeze(1)
            div_term = torch.exp(torch.arange(0, d_model, 2) * (-np.log(10000.0) / d_model))
            
            pe = torch.zeros(max_len, 1, d_model)
            pe[:, 0, 0::2] = torch.sin(position * div_term)
            pe[:, 0, 1::2] = torch.cos(position * div_term)
            
            self.register_buffer('pe', pe)
        
        def forward(self, x: torch.Tensor) -> torch.Tensor:
            x = x + self.pe[:x.size(1), :].transpose(0, 1)
            return self.dropout(x)
    
    class TimeSeriesTransformer(nn.Module):
        """Transformer model for time series forecasting"""
        
        def __init__(self, input_dim: int, model_dim: int = 64, 
                     num_heads: int = 4, num_layers: int = 3,
                     dropout: float = 0.1):
            super().__init__()
            
            self.input_projection = nn.Linear(input_dim, model_dim)
            
            # Positional encoding
            self.positional_encoding = LiquidityPatternModel.PositionalEncoding(model_dim, dropout)
            
            # Transformer encoder
            encoder_layer = nn.TransformerEncoderLayer(
                d_model=model_dim,
                nhead=num_heads,
                dim_feedforward=model_dim * 4,
                dropout=dropout,
                batch_first=True
            )
            self.transformer_encoder = nn.TransformerEncoder(
                encoder_layer,
                num_layers=num_layers
            )
            
            # Decoder
            self.decoder = nn.Sequential(
                nn.Linear(model_dim, model_dim * 2),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(model_dim * 2, model_dim),
                nn.ReLU(),
                nn.Linear(model_dim, 1)  # Predict liquidity
            )
        
        def forward(self, x: torch.Tensor) -> torch.Tensor:
            # x shape: (batch_size, sequence_length, input_dim)
            
            # Project input to model dimension
            x = self.input_projection(x)
            
            # Add positional encoding
            x = self.positional_encoding(x)
            
            # Transformer encoder
            encoded = self.transformer_encoder(x)
            
            # Use last time step for prediction
            last_step = encoded[:, -1, :]
            
            # Decode
            output = self.decoder(last_step)
            
            return output
    
    async def train(self, X_sequences: np.ndarray, y: np.ndarray, 
                   epochs: int = 50, batch_size: int = 32, **kwargs):
        """Train the transformer model"""
        
        # Convert to PyTorch tensors
        X_tensor = torch.FloatTensor(X_sequences).to(device)
        y_tensor = torch.FloatTensor(y).to(device).reshape(-1, 1)
        
        # Create model
        input_dim = X_sequences.shape[2]
        self.model = self.TimeSeriesTransformer(input_dim=input_dim).to(device)
        
        # Loss and optimizer
        criterion = nn.HuberLoss()  # Robust to outliers
        optimizer = optim.Adam(self.model.parameters(), lr=0.0001)
        scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(
            optimizer, T_0=10, T_mult=2
        )
        
        # Training loop
        train_loader = DataLoader(
            list(zip(X_tensor, y_tensor)),
            batch_size=batch_size,
            shuffle=True
        )
        
        self.model.train()
        for epoch in range(epochs):
            epoch_loss = 0
            for batch_X, batch_y in train_loader:
                optimizer.zero_grad()
                
                predictions = self.model(batch_X)
                loss = criterion(predictions, batch_y)
                
                loss.backward()
                optimizer.step()
                
                epoch_loss += loss.item()
            
            scheduler.step()
            
            if epoch % 5 == 0:
                logger.info(f"Epoch {epoch}: Loss = {epoch_loss/len(train_loader):.6f}")
    
    async def predict_liquidity_trend(self, historical_data: pd.DataFrame) -> Dict[str, Any]:
        """Predict future liquidity trends"""
        
        # Prepare sequence data
        sequences = self._prepare_sequences(historical_data)
        
        if sequences is None or len(sequences) == 0:
            return {"error": "Insufficient historical data"}
        
        # Make predictions
        if not self.is_trained or self.model is None:
            return {"error": "Model not trained"}
        
        self.model.eval()
        with torch.no_grad():
            X_tensor = torch.FloatTensor(sequences).to(device)
            predictions = self.model(X_tensor)
        
        predictions_np = predictions.cpu().numpy().flatten()
        
        # Analyze trend
        trend = "stable"
        if len(predictions_np) > 1:
            slope = np.polyfit(range(len(predictions_np)), predictions_np, 1)[0]
            if slope > 0.01:
                trend = "increasing"
            elif slope < -0.01:
                trend = "decreasing"
        
        return {
            "predicted_liquidity": float(np.mean(predictions_np)),
            "trend": trend,
            "confidence": float(1.0 - np.std(predictions_np) / np.mean(predictions_np) 
                              if np.mean(predictions_np) > 0 else 0.5),
            "predictions": predictions_np.tolist()
        }
    
    def _prepare_sequences(self, data: pd.DataFrame) -> Optional[np.ndarray]:
        """Prepare sequences for transformer input"""
        if len(data) < self.sequence_length:
            return None
        
        features = []
        for i in range(len(data) - self.sequence_length + 1):
            sequence = data.iloc[i:i + self.sequence_length]
            
            # Extract features from sequence
            seq_features = []
            
            # Liquidity features
            if 'liquidity' in sequence.columns:
                liquidity = sequence['liquidity'].values
                seq_features.extend([
                    np.mean(liquidity),
                    np.std(liquidity),
                    np.min(liquidity),
                    np.max(liquidity),
                    np.median(liquidity)
                ])
            
            # Price features
            if 'price' in sequence.columns:
                price = sequence['price'].values
                returns = np.diff(price) / price[:-1] if len(price) > 1 else np.array([0])
                
                seq_features.extend([
                    np.mean(price),
                    np.std(price),
                    np.mean(returns) if len(returns) > 0 else 0,
                    np.std(returns) if len(returns) > 0 else 0
                ])
            
            # Volume features
            if 'volume' in sequence.columns:
                volume = sequence['volume'].values
                seq_features.extend([
                    np.mean(volume),
                    np.std(volume)
                ])
            
            # Time features
            if 'hour' in sequence.columns:
                hour = sequence['hour'].values[-1]
                seq_features.append(hour / 24)  # Normalize
            
            features.append(seq_features)
        
        return np.array(features) if features else None

# ============================================================================
# 3. Route Optimization Model (Reinforcement Learning)
# ============================================================================

class RouteOptimizationModel:
    """Deep Q-Network for optimal route selection"""
    
    def __init__(self, state_size: int, action_size: int):
        self.state_size = state_size
        self.action_size = action_size
        self.memory = deque(maxlen=10000)
        self.gamma = 0.95  # Discount factor
        self.epsilon = 1.0  # Exploration rate
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.995
        self.learning_rate = 0.001
        self.batch_size = 64
        
        # Main network and target network
        self.model = self._build_model()
        self.target_model = self._build_model()
        self.update_target_model()
    
    class DQNNetwork(nn.Module):
        """Deep Q-Network architecture"""
        
        def __init__(self, state_size: int, action_size: int):
            super().__init__()
            
            self.fc1 = nn.Linear(state_size, 128)
            self.bn1 = nn.BatchNorm1d(128)
            
            self.fc2 = nn.Linear(128, 128)
            self.bn2 = nn.BatchNorm1d(128)
            
            self.fc3 = nn.Linear(128, 64)
            self.bn3 = nn.BatchNorm1d(64)
            
            self.fc4 = nn.Linear(64, action_size)
            
            self.dropout = nn.Dropout(0.2)
        
        def forward(self, x: torch.Tensor) -> torch.Tensor:
            x = F.relu(self.bn1(self.fc1(x)))
            x = self.dropout(x)
            
            x = F.relu(self.bn2(self.fc2(x)))
            x = self.dropout(x)
            
            x = F.relu(self.bn3(self.fc3(x)))
            
            return self.fc4(x)
    
    def _build_model(self) -> nn.Module:
        """Build DQN model"""
        return self.DQNNetwork(self.state_size, self.action_size).to(device)
    
    def update_target_model(self):
        """Update target network weights"""
        self.target_model.load_state_dict(self.model.state_dict())
    
    def remember(self, state: np.ndarray, action: int, reward: float, 
                next_state: np.ndarray, done: bool):
        """Store experience in replay memory"""
        self.memory.append((state, action, reward, next_state, done))
    
    def act(self, state: np.ndarray) -> int:
        """Choose action using epsilon-greedy policy"""
        if np.random.rand() <= self.epsilon:
            return np.random.choice(self.action_size)
        
        state_tensor = torch.FloatTensor(state).to(device).unsqueeze(0)
        self.model.eval()
        with torch.no_grad():
            q_values = self.model(state_tensor)
        return torch.argmax(q_values).item()
    
    def replay(self):
        """Train on replay memory"""
        if len(self.memory) < self.batch_size:
            return
        
        # Sample batch from memory
        batch = np.random.choice(len(self.memory), self.batch_size, replace=False)
        states, actions, rewards, next_states, dones = zip(
            *[self.memory[i] for i in batch]
        )
        
        # Convert to tensors
        states = torch.FloatTensor(np.array(states)).to(device)
        actions = torch.LongTensor(np.array(actions)).to(device)
        rewards = torch.FloatTensor(np.array(rewards)).to(device)
        next_states = torch.FloatTensor(np.array(next_states)).to(device)
        dones = torch.FloatTensor(np.array(dones)).to(device)
        
        # Get current Q values
        self.model.train()
        current_q = self.model(states).gather(1, actions.unsqueeze(1))
        
        # Get next Q values from target network
        with torch.no_grad():
            next_q = self.target_model(next_states).max(1)[0]
            target_q = rewards + (1 - dones) * self.gamma * next_q
        
        # Compute loss
        loss = F.mse_loss(current_q.squeeze(), target_q)
        
        # Optimize
        optimizer = optim.Adam(self.model.parameters(), lr=self.learning_rate)
        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
        optimizer.step()
        
        # Decay epsilon
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
        
        return loss.item()

# ============================================================================
# 4. Risk Assessment Model (Ensemble Classifier)
# ============================================================================

class RiskAssessmentModel(BaseAIModel):
    """Ensemble model for risk assessment"""
    
    def __init__(self):
        super().__init__("risk_assessment", "1.0.0")
        self.models = {}
        self.voting_classifier = None
        self.label_encoder = LabelEncoder()
        self.risk_classes = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
    
    async def train(self, X: np.ndarray, y: np.ndarray, **kwargs):
        """Train ensemble of models"""
        
        # Encode labels
        y_encoded = self.label_encoder.fit_transform(y)
        
        # Split data
        X_train, X_val, y_train, y_val = train_test_split(
            X, y_encoded, test_size=0.2, random_state=42
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)
        
        # Train individual models
        logger.info("Training Random Forest...")
        self.models['rf'] = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            random_state=42
        )
        self.models['rf'].fit(X_train_scaled, y_train)
        
        logger.info("Training XGBoost...")
        self.models['xgb'] = xgb.XGBRegressor(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=42
        )
        self.models['xgb'].fit(X_train_scaled, y_train)
        
        logger.info("Training LightGBM...")
        self.models['lgb'] = lgb.LGBMRegressor(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=42
        )
        self.models['lgb'].fit(X_train_scaled, y_train)
        
        # Create voting classifier
        self.voting_classifier = VotingClassifier(
            estimators=[
                ('rf', RandomForestClassifier(n_estimators=50, random_state=42)),
                ('xgb', xgb.XGBClassifier(n_estimators=50, random_state=42)),
                ('lgb', lgb.LGBMClassifier(n_estimators=50, random_state=42))
            ],
            voting='soft'
        )
        
        # For voting classifier, we need classification
        y_train_class = np.where(y_train >= 2.5, 1, 0)  # Binary classification
        self.voting_classifier.fit(X_train_scaled, y_train_class)
        
        # Evaluate
        self._evaluate_models(X_val_scaled, y_val)
        
        self.is_trained = True
        self.feature_columns = [f"feature_{i}" for i in range(X.shape[1])]
        self.target_column = "risk_score"
    
    def _evaluate_models(self, X_val: np.ndarray, y_val: np.ndarray):
        """Evaluate model performance"""
        for name, model in self.models.items():
            y_pred = model.predict(X_val)
            mae = mean_absolute_error(y_val, y_pred)
            rmse = np.sqrt(mean_squared_error(y_val, y_pred))
            logger.info(f"{name.upper()} - MAE: {mae:.4f}, RMSE: {rmse:.4f}")
    
    async def predict_risk_score(self, features: np.ndarray) -> Dict[str, Any]:
        """Predict risk score and class"""
        if not self.is_trained:
            raise ValueError("Model not trained")
        
        # Scale features
        features_scaled = self.scaler.transform(features.reshape(1, -1))
        
        # Get predictions from all models
        predictions = {}
        for name, model in self.models.items():
            pred = model.predict(features_scaled)[0]
            predictions[name] = float(pred)
        
        # Ensemble prediction (weighted average)
        weights = {'rf': 0.4, 'xgb': 0.35, 'lgb': 0.25}
        ensemble_score = sum(predictions[name] * weights[name] for name in predictions)
        
        # Get risk class
        if ensemble_score < 1.5:
            risk_class = 'LOW'
        elif ensemble_score < 2.5:
            risk_class = 'MEDIUM'
        elif ensemble_score < 3.5:
            risk_class = 'HIGH'
        else:
            risk_class = 'CRITICAL'
        
        # Get binary classification from voting classifier
        binary_risk = self.voting_classifier.predict(features_scaled)[0]
        
        return {
            'risk_score': float(ensemble_score),
            'risk_class': risk_class,
            'binary_risk': 'HIGH' if binary_risk == 1 else 'LOW',
            'model_predictions': predictions,
            'confidence': self._calculate_confidence(predictions, ensemble_score)
        }
    
    def _calculate_confidence(self, predictions: Dict[str, float], 
                            ensemble_score: float) -> float:
        """Calculate prediction confidence"""
        # Confidence is higher when models agree
        variance = np.var(list(predictions.values()))
        max_variance = 2.0  # Maximum expected variance
        
        confidence = 1.0 - min(variance / max_variance, 1.0)
        
        # Adjust confidence based on risk level
        if ensemble_score > 3.0:  # High risk
            confidence *= 0.8  # Lower confidence for extreme predictions
        
        return round(confidence, 2)

# ============================================================================
# 5. Gas Price Prediction Model (Transformer)
# ============================================================================

class GasPricePredictionModel(BaseAIModel):
    """Transformer model for gas price prediction"""
    
    def __init__(self):
        super().__init__("gas_price_predictor", "1.0.0")
        self.model = None
        self.sequence_length = 12  # Hours
    
    class GasPriceTransformer(nn.Module):
        """Transformer for gas price prediction"""
        
        def __init__(self, input_dim: int, model_dim: int = 32, 
                     num_heads: int = 4, num_layers: int = 2):
            super().__init__()
            
            self.input_projection = nn.Linear(input_dim, model_dim)
            
            # Transformer encoder
            encoder_layer = nn.TransformerEncoderLayer(
                d_model=model_dim,
                nhead=num_heads,
                dim_feedforward=model_dim * 4,
                dropout=0.1,
                batch_first=True
            )
            self.transformer = nn.TransformerEncoder(encoder_layer, num_layers)
            
            # Temporal attention
            self.temporal_attention = nn.MultiheadAttention(
                model_dim, num_heads=2, batch_first=True
            )
            
            # Output layers
            self.fc = nn.Sequential(
                nn.Linear(model_dim, model_dim * 2),
                nn.ReLU(),
                nn.Dropout(0.1),
                nn.Linear(model_dim * 2, model_dim),
                nn.ReLU(),
                nn.Linear(model_dim, 1)
            )
        
        def forward(self, x: torch.Tensor) -> torch.Tensor:
            # Project input
            x = self.input_projection(x)
            
            # Transformer encoding
            encoded = self.transformer(x)
            
            # Temporal attention
            attn_output, _ = self.temporal_attention(encoded, encoded, encoded)
            
            # Use last time step
            last_step = attn_output[:, -1, :]
            
            # Final prediction
            output = self.fc(last_step)
            
            return output
    
    async def train(self, X_sequences: np.ndarray, y: np.ndarray, 
                   epochs: int = 50, batch_size: int = 32, **kwargs):
        """Train the gas price prediction model"""
        
        # Convert to PyTorch tensors
        X_tensor = torch.FloatTensor(X_sequences).to(device)
        y_tensor = torch.FloatTensor(y).to(device).reshape(-1, 1)
        
        # Create model
        input_dim = X_sequences.shape[2]
        self.model = self.GasPriceTransformer(input_dim=input_dim).to(device)
        
        # Loss and optimizer
        criterion = nn.HuberLoss()  # Robust to outliers in gas prices
        optimizer = optim.Adam(self.model.parameters(), lr=0.0005)
        scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=20, gamma=0.5)
        
        # Training loop
        train_loader = DataLoader(
            list(zip(X_tensor, y_tensor)),
            batch_size=batch_size,
            shuffle=True
        )
        
        self.model.train()
        for epoch in range(epochs):
            epoch_loss = 0
            for batch_X, batch_y in train_loader:
                optimizer.zero_grad()
                
                predictions = self.model(batch_X)
                loss = criterion(predictions, batch_y)
                
                loss.backward()
                optimizer.step()
                
                epoch_loss += loss.item()
            
            scheduler.step()
            
            if epoch % 10 == 0:
                logger.info(f"Epoch {epoch}: Loss = {epoch_loss/len(train_loader):.6f}")
        
        self.is_trained = True
    
    async def predict_gas_price(self, historical_gas_data: np.ndarray,
                              network_conditions: Dict[str, Any]) -> Dict[str, Any]:
        """Predict optimal gas price for transaction"""
        
        # Prepare input sequence
        sequence = self._prepare_gas_sequence(historical_gas_data, network_conditions)
        
        if sequence is None:
            return {"error": "Insufficient data for prediction"}
        
        if not self.is_trained or self.model is None:
            return {"error": "Model not trained"}
        
        # Make prediction
        self.model.eval()
        with torch.no_grad():
            X_tensor = torch.FloatTensor(sequence).to(device).unsqueeze(0)
            prediction = self.model(X_tensor)
        
        predicted_price = float(prediction.item())
        
        # Calculate confidence interval
        confidence_interval = self._calculate_confidence_interval(
            historical_gas_data, predicted_price
        )
        
        # Recommend gas price (add buffer)
        recommended_price = predicted_price * 1.1  # 10% buffer
        
        return {
            "predicted_base_gas": predicted_price,
            "recommended_gas": recommended_price,
            "confidence_interval": confidence_interval,
            "suggested_priority_fee": recommended_price * 0.1,  # 10% of base fee
            "max_fee": recommended_price * 1.5,  # 50% buffer for max fee
            "timestamp": datetime.now().isoformat()
        }
    
    def _prepare_gas_sequence(self, historical_data: np.ndarray,
                            network_conditions: Dict[str, Any]) -> Optional[np.ndarray]:
        """Prepare input sequence for gas prediction"""
        if len(historical_data) < self.sequence_length:
            return None
        
        # Get recent gas prices
        recent_gas = historical_data[-self.sequence_length:]
        
        # Create features
        features = []
        for i in range(len(recent_gas)):
            # Gas price features
            gas_price = recent_gas[i]
            
            # Statistical features for window ending at i
            window_end = i + 1
            window = recent_gas[max(0, window_end - 5):window_end]
            
            window_mean = np.mean(window)
            window_std = np.std(window) if len(window) > 1 else 0
            window_min = np.min(window)
            window_max = np.max(window)
            
            # Time features
            hour_of_day = (i % 24) / 24
            
            # Network conditions (if available)
            network_congestion = network_conditions.get('congestion', 0.5)
            pending_transactions = network_conditions.get('pending_txs', 0)
            
            features.append([
                gas_price,
                window_mean,
                window_std,
                window_min,
                window_max,
                hour_of_day,
                network_congestion,
                pending_transactions / 10000  # Normalized
            ])
        
        return np.array(features)
    
    def _calculate_confidence_interval(self, historical_data: np.ndarray,
                                     predicted_price: float) -> Tuple[float, float]:
        """Calculate confidence interval for prediction"""
        if len(historical_data) < 2:
            return predicted_price * 0.9, predicted_price * 1.1
        
        # Calculate historical volatility
        returns = np.diff(historical_data) / historical_data[:-1]
        volatility = np.std(returns) if len(returns) > 0 else 0.1
        
        # 95% confidence interval
        lower_bound = predicted_price * (1 - 1.96 * volatility)
        upper_bound = predicted_price * (1 + 1.96 * volatility)
        
        return float(lower_bound), float(upper_bound)

# ============================================================================
# 6. Execution Success Model (Binary Classifier)
# ============================================================================

class ExecutionSuccessModel(BaseAIModel):
    """Binary classifier for predicting execution success"""
    
    def __init__(self):
        super().__init__("execution_success", "1.0.0")
        self.model = None
        self.threshold = 0.7  # Confidence threshold
    
    class SuccessClassifier(nn.Module):
        """Neural network classifier for execution success"""
        
        def __init__(self, input_size: int, hidden_size: int = 64):
            super().__init__()
            
            self.network = nn.Sequential(
                nn.Linear(input_size, hidden_size),
                nn.BatchNorm1d(hidden_size),
                nn.ReLU(),
                nn.Dropout(0.3),
                
                nn.Linear(hidden_size, hidden_size // 2),
                nn.BatchNorm1d(hidden_size // 2),
                nn.ReLU(),
                nn.Dropout(0.3),
                
                nn.Linear(hidden_size // 2, hidden_size // 4),
                nn.BatchNorm1d(hidden_size // 4),
                nn.ReLU(),
                
                nn.Linear(hidden_size // 4, 1),
                nn.Sigmoid()
            )
        
        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return self.network(x)
    
    async def train(self, X: np.ndarray, y: np.ndarray, 
                   epochs: int = 50, batch_size: int = 32, **kwargs):
        """Train the success classifier"""
        
        # Convert to PyTorch tensors
        X_tensor = torch.FloatTensor(X).to(device)
        y_tensor = torch.FloatTensor(y).to(device).reshape(-1, 1)
        
        # Create model
        input_size = X.shape[1]
        self.model = self.SuccessClassifier(input_size=input_size).to(device)
        
        # Loss and optimizer
        criterion = nn.BCELoss()  # Binary cross-entropy
        optimizer = optim.Adam(self.model.parameters(), lr=0.001)
        
        # Class weights for imbalanced data
        pos_weight = torch.tensor([(len(y) - sum(y)) / sum(y)]).to(device) \
            if sum(y) > 0 else torch.tensor([1.0]).to(device)
        
        # Training loop
        train_loader = DataLoader(
            list(zip(X_tensor, y_tensor)),
            batch_size=batch_size,
            shuffle=True
        )
        
        self.model.train()
        for epoch in range(epochs):
            epoch_loss = 0
            correct = 0
            total = 0
            
            for batch_X, batch_y in train_loader:
                optimizer.zero_grad()
                
                predictions = self.model(batch_X)
                loss = criterion(predictions, batch_y)
                
                # Apply class weights
                loss = loss * (batch_y * pos_weight + (1 - batch_y))
                loss = loss.mean()
                
                loss.backward()
                optimizer.step()
                
                epoch_loss += loss.item()
                
                # Calculate accuracy
                predicted_classes = (predictions > 0.5).float()
                correct += (predicted_classes == batch_y).sum().item()
                total += batch_y.size(0)
            
            accuracy = correct / total if total > 0 else 0
            
            if epoch % 10 == 0:
                logger.info(f"Epoch {epoch}: Loss = {epoch_loss/len(train_loader):.4f}, "
                          f"Accuracy = {accuracy:.4f}")
        
        self.is_trained = True
    
    async def predict_success_probability(self, features: np.ndarray) -> Dict[str, Any]:
        """Predict probability of execution success"""
        if not self.is_trained or self.model is None:
            raise ValueError("Model not trained")
        
        self.model.eval()
        with torch.no_grad():
            X_tensor = torch.FloatTensor(features).to(device)
            probability = self.model(X_tensor)
        
        prob = float(probability.item())
        
        # Determine success prediction
        will_succeed = prob > self.threshold
        
        # Calculate confidence
        confidence = abs(prob - 0.5) * 2  # Higher when probability is farther from 0.5
        
        # Identify risk factors
        risk_factors = self._identify_risk_factors(features, prob)
        
        return {
            "success_probability": prob,
            "predicted_success": bool(will_succeed),
            "confidence": confidence,
            "risk_factors": risk_factors,
            "recommendation": "Proceed" if will_succeed else "Delay or adjust parameters"
        }
    
    def _identify_risk_factors(self, features: np.ndarray, 
                             probability: float) -> List[str]:
        """Identify potential risk factors based on features"""
        risk_factors = []
        
        # Check specific feature thresholds (example)
        # These thresholds would be learned from data in production
        
        # Feature 0: gas_price_too_high (example)
        if len(features) > 0 and features[0] > 0.8:  # High gas price
            risk_factors.append("High gas price may cause execution failure")
        
        # Feature 1: liquidity_too_low (example)
        if len(features) > 1 and features[1] < 0.3:  # Low liquidity
            risk_factors.append("Low liquidity may cause slippage issues")
        
        # Feature 2: network_congestion (example)
        if len(features) > 2 and features[2] > 0.7:  # High network congestion
            risk_factors.append("Network congestion may delay execution")
        
        # Feature 3: trade_size_ratio (example)
        if len(features) > 3 and features[3] > 0.5:  # Large trade relative to liquidity
            risk_factors.append("Large trade size may cause price impact")
        
        # Low probability itself is a risk factor
        if probability < 0.3:
            risk_factors.append("Low predicted success probability")
        
        return risk_factors
