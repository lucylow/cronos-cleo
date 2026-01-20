"""
Comprehensive Financial Metrics for AI Decision Making
Tracks extensive financial data including market metrics, returns, risk indicators, and economic factors
"""
import asyncio
import logging
import statistics
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal
from dataclasses import dataclass, field
from collections import defaultdict, deque
import json

logger = logging.getLogger(__name__)


@dataclass
class MarketData:
    """Market data for a token pair"""
    pair: str
    current_price: Decimal
    price_change_24h: Decimal
    price_change_7d: Decimal
    volatility_24h: Decimal
    volatility_7d: Decimal
    volume_24h: Decimal
    volume_7d: Decimal
    high_24h: Decimal
    low_24h: Decimal
    market_cap: Optional[Decimal] = None
    liquidity_usd: Decimal = Decimal('0')
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class DEXFinancials:
    """Financial metrics for a specific DEX"""
    dex_name: str
    total_volume_24h: Decimal
    total_volume_7d: Decimal
    total_volume_30d: Decimal
    total_fees_24h: Decimal
    total_fees_7d: Decimal
    avg_fee_rate_bps: Decimal
    protocol_revenue_24h: Decimal
    active_pools: int
    tvl_usd: Decimal
    liquidity_concentration: Decimal  # Herfindahl index
    price_impact_score: Decimal
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ExecutionFinancials:
    """Detailed financial data for an execution"""
    execution_id: str
    timestamp: datetime
    token_in: str
    token_out: str
    amount_in_usd: Decimal
    amount_out_usd: Decimal
    gas_cost_usd: Decimal
    protocol_fee_usd: Decimal
    net_profit_usd: Decimal
    savings_vs_single_dex_usd: Decimal
    savings_pct: Decimal
    roi_pct: Decimal
    sharpe_ratio: Optional[Decimal] = None
    max_drawdown: Optional[Decimal] = None
    dex_distribution: Dict[str, Decimal] = field(default_factory=dict)
    market_conditions: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RiskMetrics:
    """Risk-related financial metrics"""
    var_95_1d: Decimal  # Value at Risk 95% 1-day
    var_99_1d: Decimal  # Value at Risk 99% 1-day
    cvar_95_1d: Decimal  # Conditional VaR
    max_drawdown: Decimal
    sharpe_ratio: Decimal
    sortino_ratio: Decimal
    calmar_ratio: Decimal
    win_rate: Decimal
    profit_factor: Decimal  # Gross profit / Gross loss
    average_win: Decimal
    average_loss: Decimal
    largest_win: Decimal
    largest_loss: Decimal


@dataclass
class EconomicIndicators:
    """Economic indicators affecting trading"""
    gas_price_gwei: Decimal
    gas_price_avg_24h: Decimal
    network_congestion: Decimal  # 0-1
    total_value_locked_usd: Decimal
    defi_apy_avg: Decimal
    staking_yield: Decimal
    borrowing_rate: Decimal
    correlation_crypto_index: Decimal  # Correlation with crypto market
    market_regime: str  # 'bull', 'bear', 'sideways', 'volatile'
    timestamp: datetime = field(default_factory=datetime.now)


