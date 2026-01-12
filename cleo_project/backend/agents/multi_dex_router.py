"""
Multi-DEX Router Agent - Advanced routing engine for multi-DEX swaps
Provides DEX registry management, route optimization, and analytics
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal
from dataclasses import dataclass, field

from .base_agent import BaseAgent
from .message_bus import AgentMessage
from .models import DEXPool, RouteSplit, OptimizedRoute, Token

logger = logging.getLogger(__name__)


@dataclass
class DEXConfig:
    """DEX configuration"""
    dex_id: str
    name: str
    router_address: str
    factory_address: str
    fee_bps: int  # Fee in basis points (e.g., 30 for 0.3%)
    priority: int  # Lower = higher priority
    is_active: bool = True
    min_liquidity_usd: Decimal = Decimal('10000')
    subgraph_url: Optional[str] = None


@dataclass
class RouteMetrics:
    """Metrics for a route"""
    route_id: str
    expected_output: Decimal
    estimated_slippage: Decimal
    gas_estimate: Decimal
    confidence_score: float
    price_impact: Decimal
    liquidity_utilization: Decimal


class MultiDEXRouterAgent(BaseAgent):
    """
    Advanced multi-DEX routing agent with:
    - DEX registry management
    - Advanced route optimization algorithms
    - Real-time liquidity analysis
    - Analytics and monitoring
    """
    
    def __init__(self, cronos_rpc: str):
        super().__init__("multi_dex_router", "Multi-DEX Router")
        self.w3 = None
        self.cronos_rpc = cronos_rpc
        
        # DEX Registry - Cronos DEXs
        self.dex_registry: Dict[str, DEXConfig] = {
            "vvs": DEXConfig(
                dex_id="vvs",
                name="VVS Finance",
                router_address="0x145863Eb42Cf62847A6Ca784e6416C1682b1b2Ae",
                factory_address="0x3B44B2a187b7Fc6c3a90cF00fA6d5b6C31E35eD8",
                fee_bps=30,  # 0.3%
                priority=1,
                is_active=True,
                min_liquidity_usd=Decimal('10000'),
                subgraph_url="https://api.thegraph.com/subgraphs/name/vvs-finance/vvs-dex"
            ),
            "cronaswap": DEXConfig(
                dex_id="cronaswap",
                name="CronaSwap",
                router_address="0xcd7d16fB918511BF7269eC4f48d61D79Fb26f918",
                factory_address="0x73A48f8f521EB31c55c0e1274dB0898dE599Cb11",
                fee_bps=30,  # 0.3%
                priority=2,
                is_active=True,
                min_liquidity_usd=Decimal('5000'),
                subgraph_url="https://api.thegraph.com/subgraphs/name/cronaswap/exchange"
            ),
            "mm_finance": DEXConfig(
                dex_id="mm_finance",
                name="MM Finance",
                router_address="0x145677FC4d9b8F19B5D56d1820c48e0443049a30",
                factory_address="0xd590cC180601AEcD6eeADD9B7f2B7611519544f4",
                fee_bps=30,  # 0.3%
                priority=3,
                is_active=True,
                min_liquidity_usd=Decimal('5000'),
                subgraph_url=None
            )
        }
        
        # Analytics
        self.route_analytics: Dict[str, RouteMetrics] = {}
        self.total_routes_optimized = 0
        self.total_volume_routed = Decimal('0')
        
        # Cache
        self._liquidity_cache: Dict[str, List[DEXPool]] = {}
        self._cache_ttl = 60  # 60 seconds
        
    async def handle_message(self, message: AgentMessage):
        """Handle incoming messages"""
        if message.message_type == "optimize_multi_dex_route":
            await self._handle_optimize_route(message)
        elif message.message_type == "register_dex":
            await self._handle_register_dex(message)
        elif message.message_type == "get_dex_registry":
            await self._handle_get_registry(message)
        elif message.message_type == "get_route_analytics":
            await self._handle_get_analytics(message)
    
    async def _handle_optimize_route(self, message: AgentMessage):
        """Handle route optimization request"""
        payload = message.payload
        token_in = payload.get("token_in")
        token_out = payload.get("token_out")
        amount_in = Decimal(str(payload.get("amount_in", 0)))
        max_slippage = Decimal(str(payload.get("max_slippage", 0.05)))
        strategy = payload.get("strategy", "weighted_liquidity")
        
        try:
            # Request liquidity data
            liquidity_msg = AgentMessage(
                message_id=f"liquidity_req_{datetime.now().timestamp()}",
                sender=self.agent_id,
                receiver="liquidity_analyzer",
                message_type="get_liquidity",
                payload={
                    "token_in": token_in,
                    "token_out": token_out,
                    "request_id": message.message_id
                }
            )
            await self.send_message(liquidity_msg)
            
            # For now, use cached or simplified optimization
            # In production, wait for liquidity response
            pools = await self._get_pools_for_pair(token_in, token_out)
            optimized_route = await self._optimize_route(
                token_in=token_in,
                token_out=token_out,
                amount_in=amount_in,
                pools=pools,
                strategy=strategy,
                max_slippage=max_slippage
            )
            
            # Record analytics
            self.total_routes_optimized += 1
            self.total_volume_routed += amount_in
            
            # Send response
            response = AgentMessage(
                message_id=f"resp_{message.message_id}",
                sender=self.agent_id,
                receiver=message.sender,
                message_type="optimized_multi_dex_route",
                payload={
                    "route": optimized_route.dict() if hasattr(optimized_route, 'dict') else optimized_route,
                    "request_id": message.message_id
                }
            )
            await self.send_message(response)
            
        except Exception as e:
            logger.error(f"Error optimizing route: {e}", exc_info=True)
            error_response = AgentMessage(
                message_id=f"error_{message.message_id}",
                sender=self.agent_id,
                receiver=message.sender,
                message_type="route_optimization_error",
                payload={
                    "error": str(e),
                    "request_id": message.message_id
                }
            )
            await self.send_message(error_response)
    
    async def _handle_register_dex(self, message: AgentMessage):
        """Handle DEX registration"""
        payload = message.payload
        dex_config = DEXConfig(
            dex_id=payload["dex_id"],
            name=payload["name"],
            router_address=payload["router_address"],
            factory_address=payload.get("factory_address", ""),
            fee_bps=payload.get("fee_bps", 30),
            priority=payload.get("priority", 99),
            is_active=payload.get("is_active", True),
            min_liquidity_usd=Decimal(str(payload.get("min_liquidity_usd", 10000))),
            subgraph_url=payload.get("subgraph_url")
        )
        
        self.dex_registry[dex_config.dex_id] = dex_config
        logger.info(f"Registered DEX: {dex_config.dex_id} - {dex_config.name}")
    
    async def _handle_get_registry(self, message: AgentMessage):
        """Handle registry query"""
        registry_dict = {
            dex_id: {
                "dex_id": config.dex_id,
                "name": config.name,
                "router_address": config.router_address,
                "factory_address": config.factory_address,
                "fee_bps": config.fee_bps,
                "priority": config.priority,
                "is_active": config.is_active,
                "min_liquidity_usd": str(config.min_liquidity_usd)
            }
            for dex_id, config in self.dex_registry.items()
        }
        
        response = AgentMessage(
            message_id=f"resp_{message.message_id}",
            sender=self.agent_id,
            receiver=message.sender,
            message_type="dex_registry_response",
            payload={"registry": registry_dict}
        )
        await self.send_message(response)
    
    async def _handle_get_analytics(self, message: AgentMessage):
        """Handle analytics query"""
        analytics = {
            "total_routes_optimized": self.total_routes_optimized,
            "total_volume_routed": str(self.total_volume_routed),
            "active_dexes": len([d for d in self.dex_registry.values() if d.is_active]),
            "route_analytics": {
                route_id: {
                    "expected_output": str(metrics.expected_output),
                    "estimated_slippage": str(metrics.estimated_slippage),
                    "gas_estimate": str(metrics.gas_estimate),
                    "confidence_score": metrics.confidence_score,
                    "price_impact": str(metrics.price_impact)
                }
                for route_id, metrics in self.route_analytics.items()
            }
        }
        
        response = AgentMessage(
            message_id=f"resp_{message.message_id}",
            sender=self.agent_id,
            receiver=message.sender,
            message_type="route_analytics_response",
            payload={"analytics": analytics}
        )
        await self.send_message(response)
    
    async def _get_pools_for_pair(self, token_in: str, token_out: str) -> List[DEXPool]:
        """Get pools for a token pair across all DEXs"""
        # This would normally query liquidity_analyzer agent
        # For now, return empty list (would be populated by liquidity response)
        return []
    
    async def _optimize_route(
        self,
        token_in: str,
        token_out: str,
        amount_in: Decimal,
        pools: List[DEXPool],
        strategy: str,
        max_slippage: Decimal
    ) -> OptimizedRoute:
        """
        Optimize route using specified strategy
        
        Strategies:
        - weighted_liquidity: Split based on liquidity-weighted distribution
        - price_impact: Minimize price impact across pools
        - balanced: Equal distribution
        - greedy: Use best pool only
        """
        if not pools:
            # Fallback: create empty route
            return OptimizedRoute(
                route_id=f"route_{datetime.now().timestamp()}",
                token_in=Token(address=token_in, symbol="", decimals=18, name=""),
                token_out=Token(address=token_out, symbol="", decimals=18, name=""),
                total_amount_in=amount_in,
                total_expected_out=Decimal('0'),
                total_min_out=Decimal('0'),
                splits=[],
                predicted_slippage=max_slippage,
                expected_gas=Decimal('0.05'),
                confidence_score=0.0,
                risk_score=1.0
            )
        
        # Filter pools by active DEXs and min liquidity
        active_dexes = {dex_id for dex_id, config in self.dex_registry.items() if config.is_active}
        filtered_pools = [
            p for p in pools
            if p.dex_name.lower() in active_dexes and p.reserve_usd >= self.dex_registry[p.dex_name.lower()].min_liquidity_usd
        ]
        
        if not filtered_pools:
            filtered_pools = pools  # Fallback to all pools
        
        # Apply optimization strategy
        if strategy == "weighted_liquidity":
            splits = await self._optimize_weighted_liquidity(
                filtered_pools, amount_in, token_in, token_out, max_slippage
            )
        elif strategy == "price_impact":
            splits = await self._optimize_price_impact(
                filtered_pools, amount_in, token_in, token_out, max_slippage
            )
        elif strategy == "balanced":
            splits = await self._optimize_balanced(
                filtered_pools, amount_in, token_in, token_out, max_slippage
            )
        elif strategy == "greedy":
            splits = await self._optimize_greedy(
                filtered_pools, amount_in, token_in, token_out, max_slippage
            )
        else:
            # Default to weighted liquidity
            splits = await self._optimize_weighted_liquidity(
                filtered_pools, amount_in, token_in, token_out, max_slippage
            )
        
        # Calculate totals
        total_expected_out = sum(split.expected_amount_out for split in splits)
        total_min_out = sum(split.min_amount_out for split in splits)
        
        # Calculate metrics
        avg_slippage = max_slippage if splits else Decimal('0')
        confidence = 0.9 if len(splits) > 0 else 0.0
        
        route_id = f"route_{datetime.now().timestamp()}"
        
        # Store analytics
        self.route_analytics[route_id] = RouteMetrics(
            route_id=route_id,
            expected_output=total_expected_out,
            estimated_slippage=avg_slippage,
            gas_estimate=Decimal('0.05') * len(splits),
            confidence_score=confidence,
            price_impact=avg_slippage,
            liquidity_utilization=Decimal('0.5')
        )
        
        return OptimizedRoute(
            route_id=route_id,
            token_in=Token(address=token_in, symbol="", decimals=18, name=""),
            token_out=Token(address=token_out, symbol="", decimals=18, name=""),
            total_amount_in=amount_in,
            total_expected_out=total_expected_out,
            total_min_out=total_min_out,
            splits=splits,
            predicted_slippage=avg_slippage,
            expected_gas=Decimal('0.05') * len(splits),
            confidence_score=confidence,
            risk_score=float(avg_slippage)
        )
    
    async def _optimize_weighted_liquidity(
        self,
        pools: List[DEXPool],
        amount_in: Decimal,
        token_in: str,
        token_out: str,
        max_slippage: Decimal
    ) -> List[RouteSplit]:
        """
        Weighted liquidity optimization
        Split amount proportional to pool liquidity
        """
        if not pools:
            return []
        
        # Sort by liquidity
        sorted_pools = sorted(pools, key=lambda p: p.reserve_usd, reverse=True)
        total_liquidity = sum(p.reserve_usd for p in sorted_pools)
        
        if total_liquidity <= 0:
            return []
        
        splits = []
        remaining_amount = amount_in
        
        for pool in sorted_pools:
            if remaining_amount <= 0:
                break
            
            # Calculate weighted share
            liquidity_share = pool.reserve_usd / total_liquidity
            pool_amount = amount_in * liquidity_share
            
            # Minimum allocation threshold (5%)
            if pool_amount < amount_in * Decimal('0.05'):
                continue
            
            # Ensure we don't exceed remaining
            pool_amount = min(pool_amount, remaining_amount)
            
            # Calculate expected output
            expected_out, token_in_obj, token_out_obj = self._calculate_swap_output(
                pool, pool_amount, token_in, token_out
            )
            
            if expected_out > 0:
                min_out = expected_out * (Decimal('1') - max_slippage)
                
                splits.append(RouteSplit(
                    dex_name=pool.dex_name,
                    pool_address=pool.pool_address,
                    token_in=token_in_obj,
                    token_out=token_out_obj,
                    amount_in=pool_amount,
                    expected_amount_out=expected_out,
                    min_amount_out=min_out,
                    path=[token_in, token_out]
                ))
                
                remaining_amount -= pool_amount
        
        # Add remaining to largest pool
        if remaining_amount > 0 and splits:
            splits[0].amount_in += remaining_amount
            pool = sorted_pools[0]
            expected_out, _, _ = self._calculate_swap_output(
                pool, splits[0].amount_in, token_in, token_out
            )
            splits[0].expected_amount_out = expected_out
            splits[0].min_amount_out = expected_out * (Decimal('1') - max_slippage)
        
        return splits
    
    async def _optimize_price_impact(
        self,
        pools: List[DEXPool],
        amount_in: Decimal,
        token_in: str,
        token_out: str,
        max_slippage: Decimal
    ) -> List[RouteSplit]:
        """
        Price impact minimization
        Iteratively optimize to minimize total price impact
        """
        # Simplified: use weighted liquidity as base
        # In production, would use iterative optimization algorithm
        return await self._optimize_weighted_liquidity(
            pools, amount_in, token_in, token_out, max_slippage
        )
    
    async def _optimize_balanced(
        self,
        pools: List[DEXPool],
        amount_in: Decimal,
        token_in: str,
        token_out: str,
        max_slippage: Decimal
    ) -> List[RouteSplit]:
        """
        Balanced optimization - equal distribution
        """
        if not pools:
            return []
        
        splits = []
        amount_per_pool = amount_in / Decimal(len(pools))
        
        for pool in pools:
            expected_out, token_in_obj, token_out_obj = self._calculate_swap_output(
                pool, amount_per_pool, token_in, token_out
            )
            
            if expected_out > 0:
                splits.append(RouteSplit(
                    dex_name=pool.dex_name,
                    pool_address=pool.pool_address,
                    token_in=token_in_obj,
                    token_out=token_out_obj,
                    amount_in=amount_per_pool,
                    expected_amount_out=expected_out,
                    min_amount_out=expected_out * (Decimal('1') - max_slippage),
                    path=[token_in, token_out]
                ))
        
        return splits
    
    async def _optimize_greedy(
        self,
        pools: List[DEXPool],
        amount_in: Decimal,
        token_in: str,
        token_out: str,
        max_slippage: Decimal
    ) -> List[RouteSplit]:
        """
        Greedy optimization - use best pool only
        """
        if not pools:
            return []
        
        # Find best pool (highest liquidity)
        best_pool = max(pools, key=lambda p: p.reserve_usd)
        
        expected_out, token_in_obj, token_out_obj = self._calculate_swap_output(
            best_pool, amount_in, token_in, token_out
        )
        
        if expected_out > 0:
            return [RouteSplit(
                dex_name=best_pool.dex_name,
                pool_address=best_pool.pool_address,
                token_in=token_in_obj,
                token_out=token_out_obj,
                amount_in=amount_in,
                expected_amount_out=expected_out,
                min_amount_out=expected_out * (Decimal('1') - max_slippage),
                path=[token_in, token_out]
            )]
        
        return []
    
    def _calculate_swap_output(
        self,
        pool: DEXPool,
        amount_in: Decimal,
        token_in: str,
        token_out: str
    ) -> Tuple[Decimal, Token, Token]:
        """
        Calculate swap output using constant product formula
        Returns: (expected_out, token_in_obj, token_out_obj)
        """
        if amount_in <= 0 or pool.reserve0 <= 0 or pool.reserve1 <= 0:
            return Decimal('0'), pool.token0, pool.token1
        
        # Determine token order
        if pool.token0.address.lower() == token_in.lower():
            reserve_in = pool.reserve0
            reserve_out = pool.reserve1
            token_in_obj = pool.token0
            token_out_obj = pool.token1
        else:
            reserve_in = pool.reserve1
            reserve_out = pool.reserve0
            token_in_obj = pool.token1
            token_out_obj = pool.token0
        
        # Constant product formula with fee
        fee_bps = self.dex_registry.get(pool.dex_name.lower(), DEXConfig(
            dex_id="", name="", router_address="", factory_address="", fee_bps=30, priority=99
        )).fee_bps
        
        amount_in_with_fee = amount_in * Decimal(10000 - fee_bps) / Decimal('10000')
        numerator = amount_in_with_fee * reserve_out
        denominator = reserve_in + amount_in_with_fee
        
        if denominator <= 0:
            return Decimal('0'), token_in_obj, token_out_obj
        
        expected_out = numerator / denominator
        
        return expected_out, token_in_obj, token_out_obj
    
    def get_dex_registry(self) -> Dict[str, DEXConfig]:
        """Get DEX registry"""
        return self.dex_registry
    
    def get_active_dexes(self) -> List[str]:
        """Get list of active DEX IDs"""
        return [dex_id for dex_id, config in self.dex_registry.items() if config.is_active]
    
    def register_dex(self, config: DEXConfig):
        """Register a new DEX"""
        self.dex_registry[config.dex_id] = config
        logger.info(f"Registered DEX: {config.dex_id} - {config.name}")
    
    def toggle_dex(self, dex_id: str, is_active: bool):
        """Toggle DEX active status"""
        if dex_id in self.dex_registry:
            self.dex_registry[dex_id].is_active = is_active
            logger.info(f"Set DEX {dex_id} active={is_active}")
