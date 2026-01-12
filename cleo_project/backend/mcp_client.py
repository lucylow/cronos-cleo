"""
MCP (Model Context Protocol) Client for Crypto.com Market Data
Integrates with Crypto.com MCP Server for real-time market data
"""
import os
import aiohttp
from typing import Dict, List, Optional, Any
import json
from datetime import datetime


class MCPClient:
    """
    Client for Crypto.com Market Data MCP Server
    Provides real-time price feeds, volatility metrics, and liquidity data
    """
    
    def __init__(self, mcp_server_url: Optional[str] = None, api_key: Optional[str] = None):
        self.mcp_server_url = mcp_server_url or os.getenv(
            "CRYPTOCOM_MCP_URL",
            "https://mcp.crypto.com/api/v1"
        )
        self.api_key = api_key or os.getenv("CRYPTOCOM_MCP_KEY")
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            self.session = aiohttp.ClientSession(
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            )
        return self.session
    
    async def close(self):
        """Close the session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def get_market_summary(self, pair: str) -> Dict[str, Any]:
        """
        Get market summary for a trading pair
        
        Args:
            pair: Trading pair (e.g., "CRO/USDC", "CRO-USDC")
            
        Returns:
            Market summary with price, volume, volatility, etc.
        """
        # Normalize pair format
        pair_normalized = pair.replace("-", "/").upper()
        
        try:
            session = await self._get_session()
            url = f"{self.mcp_server_url}/market/summary"
            params = {"pair": pair_normalized}
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "pair": pair_normalized,
                        "current_price": float(data.get("price", 0)),
                        "24h_volume": float(data.get("volume_24h", 0)),
                        "24h_volatility": float(data.get("volatility_24h", 0.02)),
                        "24h_high": float(data.get("high_24h", 0)),
                        "24h_low": float(data.get("low_24h", 0)),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    # Return mock data if API unavailable
                    return self._get_mock_market_summary(pair_normalized)
        except Exception as e:
            print(f"MCP API error: {e}")
            return self._get_mock_market_summary(pair_normalized)
    
    async def get_current_price(self, pair: str) -> float:
        """
        Get current price for a trading pair
        
        Args:
            pair: Trading pair
            
        Returns:
            Current price
        """
        summary = await self.get_market_summary(pair)
        return summary.get("current_price", 0.0)
    
    async def get_liquidity_data(self, pair: str) -> Dict[str, Any]:
        """
        Get liquidity data for a trading pair
        
        Args:
            pair: Trading pair
            
        Returns:
            Liquidity metrics including depth, spread, etc.
        """
        pair_normalized = pair.replace("-", "/").upper()
        
        try:
            session = await self._get_session()
            url = f"{self.mcp_server_url}/liquidity"
            params = {"pair": pair_normalized}
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "pair": pair_normalized,
                        "total_liquidity_usd": float(data.get("total_liquidity_usd", 0)),
                        "bid_depth": float(data.get("bid_depth", 0)),
                        "ask_depth": float(data.get("ask_depth", 0)),
                        "spread_bps": float(data.get("spread_bps", 0)),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    return self._get_mock_liquidity_data(pair_normalized)
        except Exception as e:
            print(f"MCP liquidity API error: {e}")
            return self._get_mock_liquidity_data(pair_normalized)
    
    async def get_historical_volatility(
        self,
        pair: str,
        period: str = "24h"
    ) -> Dict[str, Any]:
        """
        Get historical volatility metrics
        
        Args:
            pair: Trading pair
            period: Time period (1h, 24h, 7d, 30d)
            
        Returns:
            Volatility metrics
        """
        pair_normalized = pair.replace("-", "/").upper()
        
        try:
            session = await self._get_session()
            url = f"{self.mcp_server_url}/volatility"
            params = {"pair": pair_normalized, "period": period}
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "pair": pair_normalized,
                        "period": period,
                        "volatility": float(data.get("volatility", 0.02)),
                        "realized_volatility": float(data.get("realized_vol", 0.02)),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    return {
                        "pair": pair_normalized,
                        "period": period,
                        "volatility": 0.02,  # Default 2%
                        "realized_volatility": 0.02
                    }
        except Exception as e:
            print(f"MCP volatility API error: {e}")
            return {
                "pair": pair_normalized,
                "period": period,
                "volatility": 0.02,
                "realized_volatility": 0.02
            }
    
    def _get_mock_market_summary(self, pair: str) -> Dict[str, Any]:
        """Return mock market data when API is unavailable"""
        # Mock prices for common pairs
        mock_prices = {
            "CRO/USDC": 0.12,
            "CRO/USDT": 0.12,
            "USDC/USDT": 1.0,
        }
        
        price = mock_prices.get(pair, 0.5)
        
        return {
            "pair": pair,
            "current_price": price,
            "24h_volume": 1000000.0,
            "24h_volatility": 0.02,
            "24h_high": price * 1.05,
            "24h_low": price * 0.95,
            "timestamp": datetime.utcnow().isoformat(),
            "mock": True
        }
    
    def _get_mock_liquidity_data(self, pair: str) -> Dict[str, Any]:
        """Return mock liquidity data when API is unavailable"""
        return {
            "pair": pair,
            "total_liquidity_usd": 2000000.0,
            "bid_depth": 500000.0,
            "ask_depth": 500000.0,
            "spread_bps": 5.0,  # 0.05%
            "timestamp": datetime.utcnow().isoformat(),
            "mock": True
        }
    
    async def get_orderbook_depth(
        self,
        pair: str,
        depth: int = 10
    ) -> Dict[str, Any]:
        """
        Get orderbook depth for price impact analysis
        
        Args:
            pair: Trading pair
            depth: Number of levels to retrieve
            
        Returns:
            Orderbook depth data
        """
        pair_normalized = pair.replace("-", "/").upper()
        
        try:
            session = await self._get_session()
            url = f"{self.mcp_server_url}/orderbook"
            params = {"pair": pair_normalized, "depth": depth}
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "pair": pair_normalized,
                        "bids": data.get("bids", []),
                        "asks": data.get("asks", []),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    return self._get_mock_orderbook(pair_normalized, depth)
        except Exception as e:
            print(f"MCP orderbook API error: {e}")
            return self._get_mock_orderbook(pair_normalized, depth)
    
    def _get_mock_orderbook(self, pair: str, depth: int) -> Dict[str, Any]:
        """Return mock orderbook data"""
        # Generate mock orderbook levels
        base_price = 0.12 if "CRO" in pair else 1.0
        
        bids = []
        asks = []
        
        for i in range(depth):
            bid_price = base_price * (1 - (i + 1) * 0.001)
            ask_price = base_price * (1 + (i + 1) * 0.001)
            
            bids.append({
                "price": bid_price,
                "amount": 10000.0 / (i + 1)
            })
            asks.append({
                "price": ask_price,
                "amount": 10000.0 / (i + 1)
            })
        
        return {
            "pair": pair,
            "bids": bids,
            "asks": asks,
            "timestamp": datetime.utcnow().isoformat(),
            "mock": True
        }

