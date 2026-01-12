"""
Training Data Generator for C.L.E.O. AI Models
Generates synthetic training data for hackathon demonstration
"""

import numpy as np
import pandas as pd
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class TrainingDataGenerator:
    """Generate synthetic training data for hackathon demonstration"""
    
    @staticmethod
    def generate_slippage_training_data(n_samples: int = 10000) -> Dict[str, np.ndarray]:
        """Generate synthetic slippage training data"""
        np.random.seed(42)
        
        # Features
        amount_in_usd = np.random.exponential(5000, n_samples)  # Most trades small
        liquidity_usd = np.random.lognormal(10, 1, n_samples)  # Liquidity distribution
        volatility = np.random.beta(2, 5, n_samples)  # Most markets not volatile
        hour_of_day = np.random.randint(0, 24, n_samples)
        is_trading_hours = ((hour_of_day >= 9) & (hour_of_day <= 17)).astype(float)
        
        # Calculate slippage (simplified model)
        amount_ratio = amount_in_usd / liquidity_usd
        base_slippage = 0.001  # 0.1% base
        
        # Slippage increases with amount ratio and volatility
        slippage = base_slippage * (1 + amount_ratio * 10) * (1 + volatility * 5)
        
        # Add noise
        slippage *= np.random.lognormal(0, 0.1, n_samples)
        
        # Cap at 50%
        slippage = np.clip(slippage, 0, 0.5)
        
        # For LSTM, create sequences
        sequences = []
        sequence_length = 10
        
        for i in range(n_samples - sequence_length):
            seq_features = []
            for j in range(sequence_length):
                idx = i + j
                seq_features.append([
                    amount_in_usd[idx] / 10000,
                    liquidity_usd[idx] / 100000,
                    volatility[idx],
                    hour_of_day[idx] / 24,
                    is_trading_hours[idx]
                ])
            sequences.append(seq_features)
        
        X_sequences = np.array(sequences)
        y = slippage[sequence_length:].reshape(-1, 1)
        
        return {
            'X_sequences': X_sequences,
            'y': y
        }
    
    @staticmethod
    def generate_risk_training_data(n_samples: int = 5000) -> Dict[str, np.ndarray]:
        """Generate synthetic risk assessment training data"""
        np.random.seed(42)
        
        # Features
        trade_size_ratio = np.random.beta(2, 5, n_samples)  # Most trades small relative to liquidity
        market_volatility = np.random.exponential(0.5, n_samples)
        liquidity_score = np.random.beta(5, 2, n_samples)  # Mostly good liquidity
        network_congestion = np.random.beta(2, 3, n_samples)
        time_since_last_trade = np.random.exponential(10, n_samples)
        
        # Risk score (1-4)
        risk_score = (
            1 +  # Base
            trade_size_ratio * 2 +  # Larger trades = higher risk
            market_volatility * 1.5 +  # Volatility increases risk
            (1 - liquidity_score) * 1.5 +  # Low liquidity = higher risk
            network_congestion * 1 +  # Congestion increases risk
            np.random.normal(0, 0.2, n_samples)  # Noise
        )
        
        # Clip and round
        risk_score = np.clip(risk_score, 1, 4)
        risk_score = np.round(risk_score)
        
        X = np.column_stack([
            trade_size_ratio,
            market_volatility,
            liquidity_score,
            network_congestion,
            time_since_last_trade / 100  # Normalized
        ])
        
        return {'X': X, 'y': risk_score}
    
    @staticmethod
    def generate_success_training_data(n_samples: int = 8000) -> Dict[str, np.ndarray]:
        """Generate synthetic execution success training data"""
        np.random.seed(42)
        
        # Features
        gas_price_ratio = np.random.lognormal(0, 0.3, n_samples)  # Mostly around 1
        liquidity_sufficiency = np.random.beta(5, 2, n_samples)  # Mostly sufficient
        slippage_buffer = np.random.normal(2, 1, n_samples)  # Mostly positive buffer
        network_health = np.random.beta(3, 1, n_samples)  # Mostly healthy
        historical_success = np.random.beta(8, 2, n_samples)  # Mostly successful
        
        # Success probability (sigmoid of weighted sum)
        weights = np.array([-2, 1.5, 0.8, 1.2, 0.5])
        
        features = np.column_stack([
            gas_price_ratio,
            liquidity_sufficiency,
            slippage_buffer,
            network_health,
            historical_success
        ])
        
        linear_combination = np.dot(features, weights)
        success_prob = 1 / (1 + np.exp(-linear_combination))
        
        # Add noise
        success_prob += np.random.normal(0, 0.1, n_samples)
        success_prob = np.clip(success_prob, 0, 1)
        
        # Binary success (threshold at 0.5)
        success_binary = (success_prob > 0.5).astype(float)
        
        return {'X': features, 'y': success_binary}
    
    @staticmethod
    def generate_liquidity_training_data(n_samples: int = 6000) -> Dict[str, np.ndarray]:
        """Generate synthetic liquidity pattern training data"""
        np.random.seed(42)
        
        sequence_length = 24
        sequences = []
        targets = []
        
        for _ in range(n_samples):
            # Generate a sequence of liquidity data
            base_liquidity = np.random.lognormal(12, 0.5)
            trend = np.random.normal(0, 0.01)
            noise = np.random.normal(0, 0.05, sequence_length)
            
            sequence = []
            for t in range(sequence_length):
                # Liquidity with trend and noise
                liquidity = base_liquidity * (1 + trend * t) * (1 + noise[t])
                
                # Price features
                price = np.random.normal(0.08, 0.001)
                
                # Volume features
                volume = np.random.exponential(10000)
                
                sequence.append([
                    liquidity / 1000000,  # Normalized
                    price,
                    volume / 10000,  # Normalized
                    t / sequence_length  # Time feature
                ])
            
            sequences.append(sequence)
            # Target is next hour's liquidity
            targets.append(base_liquidity * (1 + trend * sequence_length) / 1000000)
        
        return {
            'X_sequences': np.array(sequences),
            'y': np.array(targets).reshape(-1, 1)
        }
    
    @staticmethod
    def generate_gas_training_data(n_samples: int = 5000) -> Dict[str, np.ndarray]:
        """Generate synthetic gas price training data"""
        np.random.seed(42)
        
        sequence_length = 12
        sequences = []
        targets = []
        
        for _ in range(n_samples):
            # Generate a sequence of gas prices
            base_gas = np.random.normal(10, 2)
            trend = np.random.normal(0, 0.1)
            noise = np.random.normal(0, 0.5, sequence_length)
            
            sequence = []
            gas_prices = []
            
            for t in range(sequence_length):
                gas_price = base_gas * (1 + trend * t / sequence_length) + noise[t]
                gas_price = max(1.0, gas_price)  # Minimum gas price
                gas_prices.append(gas_price)
                
                # Create features for each time step
                window = gas_prices[-5:] if len(gas_prices) >= 5 else gas_prices
                
                sequence.append([
                    gas_price,
                    np.mean(window),
                    np.std(window) if len(window) > 1 else 0,
                    np.min(window),
                    np.max(window),
                    (t % 24) / 24,  # Hour of day
                    np.random.beta(2, 3),  # Network congestion
                    np.random.exponential(1000) / 10000  # Pending transactions (normalized)
                ])
            
            sequences.append(sequence)
            # Target is next hour's gas price
            next_gas = base_gas * (1 + trend) + np.random.normal(0, 0.5)
            targets.append(max(1.0, next_gas))
        
        return {
            'X_sequences': np.array(sequences),
            'y': np.array(targets).reshape(-1, 1)
        }
