# C.L.E.O. Backend API

Backend API server for the Cronos Liquidity Execution Orchestrator (C.L.E.O.) project.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Copy environment variables:
```bash
cp .env.example .env
```

3. Edit `.env` with your configuration (optional - defaults work for demo)

4. Run the server:
```bash
python main.py
```

Or with uvicorn directly:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

- `GET /` - Health check
- `GET /health` - Detailed health status
- `GET /api/pools/{token_in}/{token_out}` - Get available pools for a token pair
- `POST /api/optimize` - Optimize route splits using AI
- `POST /api/simulate` - Simulate execution of routes
- `GET /api/liquidity/{pair}` - Get liquidity data for a trading pair

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Development

The backend uses:
- FastAPI for the API server
- Web3.py for blockchain interaction
- scikit-learn for ML models
- SQLAlchemy for data persistence

## Notes

- The AI agent SDK is optional - the code will work without it using fallback implementations
- Redis is optional - caching will be skipped if not available
- Database defaults to SQLite for easy setup

