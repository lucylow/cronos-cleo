# C.L.E.O. AI Models

Complete AI model system for Cronos Liquidity Execution Orchestrator.

## Overview

The C.L.E.O. AI Model System provides sophisticated machine learning models for optimizing token swaps across multiple DEXs on Cronos. The system includes 6 specialized models:

1. **Slippage Prediction Model** (LSTM + Attention) - Predicts slippage percentage
2. **Liquidity Pattern Model** (Transformer) - Analyzes liquidity trends
3. **Route Optimization Model** (Reinforcement Learning) - Optimizes route selection
4. **Risk Assessment Model** (Ensemble) - Assesses trade risk
5. **Gas Price Prediction Model** (Transformer) - Predicts optimal gas prices
6. **Execution Success Model** (Binary Classifier) - Predicts execution success probability

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Train Models

```bash
python train_models.py
```

This will:
- Generate synthetic training data
- Train all AI models
- Save models to `models/` directory
- Create model card and metadata

### 3. Test Models

```bash
python test_ai_models.py
```

### 4. Use in Code

```python
from ai.model_orchestrator import AIModelOrchestrator
import pandas as pd
import numpy as np

# Initialize orchestrator
orchestrator = AIModelOrchestrator()
await orchestrator.initialize()

# Prepare trade data
trade_data = {
    'trade_id': 'trade_001',
    'amount_in_usd': 5000.0,
    'token_pair': 'CRO/USDC',
    'max_slippage_percent': 1.0,
    'historical_data': pd.DataFrame({
        'price': np.random.normal(0.08, 0.001, 100),
        'liquidity': np.random.normal(1000000, 100000, 100),
        'volume': np.random.exponential(10000, 100)
    }),
    'historical_gas_prices': np.random.normal(10, 2, 50),
    'network_conditions': {'congestion': 0.3, 'pending_txs': 1500}
}

# Run AI analysis
analysis = await orchestrator.analyze_trade(trade_data)

print(f"Recommended Action: {analysis['recommendation']['action']}")
print(f"Confidence: {analysis['confidence_score']}")
```

## Model Details

### Slippage Prediction Model

- **Type**: LSTM with Attention Mechanism
- **Input**: Historical price, liquidity, volume data + trade parameters
- **Output**: Predicted slippage percentage (0-100%)
- **Use Case**: Estimate slippage before executing trades

### Liquidity Pattern Model

- **Type**: Time Series Transformer
- **Input**: Historical liquidity patterns
- **Output**: Liquidity trend (increasing/decreasing/stable) + predictions
- **Use Case**: Identify optimal timing for trades

### Risk Assessment Model

- **Type**: Ensemble (Random Forest + XGBoost + LightGBM)
- **Input**: Trade size, market volatility, liquidity, network conditions
- **Output**: Risk score (1-4) and risk class (LOW/MEDIUM/HIGH/CRITICAL)
- **Use Case**: Evaluate trade risk before execution

### Gas Price Prediction Model

- **Type**: Transformer with Temporal Attention
- **Input**: Historical gas prices, network conditions
- **Output**: Recommended gas price with confidence interval
- **Use Case**: Optimize gas costs for transactions

### Execution Success Model

- **Type**: Neural Network Binary Classifier
- **Input**: Gas price ratio, liquidity sufficiency, slippage buffer, network health
- **Output**: Success probability (0-1) and risk factors
- **Use Case**: Predict if a trade will execute successfully

### Route Optimization Model

- **Type**: Deep Q-Network (DQN)
- **Input**: Trade state (amount, slippage, risk, market conditions)
- **Output**: Optimal route strategy and split configuration
- **Use Case**: Determine best route across multiple DEXs

## Integration with Agents

The AI models can be integrated with existing agents:

```python
from ai.integration_example import EnhancedSlippagePredictor

predictor = EnhancedSlippagePredictor()
await predictor.initialize()

prediction = await predictor.predict_slippage(
    amount=5000.0,
    liquidity=1000000.0,
    token_pair="CRO/USDC"
)
```

## Model Files

Trained models are saved in the `models/` directory:

- `slippage_predictor_v2.0.0.pkl` - Slippage prediction model
- `risk_assessment_v1.0.0.pkl` - Risk assessment model
- `execution_success_v1.0.0.pkl` - Success prediction model
- `liquidity_pattern_v1.0.0.pkl` - Liquidity pattern model
- `gas_price_predictor_v1.0.0.pkl` - Gas price prediction model
- `training_metadata.json` - Training metadata
- `model_card.json` - Model documentation

## Training Data

For hackathon demonstration, synthetic training data is generated using:
- Beta distributions for market conditions
- Exponential distributions for trade sizes
- Lognormal distributions for liquidity
- Realistic correlations between features

In production, models should be trained on real Cronos historical data.

## API Integration

The models can be accessed via the FastAPI backend:

```python
# In main.py
from ai.model_orchestrator import AIModelOrchestrator

orchestrator = AIModelOrchestrator()

@app.post("/api/ai/analyze-trade")
async def analyze_trade_ai(trade_data: dict):
    analysis = await orchestrator.analyze_trade(trade_data)
    return analysis
```

## Performance

Models are optimized for:
- **Low Latency**: Async inference for real-time decisions
- **Accuracy**: State-of-the-art architectures (LSTM, Transformers, Ensemble)
- **Robustness**: Handles missing data and edge cases
- **Interpretability**: Provides confidence scores and risk factors

## Limitations

- Models are trained on synthetic data for hackathon demonstration
- Production use requires real Cronos historical data
- Some models may need fine-tuning for specific token pairs
- Continuous learning from execution results recommended

## Future Enhancements

- Real-time model updates from execution results
- Multi-token pair specialized models
- Advanced reinforcement learning for route optimization
- Model ensemble voting for improved accuracy
- Integration with on-chain data feeds
