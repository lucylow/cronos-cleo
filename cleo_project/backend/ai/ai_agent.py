"""
AI Agent for route optimization
"""
import os
import sys
import numpy as np
from typing import Dict, List, Optional
from sklearn.ensemble import GradientBoostingRegressor
import joblib
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mcp_client import MCPClient

# Optional imports - will work without SDK
try:
    from crypto_ai_agent_sdk import Agent, Tool, MarketDataClient
    HAS_SDK = True
except ImportError:
    HAS_SDK = False
    # Create minimal stubs
    class Agent:
        def __init__(self, name: str):
            self.name = name
            self.tools = []
        def register_tool(self, tool):
            self.tools.append(tool)
    
    class Tool:
        def __init__(self, name: str, func, description: str):
            self.name = name
            self.func = func
            self.description = description
    
    class MarketDataClient:
        def __init__(self, api_key: Optional[str] = None):
            self.api_key = api_key
        async def get_market_summary(self, pair: str):
            return {"24h_volatility": 0.02}
        async def get_current_price(self, pair: str):
            return 0.5  # Mock price


class RouteOptimizerAgent(Agent if HAS_SDK else object):
    """AI agent for optimizing cross-DEX route splits"""
    
    def __init__(self, liquidity_monitor=None, mcp_client: Optional[MCPClient] = None):
        if HAS_SDK:
            super().__init__(name="CrossDEXOptimizer")
        else:
            self.name = "CrossDEXOptimizer"
            self.tools = []
        
        self.liquidity_monitor = liquidity_monitor
        self.mcp_client = mcp_client or MCPClient()
        self.model = self._load_or_train_model()
        
        # Register tools
        self.register_tool(Tool(
            name="analyze_liquidity",
            func=self.analyze_liquidity,
            description="Analyze liquidity across DEXs for token pair"
        ))
        
        self.register_tool(Tool(
            name="predict_slippage",
            func=self.predict_slippage,
            description="Predict slippage for given trade size and route"
        ))
    
    def register_tool(self, tool):
        """Register a tool"""
        if hasattr(self, 'tools'):
            self.tools.append(tool)
    
    def _load_or_train_model(self):
        """Load trained model or create new one"""
        model_path = Path("models/slippage_predictor.pkl")
        try:
            if model_path.exists():
                model = joblib.load(model_path)
            else:
                raise FileNotFoundError()
        except:
            # Create untrained model (will use default predictions)
            model = GradientBoostingRegressor(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=5,
                random_state=42
            )
            # Initialize with dummy data so predict works
            X_dummy = np.array([[1000, 1000000, 0.02, 12]])
            y_dummy = np.array([0.001])
            model.fit(X_dummy, y_dummy)
        
        return model
    
    async def analyze_liquidity(self, token_in: str, token_out: str) -> Dict:
        """Analyze liquidity across DEXs for token pair"""
        # Get real-time data from Crypto.com MCP
        market_info = await self.mcp_client.get_market_summary(f"{token_in}-{token_out}")
        liquidity_data = await self.mcp_client.get_liquidity_data(f"{token_in}-{token_out}")
        volatility_data = await self.mcp_client.get_historical_volatility(f"{token_in}-{token_out}")
        
        # Get on-chain liquidity
        pools = []
        if self.liquidity_monitor:
            try:
                pools = await self.liquidity_monitor.get_all_pools_for_pair(token_in, token_out)
            except:
                pass
        
        if not pools:
            # Return mock data structure
            return {
                "total_liquidity_usd": 1000000,
                "best_price": 0.5,
                "worst_price": 0.48,
                "recommended_dexes": ["VVS Finance", "CronaSwap"],
                "volatility": market_info.get("24h_volatility", 0.02),
                "pools": []
            }
        
        # Combine MCP data with on-chain pool data
        mcp_volatility = volatility_data.get("volatility", market_info.get("24h_volatility", 0.02))
        mcp_liquidity = liquidity_data.get("total_liquidity_usd", 0)
        
        analysis = {
            "total_liquidity_usd": max(
                sum(float(p.get('reserveUSD', 0)) for p in pools),
                mcp_liquidity
            ),
            "best_price": min((float(p.get('price', 0.5)) for p in pools if p.get('price')), default=market_info.get("current_price", 0.5)),
            "worst_price": max((float(p.get('price', 0.5)) for p in pools if p.get('price')), default=market_info.get("current_price", 0.5)),
            "recommended_dexes": self._rank_dexes(pools),
            "volatility": mcp_volatility,
            "spread_bps": liquidity_data.get("spread_bps", 5.0),
            "pools": pools,
            "mcp_data": {
                "price": market_info.get("current_price"),
                "volume_24h": market_info.get("24h_volume", 0),
                "liquidity_usd": mcp_liquidity
            }
        }
        
        return analysis
    
    def _rank_dexes(self, pools: List[Dict]) -> List[str]:
        """Rank DEXs by liquidity and quality"""
        dex_scores = {}
        for pool in pools:
            dex = pool.get('dex', 'Unknown')
            if dex not in dex_scores:
                dex_scores[dex] = 0
            dex_scores[dex] += float(pool.get('reserveUSD', 0))
        
        return sorted(dex_scores.keys(), key=lambda x: dex_scores[x], reverse=True)
    
    async def predict_slippage(self, trade_size: float, pool_liquidity: float, volatility: float) -> float:
        """Predict slippage for given parameters"""
        try:
            # Use model to predict
            prediction = self.model.predict([[trade_size, pool_liquidity, volatility, 12]])[0]
            return max(0.0, min(1.0, float(prediction)))  # Clamp between 0 and 1
        except:
            # Fallback calculation
            impact = trade_size / max(pool_liquidity, 1)
            return min(0.1, impact * volatility * 10)
    
    async def optimize_split(
        self,
        token_in: str,
        token_out: str,
        amount_in: float,
        max_slippage: float = 0.005
    ) -> Dict:
        """Main optimization function"""
        # Step 1: Get current market state
        liquidity_analysis = await self.analyze_liquidity(token_in, token_out)
        
        # Get current price from MCP
        current_price = await self.mcp_client.get_current_price(f"{token_in}-{token_out}")
        if current_price == 0:
            current_price = 0.5  # Fallback mock price
        
        pools = liquidity_analysis.get("pools", [])
        
        # Step 2: Generate candidate splits
        candidate_splits = self._generate_candidate_splits(pools, amount_in)
        
        # Step 3: Predict outcomes for each candidate
        predictions = []
        volatility = liquidity_analysis.get("volatility", 0.02)
        
        for split in candidate_splits:
            total_liquidity = sum(float(p.get('reserveUSD', 100000)) for p in pools)
            num_routes = len(split.get('splits', []))
            
            try:
                predicted_slippage = self.model.predict([[
                    amount_in,
                    total_liquidity,
                    volatility,
                    12  # time_of_day
                ]])[0]
            except:
                # Fallback calculation
                predicted_slippage = min(0.01, (amount_in / max(total_liquidity, 1)) * volatility * 5)
            
            if predicted_slippage <= max_slippage:
                split['predicted_slippage'] = float(predicted_slippage)
                split['predicted_output'] = amount_in * current_price * (1 - predicted_slippage)
                split['total_liquidity'] = total_liquidity
                split['num_routes'] = num_routes
                predictions.append(split)
        
        # Step 4: Select best split
        if not predictions:
            # Fallback to first strategy
            best_split = candidate_splits[0] if candidate_splits else {"strategy": "fallback", "splits": []}
        else:
            best_split = max(predictions, key=lambda x: x.get('predicted_output', 0))
        
        # Step 5: Format for x402 execution
        x402_operations = self._format_for_x402(best_split)
        
        return {
            "optimized_split": best_split,
            "x402_operations": x402_operations,
            "predicted_improvement": self._calculate_improvement(best_split, amount_in, current_price),
            "risk_metrics": self._calculate_risk_metrics(best_split)
        }
    
    def _generate_candidate_splits(self, pools: List[Dict], amount_in: float) -> List[Dict]:
        """Generate various split strategies"""
        strategies = []
        
        if not pools:
            # Mock pools for fallback
            pools = [
                {"dex": "VVS Finance", "reserveUSD": 1000000, "address": "0xVVS", "price": 0.5},
                {"dex": "CronaSwap", "reserveUSD": 600000, "address": "0xCRONA", "price": 0.49},
                {"dex": "MM Finance", "reserveUSD": 350000, "address": "0xMM", "price": 0.48},
            ]
        
        # Strategy 1: Proportional to liquidity
        total_liquidity = sum(float(p.get('reserveUSD', 0)) for p in pools)
        if total_liquidity > 0:
            proportional_split = []
            for pool in pools:
                share = float(pool.get('reserveUSD', 0)) / total_liquidity
                proportional_split.append({
                    'dex': pool.get('dex', 'Unknown'),
                    'pool': pool.get('address', pool.get('id', '0x')),
                    'amount': amount_in * share,
                    'share': share
                })
            
            strategies.append({
                'strategy': 'proportional',
                'splits': proportional_split
            })
        
        # Strategy 2: Concentrated in best price
        pools_with_price = [p for p in pools if p.get('price')]
        if pools_with_price:
            best_pool = max(pools_with_price, key=lambda x: float(x.get('price', 0)))
            strategies.append({
                'strategy': 'concentrated',
                'splits': [{
                    'dex': best_pool.get('dex', 'Unknown'),
                    'pool': best_pool.get('address', best_pool.get('id', '0x')),
                    'amount': amount_in,
                    'share': 1.0
                }]
            })
        
        # Strategy 3: AI optimized (simple equal split for now)
        if len(pools) > 1:
            equal_split = []
            share = 1.0 / len(pools)
            for pool in pools[:3]:  # Limit to top 3
                equal_split.append({
                    'dex': pool.get('dex', 'Unknown'),
                    'pool': pool.get('address', pool.get('id', '0x')),
                    'amount': amount_in * share,
                    'share': share
                })
            strategies.append({
                'strategy': 'equal_split',
                'splits': equal_split
            })
        
        return strategies if strategies else [{"strategy": "fallback", "splits": []}]
    
    def _format_for_x402(self, split: Dict) -> Dict:
        """Format split for x402 execution"""
        return {
            "targets": [s.get('pool') for s in split.get('splits', [])],
            "amounts": [s.get('amount') for s in split.get('splits', [])],
            "strategy": split.get('strategy', 'unknown')
        }
    
    def _calculate_improvement(self, split: Dict, amount_in: float, price: float) -> float:
        """Calculate predicted improvement vs single route"""
        # Simplified: assume 5% improvement for multi-route
        return 0.05 if len(split.get('splits', [])) > 1 else 0.0
    
    def _calculate_risk_metrics(self, split: Dict) -> Dict:
        """Calculate risk metrics for the split"""
        return {
            "diversification_score": len(split.get('splits', [])),
            "max_single_route_share": max((s.get('share', 0) for s in split.get('splits', [])), default=0),
            "route_count": len(split.get('splits', []))
        }
