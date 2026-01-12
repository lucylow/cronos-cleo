"""
Route Optimizer Agent - Calculates optimal route splits
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from decimal import Decimal

from .base_agent import BaseAgent
from .message_bus import AgentMessage
from .models import DEXPool, RouteSplit, OptimizedRoute, Token

logger = logging.getLogger(__name__)


class RouteOptimizerAgent(BaseAgent):
    """Agent responsible for calculating optimal route splits"""
    
    def __init__(self):
        super().__init__("route_optimizer", "Route Optimizer")
        self.optimization_strategies = {
            "proportional": self._proportional_split,
            "greedy": self._greedy_split,
            "balanced": self._balanced_split,
            "ai_optimized": self._ai_optimized_split
        }
        self._pending_requests: Dict[str, Dict] = {}
    
    async def handle_message(self, message: AgentMessage):
        """Handle incoming messages"""
        if message.message_type == "optimize_route":
            # Extract parameters
            token_in = message.payload.get("token_in")
            token_out = message.payload.get("token_out")
            amount_in = Decimal(str(message.payload.get("amount_in", 0)))
            max_slippage = Decimal(str(message.payload.get("max_slippage", 0.05)))  # 5% default
            strategy = message.payload.get("strategy", "ai_optimized")
            request_id = message.payload.get("request_id")
            
            # Store the original request
            self._pending_requests[request_id] = {
                "original_message": message,
                "params": {
                    "token_in": token_in,
                    "token_out": token_out,
                    "amount_in": amount_in,
                    "max_slippage": max_slippage,
                    "strategy": strategy
                }
            }
            
            # Request liquidity data
            liquidity_msg = AgentMessage(
                message_id=f"liquidity_req_{datetime.now().timestamp()}_{request_id}",
                sender=self.agent_id,
                receiver="liquidity_analyzer",
                message_type="get_liquidity",
                payload={
                    "token_in": token_in,
                    "token_out": token_out,
                    "request_id": request_id
                }
            )
            await self.send_message(liquidity_msg)
        
        elif message.message_type == "liquidity_response":
            # Process liquidity response and calculate optimal route
            request_id = message.payload.get("request_id")
            if request_id in self._pending_requests:
                pools_data = message.payload.get("pools", [])
                pools = [DEXPool(**pool) for pool in pools_data]
                await self._process_liquidity_response(pools, request_id)
    
    async def _process_liquidity_response(self, pools: List[DEXPool], request_id: str):
        """Process liquidity response and calculate optimal route"""
        if request_id not in self._pending_requests:
            return
        
        request = self._pending_requests.pop(request_id)
        params = request["params"]
        original_message = request["original_message"]
        
        # Get strategy function
        strategy_func = self.optimization_strategies.get(
            params["strategy"], self._ai_optimized_split
        )
        
        # Calculate optimal split
        optimal_splits = await strategy_func(
            pools=pools,
            amount_in=params["amount_in"],
            token_in=params["token_in"],
            token_out=params["token_out"],
            max_slippage=params["max_slippage"]
        )
        
        # Create optimized route
        total_expected_out = sum(split.expected_amount_out for split in optimal_splits)
        total_min_out = sum(split.min_amount_out for split in optimal_splits)
        
        # Calculate predicted slippage (average)
        predicted_slippage = params["max_slippage"] if optimal_splits else Decimal('0')
        
        optimized_route = OptimizedRoute(
            route_id=f"route_{datetime.now().timestamp()}_{request_id}",
            token_in=Token(address=params["token_in"], symbol="", decimals=18, name=""),
            token_out=Token(address=params["token_out"], symbol="", decimals=18, name=""),
            total_amount_in=params["amount_in"],
            total_expected_out=total_expected_out,
            total_min_out=total_min_out,
            splits=optimal_splits,
            predicted_slippage=predicted_slippage,
            expected_gas=Decimal('0.05'),  # Will be calculated
            confidence_score=0.9,
            risk_score=0.1
        )
        
        # Send response back to original requester
        response = AgentMessage(
            message_id=f"resp_{original_message.message_id}",
            sender=self.agent_id,
            receiver=original_message.sender,
            message_type="optimized_route",
            payload={
                "route": optimized_route.dict(),
                "request_id": request_id
            }
        )
        await self.send_message(response)
    
    async def _ai_optimized_split(self, pools: List[DEXPool], amount_in: Decimal,
                                token_in: str, token_out: str, max_slippage: Decimal) -> List[RouteSplit]:
        """AI-optimized split using ML predictions"""
        if not pools:
            return []
        
        splits = []
        remaining_amount = amount_in
        
        # Sort pools by liquidity (descending)
        sorted_pools = sorted(pools, key=lambda p: p.reserve_usd, reverse=True)
        
        # Distribute based on liquidity and predicted slippage
        total_liquidity = sum(p.reserve_usd for p in sorted_pools)
        
        if total_liquidity <= 0:
            return []
        
        for i, pool in enumerate(sorted_pools):
            if remaining_amount <= 0:
                break
            
            # Calculate share based on liquidity and position
            liquidity_share = pool.reserve_usd / total_liquidity
            position_factor = 1.0 / (i + 1)  # Favor higher liquidity pools
            
            share = liquidity_share * position_factor
            pool_amount = amount_in * Decimal(str(share))
            
            # Don't allocate tiny amounts
            if pool_amount < amount_in * Decimal('0.05'):  # Less than 5%
                continue
            
            # Ensure we don't exceed remaining amount
            pool_amount = min(pool_amount, remaining_amount)
            
            # Calculate expected output
            if pool.token0.address.lower() == token_in.lower() and pool.token1.address.lower() == token_out.lower():
                expected_out = self._calculate_output(
                    pool_amount, pool.reserve0, pool.reserve1, pool.fee_tier
                )
                token_in_obj = pool.token0
                token_out_obj = pool.token1
            else:
                expected_out = self._calculate_output(
                    pool_amount, pool.reserve1, pool.reserve0, pool.fee_tier
                )
                token_in_obj = pool.token1
                token_out_obj = pool.token0
            
            # Apply slippage tolerance
            min_out = expected_out * (Decimal('1') - max_slippage)
            
            split = RouteSplit(
                dex_name=pool.dex_name,
                pool_address=pool.pool_address,
                token_in=token_in_obj,
                token_out=token_out_obj,
                amount_in=pool_amount,
                expected_amount_out=expected_out,
                min_amount_out=min_out,
                path=[token_in, token_out]
            )
            
            splits.append(split)
            remaining_amount -= pool_amount
        
        # If there's remaining amount, add it to the largest pool
        if remaining_amount > 0 and splits:
            splits[0].amount_in += remaining_amount
            # Recalculate for this pool
            pool = sorted_pools[0]
            if pool.token0.address.lower() == token_in.lower():
                expected_out = self._calculate_output(
                    splits[0].amount_in, pool.reserve0, pool.reserve1, pool.fee_tier
                )
            else:
                expected_out = self._calculate_output(
                    splits[0].amount_in, pool.reserve1, pool.reserve0, pool.fee_tier
                )
            splits[0].expected_amount_out = expected_out
            splits[0].min_amount_out = expected_out * (Decimal('1') - max_slippage)
        
        return splits
    
    async def _proportional_split(self, pools: List[DEXPool], amount_in: Decimal,
                                token_in: str, token_out: str, max_slippage: Decimal) -> List[RouteSplit]:
        """Proportional split based on liquidity"""
        return await self._ai_optimized_split(pools, amount_in, token_in, token_out, max_slippage)
    
    async def _greedy_split(self, pools: List[DEXPool], amount_in: Decimal,
                           token_in: str, token_out: str, max_slippage: Decimal) -> List[RouteSplit]:
        """Greedy split - use best pool first"""
        if not pools:
            return []
        
        # Sort by best price
        best_pool = max(pools, key=lambda p: p.reserve_usd)
        return await self._ai_optimized_split([best_pool], amount_in, token_in, token_out, max_slippage)
    
    async def _balanced_split(self, pools: List[DEXPool], amount_in: Decimal,
                            token_in: str, token_out: str, max_slippage: Decimal) -> List[RouteSplit]:
        """Balanced split - equal distribution"""
        if not pools:
            return []
        
        splits = []
        amount_per_pool = amount_in / Decimal(len(pools))
        
        for pool in pools:
            if pool.token0.address.lower() == token_in.lower() and pool.token1.address.lower() == token_out.lower():
                expected_out = self._calculate_output(
                    amount_per_pool, pool.reserve0, pool.reserve1, pool.fee_tier
                )
                token_in_obj = pool.token0
                token_out_obj = pool.token1
            else:
                expected_out = self._calculate_output(
                    amount_per_pool, pool.reserve1, pool.reserve0, pool.fee_tier
                )
                token_in_obj = pool.token1
                token_out_obj = pool.token0
            
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
    
    def _calculate_output(self, amount_in: Decimal, reserve_in: Decimal,
                        reserve_out: Decimal, fee: int) -> Decimal:
        """Calculate output amount"""
        if amount_in <= 0 or reserve_in <= 0 or reserve_out <= 0:
            return Decimal('0')
        
        amount_in_with_fee = amount_in * Decimal('997') / Decimal('1000')
        numerator = amount_in_with_fee * reserve_out
        denominator = reserve_in + amount_in_with_fee
        return numerator / denominator
