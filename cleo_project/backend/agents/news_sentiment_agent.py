"""
News/Sentiment Agent - Event-driven risk detection
Monitors news, sentiment, and events that could impact portfolio holdings
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal

from .base_agent import BaseAgent
from .message_bus import AgentMessage
from .portfolio_models import Portfolio, Position, RiskLevel
from .portfolio_storage import portfolio_storage

logger = logging.getLogger(__name__)


class NewsSentimentAgent(BaseAgent):
    """Agent responsible for monitoring news and sentiment for portfolio holdings"""
    
    def __init__(self, mcp_client=None):
        super().__init__("news_sentiment", "News/Sentiment Agent")
        self.mcp_client = mcp_client
        self.news_cache: Dict[str, List[Dict]] = {}  # token_address -> news items
        self.sentiment_scores: Dict[str, Dict] = {}  # token_address -> {score, timestamp}
        self.event_alerts: List[Dict] = []
    
    async def handle_message(self, message: AgentMessage):
        """Handle incoming messages"""
        if message.message_type == "analyze_portfolio_sentiment":
            await self._handle_analyze_sentiment(message)
        elif message.message_type == "check_event_risk":
            await self._handle_check_event_risk(message)
        elif message.message_type == "news_update":
            await self._handle_news_update(message)
    
    async def _handle_analyze_sentiment(self, message: AgentMessage):
        """Analyze sentiment for all holdings in a portfolio"""
        portfolio_id = message.payload.get("portfolio_id")
        if not portfolio_id:
            return
        
        portfolio = portfolio_storage.get_portfolio(portfolio_id)
        if not portfolio:
            return
        
        try:
            sentiment_analysis = await self.analyze_portfolio_sentiment(portfolio)
            
            response = AgentMessage(
                message_id=f"resp_{message.message_id}",
                sender=self.agent_id,
                receiver=message.sender,
                message_type="sentiment_analysis",
                payload={
                    "portfolio_id": portfolio_id,
                    "analysis": sentiment_analysis
                }
            )
            await self.send_message(response)
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}", exc_info=True)
    
    async def analyze_portfolio_sentiment(self, portfolio: Portfolio) -> Dict[str, Any]:
        """Analyze sentiment for all positions in portfolio"""
        analysis = {
            "portfolio_id": portfolio.portfolio_id,
            "timestamp": datetime.now().isoformat(),
            "overall_sentiment": "neutral",
            "overall_score": 0.0,
            "position_sentiments": [],
            "risk_alerts": []
        }
        
        position_scores = []
        
        for token_address, position in portfolio.positions.items():
            sentiment = await self.get_token_sentiment(token_address, position.token_symbol)
            position_scores.append(sentiment["score"])
            
            analysis["position_sentiments"].append({
                "token_address": token_address,
                "token_symbol": position.token_symbol,
                "sentiment_score": sentiment["score"],
                "sentiment_label": sentiment["label"],
                "recent_news_count": sentiment.get("news_count", 0),
                "risk_level": sentiment.get("risk_level", "low")
            })
            
            # Check for risk alerts
            if sentiment["score"] < -0.5:  # Very negative sentiment
                analysis["risk_alerts"].append({
                    "type": "negative_sentiment",
                    "token": position.token_symbol,
                    "token_address": token_address,
                    "score": sentiment["score"],
                    "severity": "high" if sentiment["score"] < -0.7 else "medium",
                    "recommendation": "Consider reducing exposure or hedging"
                })
        
        # Compute overall sentiment
        if position_scores:
            avg_score = sum(position_scores) / len(position_scores)
            analysis["overall_score"] = avg_score
            
            if avg_score > 0.3:
                analysis["overall_sentiment"] = "positive"
            elif avg_score < -0.3:
                analysis["overall_sentiment"] = "negative"
            else:
                analysis["overall_sentiment"] = "neutral"
        
        return analysis
    
    async def get_token_sentiment(self, token_address: str, token_symbol: str) -> Dict[str, Any]:
        """Get sentiment score for a token"""
        # Check cache first
        if token_address in self.sentiment_scores:
            cached = self.sentiment_scores[token_address]
            # Use cached if less than 1 hour old
            if (datetime.now() - cached["timestamp"]).seconds < 3600:
                return cached["sentiment"]
        
        # Fetch news and compute sentiment
        news_items = await self.fetch_token_news(token_address, token_symbol)
        sentiment = await self.compute_sentiment_from_news(news_items)
        
        # Cache result
        self.sentiment_scores[token_address] = {
            "sentiment": sentiment,
            "timestamp": datetime.now()
        }
        
        return sentiment
    
    async def fetch_token_news(self, token_address: str, token_symbol: str, limit: int = 20) -> List[Dict]:
        """Fetch recent news for a token"""
        # In production, integrate with news APIs, Twitter, Reddit, etc.
        # For now, use mock data or MCP client if available
        
        if token_address in self.news_cache:
            # Return cached news
            return self.news_cache[token_address][:limit]
        
        # Try to fetch from MCP client if available
        news_items = []
        if self.mcp_client:
            try:
                # This would call an MCP tool for news/sentiment
                # For now, return empty list
                pass
            except Exception as e:
                logger.debug(f"Could not fetch news from MCP: {e}")
        
        # Store in cache
        self.news_cache[token_address] = news_items
        
        return news_items
    
    async def compute_sentiment_from_news(self, news_items: List[Dict]) -> Dict[str, Any]:
        """Compute sentiment score from news items"""
        if not news_items:
            return {
                "score": 0.0,
                "label": "neutral",
                "news_count": 0,
                "risk_level": "low"
            }
        
        # Simplified sentiment scoring
        # In production, use NLP models (BERT, GPT, etc.)
        scores = []
        for item in news_items:
            # Mock sentiment score (-1 to 1)
            # In production, use actual sentiment analysis
            text = item.get("title", "") + " " + item.get("content", "")
            score = self._simple_sentiment_score(text)
            scores.append(score)
        
        avg_score = sum(scores) / len(scores) if scores else 0.0
        
        # Determine label
        if avg_score > 0.3:
            label = "positive"
        elif avg_score < -0.3:
            label = "negative"
        else:
            label = "neutral"
        
        # Determine risk level
        if avg_score < -0.7:
            risk_level = "critical"
        elif avg_score < -0.5:
            risk_level = "high"
        elif avg_score < -0.3:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        return {
            "score": avg_score,
            "label": label,
            "news_count": len(news_items),
            "risk_level": risk_level
        }
    
    def _simple_sentiment_score(self, text: str) -> float:
        """Simple keyword-based sentiment scoring (mock)"""
        # In production, use proper NLP models
        text_lower = text.lower()
        
        positive_words = ["bullish", "surge", "rally", "gain", "up", "positive", "growth", "adoption"]
        negative_words = ["bearish", "crash", "drop", "fall", "down", "negative", "risk", "hack", "exploit"]
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count == 0 and negative_count == 0:
            return 0.0
        
        score = (positive_count - negative_count) / max(positive_count + negative_count, 1)
        return max(-1.0, min(1.0, score))
    
    async def _handle_check_event_risk(self, message: AgentMessage):
        """Check for event-driven risks"""
        portfolio_id = message.payload.get("portfolio_id")
        if not portfolio_id:
            return
        
        portfolio = portfolio_storage.get_portfolio(portfolio_id)
        if not portfolio:
            return
        
        event_risks = await self.check_event_risks(portfolio)
        
        response = AgentMessage(
            message_id=f"resp_{message.message_id}",
            sender=self.agent_id,
            receiver=message.sender,
            message_type="event_risk_analysis",
            payload={
                "portfolio_id": portfolio_id,
                "event_risks": event_risks
            }
        )
        await self.send_message(response)
    
    async def check_event_risks(self, portfolio: Portfolio) -> List[Dict[str, Any]]:
        """Check for event-driven risks in portfolio"""
        risks = []
        
        for token_address, position in portfolio.positions.items():
            # Check for negative sentiment without price adjustment
            sentiment = await self.get_token_sentiment(token_address, position.token_symbol)
            
            if sentiment["score"] < -0.5:
                # Check if price has adjusted
                price_change = position.unrealized_pnl_pct
                
                # If sentiment is very negative but price hasn't dropped much, flag it
                if price_change > -0.05:  # Less than 5% drop
                    risks.append({
                        "type": "sentiment_price_divergence",
                        "token": position.token_symbol,
                        "token_address": token_address,
                        "sentiment_score": sentiment["score"],
                        "price_change_pct": float(price_change),
                        "severity": "high",
                        "recommendation": "Consider reducing exposure or hedging - negative sentiment not yet reflected in price"
                    })
            
            # Check for recent negative news
            news_items = await self.fetch_token_news(token_address, position.token_symbol, limit=5)
            recent_negative = [
                item for item in news_items
                if self._simple_sentiment_score(item.get("title", "") + " " + item.get("content", "")) < -0.5
            ]
            
            if len(recent_negative) >= 3:  # Multiple negative news items
                risks.append({
                    "type": "negative_news_cluster",
                    "token": position.token_symbol,
                    "token_address": token_address,
                    "negative_news_count": len(recent_negative),
                    "severity": "medium",
                    "recommendation": "Monitor closely - multiple negative news items"
                })
        
        return risks
    
    async def _handle_news_update(self, message: AgentMessage):
        """Handle incoming news update"""
        token_address = message.payload.get("token_address")
        news_item = message.payload.get("news_item")
        
        if not token_address or not news_item:
            return
        
        # Add to cache
        if token_address not in self.news_cache:
            self.news_cache[token_address] = []
        
        self.news_cache[token_address].insert(0, {
            **news_item,
            "timestamp": datetime.now()
        })
        
        # Keep only last 100 items per token
        if len(self.news_cache[token_address]) > 100:
            self.news_cache[token_address] = self.news_cache[token_address][:100]
        
        # Invalidate sentiment cache
        if token_address in self.sentiment_scores:
            del self.sentiment_scores[token_address]
        
        # Check if this news affects any portfolios
        await self._check_news_impact(token_address, news_item)
    
    async def _check_news_impact(self, token_address: str, news_item: Dict):
        """Check if news affects any portfolios and alert"""
        # Find all portfolios holding this token
        portfolios = portfolio_storage.list_portfolios()
        
        for portfolio in portfolios:
            if token_address in portfolio.positions:
                # Compute sentiment for this news
                sentiment_score = self._simple_sentiment_score(
                    news_item.get("title", "") + " " + news_item.get("content", "")
                )
                
                # If very negative, create alert
                if sentiment_score < -0.7:
                    self.event_alerts.append({
                        "portfolio_id": portfolio.portfolio_id,
                        "token_address": token_address,
                        "news_item": news_item,
                        "sentiment_score": sentiment_score,
                        "timestamp": datetime.now(),
                        "severity": "high"
                    })
                    
                    # Broadcast alert
                    await self.broadcast_event("news_risk_alert", {
                        "portfolio_id": portfolio.portfolio_id,
                        "token_address": token_address,
                        "sentiment_score": sentiment_score,
                        "severity": "high"
                    })

