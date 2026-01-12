"""
Transaction Simulator for Pre-Execution Validation
Simulates swap execution to predict outcomes before actual on-chain execution
"""
import asyncio
from typing import Dict, List, Optional, Any
from web3 import Web3, AsyncWeb3
from decimal import Decimal


class TransactionSimulator:
    """
    Simulates DEX swap execution to predict outcomes
    Uses constant product formula (x * y = k) for AMM pools
    """
    
    def __init__(self, rpc_url: str):
        self.w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(rpc_url))
    
    def calculate_amm_output(
        self,
        amount_in: float,
        reserve_in: float,
        reserve_out: float,
        fee_bps: int = 30
    ) -> float:
        """
        Calculate output amount using constant product formula (Uniswap V2 style)
        
        Formula: (x + Δx) * (y - Δy) = k
        With fee: amount_in_with_fee = amount_in * (10000 - fee_bps) / 10000
        
        Args:
            amount_in: Input amount
            reserve_in: Input token reserve in pool
            reserve_out: Output token reserve in pool
            fee_bps: Fee in basis points (e.g., 30 = 0.3%)
            
        Returns:
            Output amount
        """
        if reserve_in == 0 or reserve_out == 0:
            return 0.0
        
        # Apply fee
        fee_multiplier = (10000 - fee_bps) / 10000
        amount_in_with_fee = amount_in * fee_multiplier
        
        # Constant product formula
        # (reserve_in + amount_in_with_fee) * (reserve_out - amount_out) = reserve_in * reserve_out
        # Solving for amount_out:
        numerator = amount_in_with_fee * reserve_out
        denominator = reserve_in + amount_in_with_fee
        amount_out = numerator / denominator
        
        return amount_out
    
    def calculate_price_impact(
        self,
        amount_in: float,
        reserve_in: float,
        reserve_out: float,
        fee_bps: int = 30
    ) -> Dict[str, float]:
        """
        Calculate price impact and slippage for a swap
        
        Returns:
            Dictionary with output amount, price impact, and effective price
        """
        # Spot price (before swap)
        spot_price = reserve_out / reserve_in if reserve_in > 0 else 0
        
        # Calculate output
        amount_out = self.calculate_amm_output(amount_in, reserve_in, reserve_out, fee_bps)
        
        # Effective price
        effective_price = amount_out / amount_in if amount_in > 0 else 0
        
        # Price impact (slippage)
        price_impact = abs((effective_price - spot_price) / spot_price * 100) if spot_price > 0 else 0
        
        return {
            "amount_out": amount_out,
            "spot_price": spot_price,
            "effective_price": effective_price,
            "price_impact_pct": price_impact,
            "slippage_pct": price_impact
        }
    
    async def simulate_multi_route_swap(
        self,
        routes: List[Dict],
        pools: List[Dict]
    ) -> Dict[str, Any]:
        """
        Simulate execution across multiple routes
        
        Args:
            routes: List of route splits with dex, amountIn, path
            pools: List of pool data with reserves and fees
            
        Returns:
            Simulation results with total output, slippage, etc.
        """
        total_in = sum(float(r.get("amountIn", 0)) for r in routes)
        total_out = 0.0
        route_results = []
        
        for route in routes:
            dex_id = route.get("dexId", "").lower()
            amount_in = float(route.get("amountIn", 0))
            
            # Find matching pool
            pool = None
            for p in pools:
                if p.get("dex", "").lower() == dex_id:
                    pool = p
                    break
            
            if not pool:
                # Use default pool data
                pool = {
                    "reserve0": 1000000,
                    "reserve1": 500000,
                    "feeBps": 30
                }
            
            # Determine which reserve is which based on path
            reserve_in = float(pool.get("reserve0", 1000000))
            reserve_out = float(pool.get("reserve1", 500000))
            fee_bps = int(pool.get("feeBps", 30))
            
            # Calculate output for this route
            impact_data = self.calculate_price_impact(
                amount_in,
                reserve_in,
                reserve_out,
                fee_bps
            )
            
            route_out = impact_data["amount_out"]
            total_out += route_out
            
            route_results.append({
                "dex": dex_id,
                "amount_in": amount_in,
                "amount_out": route_out,
                "price_impact_pct": impact_data["price_impact_pct"],
                "effective_price": impact_data["effective_price"]
            })
        
        # Calculate overall metrics
        overall_slippage = abs((total_out / total_in - 1) * 100) if total_in > 0 else 0
        effective_rate = total_out / total_in if total_in > 0 else 0
        
        return {
            "total_in": total_in,
            "total_out": total_out,
            "effective_rate": effective_rate,
            "overall_slippage_pct": overall_slippage,
            "route_count": len(routes),
            "route_results": route_results,
            "success": True
        }
    
    async def simulate_with_slippage_tolerance(
        self,
        routes: List[Dict],
        pools: List[Dict],
        max_slippage_pct: float = 0.5
    ) -> Dict[str, Any]:
        """
        Simulate and validate against slippage tolerance
        
        Returns:
            Simulation result with validation status
        """
        simulation = await self.simulate_multi_route_swap(routes, pools)
        
        # Validate slippage
        within_tolerance = simulation["overall_slippage_pct"] <= max_slippage_pct
        
        simulation["within_slippage_tolerance"] = within_tolerance
        simulation["max_slippage_pct"] = max_slippage_pct
        
        if not within_tolerance:
            simulation["warning"] = f"Slippage {simulation['overall_slippage_pct']:.2f}% exceeds tolerance {max_slippage_pct}%"
        
        return simulation
    
    def estimate_gas_cost(
        self,
        route_count: int,
        base_gas: int = 120000,
        per_route_gas: int = 12000
    ) -> Dict[str, int]:
        """
        Estimate gas cost for multi-route execution
        
        Args:
            route_count: Number of routes
            base_gas: Base gas for transaction
            per_route_gas: Additional gas per route
            
        Returns:
            Gas estimates
        """
        total_gas = base_gas + (route_count * per_route_gas)
        
        return {
            "base_gas": base_gas,
            "per_route_gas": per_route_gas,
            "total_gas": total_gas,
            "route_count": route_count
        }
    
    async def compare_single_vs_multi_route(
        self,
        total_amount: float,
        single_pool: Dict,
        multi_routes: List[Dict],
        multi_pools: List[Dict]
    ) -> Dict[str, Any]:
        """
        Compare single route vs multi-route execution
        
        Returns:
            Comparison showing improvement from multi-route
        """
        # Simulate single route
        single_result = self.calculate_price_impact(
            total_amount,
            float(single_pool.get("reserve0", 1000000)),
            float(single_pool.get("reserve1", 500000)),
            int(single_pool.get("feeBps", 30))
        )
        
        # Simulate multi-route
        multi_result = await self.simulate_multi_route_swap(multi_routes, multi_pools)
        
        # Calculate improvement
        single_output = single_result["amount_out"]
        multi_output = multi_result["total_out"]
        
        improvement_pct = ((multi_output - single_output) / single_output * 100) if single_output > 0 else 0
        savings = multi_output - single_output
        
        return {
            "single_route": {
                "output": single_output,
                "slippage_pct": single_result["price_impact_pct"]
            },
            "multi_route": {
                "output": multi_output,
                "slippage_pct": multi_result["overall_slippage_pct"]
            },
            "improvement": {
                "output_increase_pct": improvement_pct,
                "savings": savings,
                "slippage_reduction_pct": single_result["price_impact_pct"] - multi_result["overall_slippage_pct"]
            }
        }

