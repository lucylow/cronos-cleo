"""
Multi-DEX Analytics Service
Tracks and analyzes routing performance across multiple DEXs
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from decimal import Decimal
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class SwapExecution:
    """Record of a swap execution"""
    swap_id: str
    timestamp: datetime
    user: str
    token_in: str
    token_out: str
    amount_in: Decimal
    amount_out: Decimal
    expected_out: Decimal
    actual_slippage: Decimal
    gas_used: Decimal
    gas_price: Decimal
    routes: List[str]  # DEX names used
    success: bool
    tx_hash: Optional[str] = None


@dataclass
class DEXMetrics:
    """Metrics for a specific DEX"""
    dex_id: str
    total_swaps: int = 0
    total_volume: Decimal = Decimal('0')
    total_successful: int = 0
    total_failed: int = 0
    total_gas_used: Decimal = Decimal('0')
    avg_slippage: Decimal = Decimal('0')
    avg_price_impact: Decimal = Decimal('0')
    best_execution: Optional[SwapExecution] = None
    worst_execution: Optional[SwapExecution] = None


@dataclass
class RouteAnalytics:
    """Analytics for routing"""
    route_id: str
    timestamp: datetime
    token_pair: str  # "TOKEN_IN/TOKEN_OUT"
    amount_in: Decimal
    expected_output: Decimal
    actual_output: Optional[Decimal] = None
    estimated_slippage: Decimal = Decimal('0')
    actual_slippage: Optional[Decimal] = None
    confidence_score: float = 0.0
    routes_used: List[str] = field(default_factory=list)
    execution_time_ms: Optional[float] = None
    success: bool = False


class MultiDEXAnalytics:
    """
    Analytics service for multi-DEX routing
    Tracks performance, slippage, gas costs, and route efficiency
    """
    
    def __init__(self):
        self.executions: Dict[str, SwapExecution] = {}
        self.route_analytics: Dict[str, RouteAnalytics] = {}
        self.dex_metrics: Dict[str, DEXMetrics] = {}
        
        # Time-based aggregations
        self._daily_volume: Dict[str, Decimal] = defaultdict(lambda: Decimal('0'))
        self._daily_swaps: Dict[str, int] = defaultdict(int)
        
        # Performance tracking
        self.total_swaps = 0
        self.total_volume = Decimal('0')
        self.total_gas_used = Decimal('0')
        self.total_successful = 0
        self.total_failed = 0
    
    def record_execution(self, execution: SwapExecution):
        """Record a swap execution"""
        self.executions[execution.swap_id] = execution
        
        # Update totals
        self.total_swaps += 1
        self.total_volume += execution.amount_in
        self.total_gas_used += execution.gas_used * execution.gas_price
        
        if execution.success:
            self.total_successful += 1
        else:
            self.total_failed += 1
        
        # Update daily aggregates
        day_key = execution.timestamp.strftime("%Y-%m-%d")
        self._daily_volume[day_key] += execution.amount_in
        self._daily_swaps[day_key] += 1
        
        # Update DEX metrics
        for dex_name in execution.routes:
            if dex_name not in self.dex_metrics:
                self.dex_metrics[dex_name] = DEXMetrics(dex_id=dex_name)
            
            metrics = self.dex_metrics[dex_name]
            metrics.total_swaps += 1
            metrics.total_volume += execution.amount_in
            metrics.total_gas_used += execution.gas_used * execution.gas_price
            
            if execution.success:
                metrics.total_successful += 1
            else:
                metrics.total_failed += 1
            
            # Update average slippage
            if metrics.total_successful > 0:
                total_slippage = metrics.avg_slippage * Decimal(metrics.total_successful - 1)
                metrics.avg_slippage = (total_slippage + execution.actual_slippage) / Decimal(metrics.total_successful)
            
            # Track best/worst execution
            if metrics.best_execution is None or execution.actual_slippage < metrics.best_execution.actual_slippage:
                metrics.best_execution = execution
            
            if metrics.worst_execution is None or execution.actual_slippage > metrics.worst_execution.actual_slippage:
                metrics.worst_execution = execution
        
        logger.info(f"Recorded execution: {execution.swap_id} - {execution.token_in}->{execution.token_out}, "
                   f"Amount: {execution.amount_in}, Slippage: {execution.actual_slippage * 100:.2f}%")
    
    def record_route_analysis(self, analytics: RouteAnalytics):
        """Record route analysis"""
        self.route_analytics[analytics.route_id] = analytics
    
    def update_route_execution(
        self,
        route_id: str,
        actual_output: Decimal,
        actual_slippage: Decimal,
        execution_time_ms: float,
        success: bool,
        tx_hash: Optional[str] = None
    ):
        """Update route analytics with execution results"""
        if route_id in self.route_analytics:
            analytics = self.route_analytics[route_id]
            analytics.actual_output = actual_output
            analytics.actual_slippage = actual_slippage
            analytics.execution_time_ms = execution_time_ms
            analytics.success = success
    
    def get_dex_metrics(self, dex_id: str) -> Optional[DEXMetrics]:
        """Get metrics for a specific DEX"""
        return self.dex_metrics.get(dex_id)
    
    def get_all_dex_metrics(self) -> Dict[str, DEXMetrics]:
        """Get metrics for all DEXs"""
        return self.dex_metrics.copy()
    
    def get_success_rate(self) -> float:
        """Get overall success rate"""
        if self.total_swaps == 0:
            return 0.0
        return (self.total_successful / self.total_swaps) * 100.0
    
    def get_average_slippage(self) -> Decimal:
        """Get average slippage across all successful swaps"""
        successful_executions = [
            e for e in self.executions.values()
            if e.success
        ]
        
        if not successful_executions:
            return Decimal('0')
        
        total_slippage = sum(e.actual_slippage for e in successful_executions)
        return total_slippage / Decimal(len(successful_executions))
    
    def get_average_gas_cost(self) -> Decimal:
        """Get average gas cost"""
        if self.total_swaps == 0:
            return Decimal('0')
        return self.total_gas_used / Decimal(self.total_swaps)
    
    def get_volume_last_24h(self) -> Decimal:
        """Get volume in last 24 hours"""
        cutoff = datetime.now() - timedelta(hours=24)
        volume = Decimal('0')
        
        for execution in self.executions.values():
            if execution.timestamp >= cutoff:
                volume += execution.amount_in
        
        return volume
    
    def get_swaps_last_24h(self) -> int:
        """Get number of swaps in last 24 hours"""
        cutoff = datetime.now() - timedelta(hours=24)
        count = 0
        
        for execution in self.executions.values():
            if execution.timestamp >= cutoff:
                count += 1
        
        return count
    
    def get_daily_statistics(self, days: int = 7) -> List[Dict]:
        """Get daily statistics for last N days"""
        stats = []
        today = datetime.now().date()
        
        for i in range(days):
            date = today - timedelta(days=i)
            day_key = date.strftime("%Y-%m-%d")
            
            volume = self._daily_volume.get(day_key, Decimal('0'))
            swaps = self._daily_swaps.get(day_key, 0)
            
            # Get successful swaps for this day
            successful = 0
            for execution in self.executions.values():
                if execution.timestamp.date() == date and execution.success:
                    successful += 1
            
            stats.append({
                "date": day_key,
                "volume": str(volume),
                "swaps": swaps,
                "successful": successful,
                "failed": swaps - successful,
                "success_rate": (successful / swaps * 100.0) if swaps > 0 else 0.0
            })
        
        return list(reversed(stats))  # Return oldest to newest
    
    def get_best_dex_for_pair(self, token_in: str, token_out: str) -> Optional[str]:
        """Get best performing DEX for a token pair"""
        pair_key = f"{token_in}/{token_out}"
        
        # Aggregate metrics by DEX for this pair
        dex_performance: Dict[str, List[Decimal]] = defaultdict(list)
        
        for execution in self.executions.values():
            if execution.token_in.lower() == token_in.lower() and \
               execution.token_out.lower() == token_out.lower() and \
               execution.success:
                for dex_name in execution.routes:
                    dex_performance[dex_name].append(execution.actual_slippage)
        
        if not dex_performance:
            return None
        
        # Find DEX with lowest average slippage
        best_dex = None
        best_avg_slippage = Decimal('1.0')  # 100% (worst case)
        
        for dex_name, slippages in dex_performance.items():
            avg_slippage = sum(slippages) / Decimal(len(slippages))
            if avg_slippage < best_avg_slippage:
                best_avg_slippage = avg_slippage
                best_dex = dex_name
        
        return best_dex
    
    def get_summary(self) -> Dict:
        """Get summary statistics"""
        return {
            "total_swaps": self.total_swaps,
            "total_volume": str(self.total_volume),
            "total_successful": self.total_successful,
            "total_failed": self.total_failed,
            "success_rate": self.get_success_rate(),
            "average_slippage": str(self.get_average_slippage()),
            "average_gas_cost": str(self.get_average_gas_cost()),
            "volume_24h": str(self.get_volume_last_24h()),
            "swaps_24h": self.get_swaps_last_24h(),
            "active_dexes": len(self.dex_metrics),
            "dex_metrics": {
                dex_id: {
                    "total_swaps": metrics.total_swaps,
                    "total_volume": str(metrics.total_volume),
                    "success_rate": (metrics.total_successful / metrics.total_swaps * 100.0) if metrics.total_swaps > 0 else 0.0,
                    "avg_slippage": str(metrics.avg_slippage),
                    "avg_gas": str(metrics.total_gas_used / Decimal(metrics.total_swaps)) if metrics.total_swaps > 0 else "0"
                }
                for dex_id, metrics in self.dex_metrics.items()
            }
        }
    
    def clear_old_data(self, days_to_keep: int = 30):
        """Clear data older than specified days"""
        cutoff = datetime.now() - timedelta(days=days_to_keep)
        
        to_remove = [
            swap_id for swap_id, execution in self.executions.items()
            if execution.timestamp < cutoff
        ]
        
        for swap_id in to_remove:
            del self.executions[swap_id]
        
        # Clear route analytics
        to_remove_routes = [
            route_id for route_id, analytics in self.route_analytics.items()
            if analytics.timestamp < cutoff
        ]
        
        for route_id in to_remove_routes:
            del self.route_analytics[route_id]
        
        logger.info(f"Cleared {len(to_remove)} old executions and {len(to_remove_routes)} route analytics")


# Global analytics instance
analytics_service = MultiDEXAnalytics()