class FinancialMetricsCollector:
    """Collects and calculates comprehensive financial metrics for AI use"""
    
    def __init__(self):
        self.executions: deque = deque(maxlen=10000)  # Keep last 10k executions
        self.market_data: Dict[str, MarketData] = {}
        self.dex_financials: Dict[str, DEXFinancials] = {}
        self.economic_indicators: EconomicIndicators = None
        self.price_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.returns_history: deque = deque(maxlen=1000)
        
        # Aggregate metrics
        self.total_profit_usd = Decimal('0')
        self.total_costs_usd = Decimal('0')
        self.total_revenue_usd = Decimal('0')
        self.total_volume_usd = Decimal('0')
        self.total_executions = 0
        self.successful_executions = 0
        self.failed_executions = 0
        
        # Time-based aggregations
        self.daily_metrics: Dict[str, Dict] = defaultdict(dict)
        self.hourly_metrics: Dict[str, Dict] = defaultdict(dict)
    
    def add_execution(self, execution: ExecutionFinancials):
        """Add a new execution and update metrics"""
        self.executions.append(execution)
        self.total_executions += 1
        
        if execution.net_profit_usd >= 0:
            self.successful_executions += 1
        else:
            self.failed_executions += 1
        
        self.total_volume_usd += execution.amount_in_usd
        self.total_profit_usd += execution.net_profit_usd
        self.total_costs_usd += execution.gas_cost_usd + execution.protocol_fee_usd
        self.total_revenue_usd += execution.net_profit_usd + execution.gas_cost_usd + execution.protocol_fee_usd
        
        # Update returns history for risk metrics
        if execution.roi_pct:
            self.returns_history.append(float(execution.roi_pct))
        
        # Update time-based aggregations
        day_key = execution.timestamp.strftime("%Y-%m-%d")
        hour_key = execution.timestamp.strftime("%Y-%m-%d-%H")
        
        if day_key not in self.daily_metrics:
            self.daily_metrics[day_key] = {
                'volume': Decimal('0'),
                'profit': Decimal('0'),
                'costs': Decimal('0'),
                'executions': 0,
                'successful': 0
            }
        
        self.daily_metrics[day_key]['volume'] += execution.amount_in_usd
        self.daily_metrics[day_key]['profit'] += execution.net_profit_usd
        self.daily_metrics[day_key]['costs'] += execution.gas_cost_usd + execution.protocol_fee_usd
        self.daily_metrics[day_key]['executions'] += 1
        if execution.net_profit_usd >= 0:
            self.daily_metrics[day_key]['successful'] += 1
    
    def update_market_data(self, pair: str, market_data: MarketData):
        """Update market data for a token pair"""
        self.market_data[pair] = market_data
        # Update price history
        self.price_history[pair].append({
            'timestamp': market_data.timestamp,
            'price': market_data.current_price
        })
    
    def update_dex_financials(self, dex_name: str, dex_data: DEXFinancials):
        """Update financial metrics for a DEX"""
        self.dex_financials[dex_name] = dex_data
    
    def update_economic_indicators(self, indicators: EconomicIndicators):
        """Update economic indicators"""
        self.economic_indicators = indicators
    
    def calculate_risk_metrics(self, lookback_days: int = 30) -> RiskMetrics:
        """Calculate comprehensive risk metrics"""
        cutoff_date = datetime.now() - timedelta(days=lookback_days)
        recent_returns = [
            float(e.roi_pct) for e in self.executions
            if e.timestamp >= cutoff_date and e.roi_pct is not None
        ]
        
        if len(recent_returns) < 10:
            # Return default metrics if insufficient data
            return RiskMetrics(
                var_95_1d=Decimal('0.05'),
                var_99_1d=Decimal('0.10'),
                cvar_95_1d=Decimal('0.08'),
                max_drawdown=Decimal('0.15'),
                sharpe_ratio=Decimal('1.5'),
                sortino_ratio=Decimal('2.0'),
                calmar_ratio=Decimal('2.5'),
                win_rate=Decimal('0.65'),
                profit_factor=Decimal('1.8'),
                average_win=Decimal('0.02'),
                average_loss=Decimal('-0.01'),
                largest_win=Decimal('0.15'),
                largest_loss=Decimal('-0.08')
            )
        
        # Calculate VaR (assuming normal distribution for simplicity)
        returns_mean = statistics.mean(recent_returns)
        returns_std = statistics.stdev(recent_returns) if len(recent_returns) > 1 else 0.01
        
        # VaR at 95% and 99% confidence
        var_95 = Decimal(str(returns_mean - 1.645 * returns_std))
        var_99 = Decimal(str(returns_mean - 2.326 * returns_std))
        
        # CVaR (expected shortfall) - average of worst 5% returns
        sorted_returns = sorted(recent_returns)
        worst_5pct = sorted_returns[:max(1, len(sorted_returns) // 20)]
        cvar_95 = Decimal(str(statistics.mean(worst_5pct) if worst_5pct else var_95))
        
        # Max drawdown
        cumulative = []
        cumsum = 0
        for r in recent_returns:
            cumsum += r
            cumulative.append(cumsum)
        
        peak = cumulative[0]
        max_dd = Decimal('0')
        for value in cumulative:
            if value > peak:
                peak = value
            dd = (peak - value) / abs(peak) if peak != 0 else Decimal('0')
            if dd > max_dd:
                max_dd = dd
        
        # Sharpe ratio (annualized, assuming risk-free rate = 0)
        sharpe = Decimal(str(returns_mean / returns_std * math.sqrt(252))) if returns_std > 0 else Decimal('0')
        
        # Sortino ratio (using downside deviation)
        negative_returns = [r for r in recent_returns if r < 0]
        downside_std = statistics.stdev(negative_returns) if len(negative_returns) > 1 else 0.01
        sortino = Decimal(str(returns_mean / downside_std * math.sqrt(252))) if downside_std > 0 else Decimal('0')
        
        # Calmar ratio (annualized return / max drawdown)
        annual_return = Decimal(str(returns_mean * 252))
        calmar = annual_return / max_dd if max_dd > 0 else Decimal('100')
        
        # Win rate and profit factor
        wins = [r for r in recent_returns if r > 0]
        losses = [r for r in recent_returns if r < 0]
        win_rate = Decimal(str(len(wins) / len(recent_returns))) if recent_returns else Decimal('0')
        
        gross_profit = sum(wins) if wins else 0
        gross_loss = abs(sum(losses)) if losses else 1
        profit_factor = Decimal(str(gross_profit / gross_loss)) if gross_loss > 0 else Decimal('0')
        
        avg_win = Decimal(str(statistics.mean(wins))) if wins else Decimal('0')
        avg_loss = Decimal(str(statistics.mean(losses))) if losses else Decimal('0')
        largest_win = Decimal(str(max(wins))) if wins else Decimal('0')
        largest_loss = Decimal(str(min(losses))) if losses else Decimal('0')
        
        return RiskMetrics(
            var_95_1d=var_95,
            var_99_1d=var_99,
            cvar_95_1d=cvar_95,
            max_drawdown=max_dd,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            win_rate=win_rate,
            profit_factor=profit_factor,
            average_win=avg_win,
            average_loss=avg_loss,
            largest_win=largest_win,
            largest_loss=largest_loss
        )
    
    def get_financial_summary(self) -> Dict[str, Any]:
        """Get comprehensive financial summary for AI use"""
        risk_metrics = self.calculate_risk_metrics()
        
        # Calculate returns distribution
        recent_returns = [float(e.roi_pct) for e in list(self.executions)[-100:] if e.roi_pct is not None]
        returns_distribution = {
            'mean': float(statistics.mean(recent_returns)) if recent_returns else 0,
            'median': float(statistics.median(recent_returns)) if recent_returns else 0,
            'std': float(statistics.stdev(recent_returns)) if len(recent_returns) > 1 else 0,
            'min': float(min(recent_returns)) if recent_returns else 0,
            'max': float(max(recent_returns)) if recent_returns else 0,
            'percentile_25': float(sorted(recent_returns)[len(recent_returns)//4]) if recent_returns else 0,
            'percentile_75': float(sorted(recent_returns)[3*len(recent_returns)//4]) if recent_returns else 0,
        }
        
        # Calculate ROI
        roi = (self.total_profit_usd / self.total_volume_usd * 100) if self.total_volume_usd > 0 else Decimal('0')
        
        # Success rate
        success_rate = (self.successful_executions / self.total_executions * 100) if self.total_executions > 0 else Decimal('0')
        
        # Average metrics
        avg_profit_per_execution = (self.total_profit_usd / self.total_executions) if self.total_executions > 0 else Decimal('0')
        avg_cost_per_execution = (self.total_costs_usd / self.total_executions) if self.total_executions > 0 else Decimal('0')
        avg_volume_per_execution = (self.total_volume_usd / self.total_executions) if self.total_executions > 0 else Decimal('0')
        
        # Daily trends (last 7 days)
        last_7_days = []
        for i in range(7):
            day = datetime.now() - timedelta(days=i)
            day_key = day.strftime("%Y-%m-%d")
            if day_key in self.daily_metrics:
                last_7_days.append({
                    'date': day_key,
                    'volume': float(self.daily_metrics[day_key]['volume']),
                    'profit': float(self.daily_metrics[day_key]['profit']),
                    'costs': float(self.daily_metrics[day_key]['costs']),
                    'executions': self.daily_metrics[day_key]['executions'],
                    'success_rate': float(self.daily_metrics[day_key]['successful'] / self.daily_metrics[day_key]['executions'] * 100) if self.daily_metrics[day_key]['executions'] > 0 else 0
                })
        
        return {
            # Core metrics
            'total_profit_usd': float(self.total_profit_usd),
            'total_costs_usd': float(self.total_costs_usd),
            'total_revenue_usd': float(self.total_revenue_usd),
            'total_volume_usd': float(self.total_volume_usd),
            'total_gas_costs_usd': float(sum(e.gas_cost_usd for e in self.executions)),
            'total_protocol_fees_usd': float(sum(e.protocol_fee_usd for e in self.executions)),
            'total_executions': self.total_executions,
            'successful_executions': self.successful_executions,
            'failed_executions': self.failed_executions,
            'success_rate': float(success_rate),
            
            # ROI and returns
            'roi_pct': float(roi),
            'avg_profit_per_execution': float(avg_profit_per_execution),
            'avg_cost_per_execution': float(avg_cost_per_execution),
            'avg_volume_per_execution': float(avg_volume_per_execution),
            'returns_distribution': returns_distribution,
            
            # Risk metrics
            'risk_metrics': {
                'var_95_1d': float(risk_metrics.var_95_1d),
                'var_99_1d': float(risk_metrics.var_99_1d),
                'cvar_95_1d': float(risk_metrics.cvar_95_1d),
                'max_drawdown': float(risk_metrics.max_drawdown),
                'sharpe_ratio': float(risk_metrics.sharpe_ratio),
                'sortino_ratio': float(risk_metrics.sortino_ratio),
                'calmar_ratio': float(risk_metrics.calmar_ratio),
                'win_rate': float(risk_metrics.win_rate),
                'profit_factor': float(risk_metrics.profit_factor),
                'average_win': float(risk_metrics.average_win),
                'average_loss': float(risk_metrics.average_loss),
            },
            
            # Market data
            'market_data': {
                pair: {
                    'current_price': float(md.current_price),
                    'price_change_24h': float(md.price_change_24h),
                    'price_change_7d': float(md.price_change_7d),
                    'volatility_24h': float(md.volatility_24h),
                    'volatility_7d': float(md.volatility_7d),
                    'volume_24h': float(md.volume_24h),
                    'liquidity_usd': float(md.liquidity_usd),
                }
                for pair, md in self.market_data.items()
            },
            
            # DEX financials
            'dex_financials': {
                dex: {
                    'total_volume_24h': float(df.total_volume_24h),
                    'total_volume_7d': float(df.total_volume_7d),
                    'total_fees_24h': float(df.total_fees_24h),
                    'avg_fee_rate_bps': float(df.avg_fee_rate_bps),
                    'protocol_revenue_24h': float(df.protocol_revenue_24h),
                    'tvl_usd': float(df.tvl_usd),
                    'price_impact_score': float(df.price_impact_score),
                }
                for dex, df in self.dex_financials.items()
            },
            
            # Economic indicators
            'economic_indicators': {
                'gas_price_gwei': float(self.economic_indicators.gas_price_gwei) if self.economic_indicators else 10.0,
                'gas_price_avg_24h': float(self.economic_indicators.gas_price_avg_24h) if self.economic_indicators else 10.0,
                'network_congestion': float(self.economic_indicators.network_congestion) if self.economic_indicators else 0.3,
                'total_value_locked_usd': float(self.economic_indicators.total_value_locked_usd) if self.economic_indicators else 0,
                'market_regime': self.economic_indicators.market_regime if self.economic_indicators else 'neutral',
            } if self.economic_indicators else {},
            
            # Trends
            'daily_trends': last_7_days,
            
            # Timestamp
            'last_updated': datetime.now().isoformat()
        }
    
    def get_executions_for_ai(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent executions formatted for AI analysis"""
        recent = list(self.executions)[-limit:]
        return [
            {
                'execution_id': e.execution_id,
                'timestamp': e.timestamp.isoformat(),
                'token_pair': f"{e.token_in}/{e.token_out}",
                'amount_in_usd': float(e.amount_in_usd),
                'amount_out_usd': float(e.amount_out_usd),
                'net_profit_usd': float(e.net_profit_usd),
                'roi_pct': float(e.roi_pct),
                'savings_pct': float(e.savings_pct),
                'gas_cost_usd': float(e.gas_cost_usd),
                'protocol_fee_usd': float(e.protocol_fee_usd),
                'dex_distribution': {k: float(v) for k, v in e.dex_distribution.items()},
                'market_conditions': e.market_conditions,
            }
            for e in recent
        ]


# Global instance
financial_metrics_collector = FinancialMetricsCollector()

