"""
Condition Evaluator Service
Evaluates conditions for instruction sets (on-chain state, oracle prices, etc.)
"""
from typing import Dict, List, Optional, Any
from web3 import Web3
from .models import Condition, ConditionType
import asyncio


class ConditionEvaluator:
    """Evaluates conditions for instruction set execution"""
    
    def __init__(self, w3: Web3, liquidity_monitor=None):
        self.w3 = w3
        self.liquidity_monitor = liquidity_monitor
        
    async def evaluate_condition(self, condition: Condition, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Evaluate a single condition
        
        Args:
            condition: Condition to evaluate
            context: Optional context data (current block, prices, etc.)
            
        Returns:
            True if condition is satisfied, False otherwise
        """
        context = context or {}
        current_block = await self.w3.eth.block_number
        current_timestamp = (await self.w3.eth.get_block(current_block))['timestamp']
        
        if condition.condition_type == ConditionType.TIME_BASED:
            return await self._evaluate_time_based(condition, current_timestamp)
        elif condition.condition_type == ConditionType.PRICE_RANGE:
            return await self._evaluate_price_range(condition, context)
        elif condition.condition_type == ConditionType.PRICE_THRESHOLD:
            return await self._evaluate_price_threshold(condition, context)
        elif condition.condition_type == ConditionType.BALANCE_MIN:
            return await self._evaluate_balance_min(condition)
        elif condition.condition_type == ConditionType.BALANCE_MAX:
            return await self._evaluate_balance_max(condition)
        elif condition.condition_type == ConditionType.VAULT_UTILIZATION:
            return await self._evaluate_vault_utilization(condition)
        elif condition.condition_type == ConditionType.HEALTH_FACTOR:
            return await self._evaluate_health_factor(condition)
        elif condition.condition_type == ConditionType.POOL_LIQUIDITY:
            return await self._evaluate_pool_liquidity(condition)
        elif condition.condition_type == ConditionType.VOLATILITY:
            return await self._evaluate_volatility(condition, context)
        elif condition.condition_type == ConditionType.EXTERNAL_FLAG:
            return await self._evaluate_external_flag(condition, context)
        elif condition.condition_type == ConditionType.GOVERNANCE_FLAG:
            return await self._evaluate_governance_flag(condition)
        elif condition.condition_type == ConditionType.ORACLE_STATE:
            return await self._evaluate_oracle_state(condition)
        elif condition.condition_type == ConditionType.COMPOSITE:
            return await self._evaluate_composite(condition, context)
        else:
            raise ValueError(f"Unknown condition type: {condition.condition_type}")
    
    async def evaluate_conditions(self, conditions: List[Condition], context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Evaluate all conditions (AND logic - all must pass)
        
        Args:
            conditions: List of conditions to evaluate
            context: Optional context data
            
        Returns:
            True if all conditions are satisfied
        """
        if not conditions:
            return True  # No conditions means always pass
        
        for condition in conditions:
            result = await self.evaluate_condition(condition, context)
            if not result:
                return False
        
        return True
    
    async def _evaluate_time_based(self, condition: Condition, current_timestamp: int) -> bool:
        """Evaluate time-based condition"""
        params = condition.parameters
        threshold = params.get("timestamp")
        operator = params.get("operator", ">=")  # >=, <=, ==
        
        if operator == ">=":
            return current_timestamp >= threshold
        elif operator == "<=":
            return current_timestamp <= threshold
        elif operator == "==":
            return current_timestamp == threshold
        else:
            raise ValueError(f"Unknown operator: {operator}")
    
    async def _evaluate_price_range(self, condition: Condition, context: Dict[str, Any]) -> bool:
        """Evaluate price range condition"""
        params = condition.parameters
        pair = params.get("pair")  # e.g., "CRO/USDC"
        min_price = params.get("min_price")
        max_price = params.get("max_price")
        
        # Try to get price from context first, then fetch if needed
        price_key = f"price_{pair}"
        if price_key in context:
            price = context[price_key]
        else:
            price = await self._get_price(pair)
        
        return min_price <= price <= max_price
    
    async def _evaluate_price_threshold(self, condition: Condition, context: Dict[str, Any]) -> bool:
        """Evaluate price threshold condition"""
        params = condition.parameters
        pair = params.get("pair")
        threshold = params.get("threshold")
        operator = params.get("operator", ">=")  # >=, <=
        
        price_key = f"price_{pair}"
        if price_key in context:
            price = context[price_key]
        else:
            price = await self._get_price(pair)
        
        if operator == ">=":
            return price >= threshold
        elif operator == "<=":
            return price <= threshold
        else:
            raise ValueError(f"Unknown operator: {operator}")
    
    async def _evaluate_balance_min(self, condition: Condition) -> bool:
        """Evaluate minimum balance condition"""
        params = condition.parameters
        token_address = params.get("token_address")
        address = params.get("address")
        min_balance = params.get("min_balance")
        
        balance = self._get_balance(token_address, address)
        return balance >= min_balance
    
    async def _evaluate_balance_max(self, condition: Condition) -> bool:
        """Evaluate maximum balance condition"""
        params = condition.parameters
        token_address = params.get("token_address")
        address = params.get("address")
        max_balance = params.get("max_balance")
        
        balance = await self._get_balance(token_address, address)
        return balance <= max_balance
    
    async def _evaluate_vault_utilization(self, condition: Condition) -> bool:
        """Evaluate vault utilization condition"""
        params = condition.parameters
        vault_address = params.get("vault_address")
        min_util = params.get("min_utilization", 0)
        max_util = params.get("max_utilization", 100)
        
        # This would call vault contract to get utilization
        # For now, return True (would need vault ABI)
        try:
            # Example: vault.getUtilization() returns utilization percentage
            utilization = self._call_contract_view(
                vault_address,
                "getUtilization()",
                []
            )
            if utilization is None:
                return False  # Not implemented
            return min_util <= utilization <= max_util
        except:
            return False
    
    async def _evaluate_health_factor(self, condition: Condition) -> bool:
        """Evaluate health factor condition"""
        params = condition.parameters
        protocol_address = params.get("protocol_address")
        user_address = params.get("user_address")
        min_health_factor = params.get("min_health_factor")
        
        try:
            health_factor = await self._call_contract_view(
                protocol_address,
                "getHealthFactor(address)",
                [user_address]
            )
            return health_factor >= min_health_factor
        except:
            return False
    
    async def _evaluate_pool_liquidity(self, condition: Condition) -> bool:
        """Evaluate pool liquidity condition"""
        params = condition.parameters
        pool_address = params.get("pool_address")
        min_liquidity = params.get("min_liquidity")
        
        try:
            liquidity = self._call_contract_view(
                pool_address,
                "getLiquidity()",
                []
            )
            if liquidity is None:
                return False  # Not implemented
            return liquidity >= min_liquidity
        except:
            return False
    
    async def _evaluate_volatility(self, condition: Condition, context: Dict[str, Any]) -> bool:
        """Evaluate volatility condition"""
        params = condition.parameters
        pair = params.get("pair")
        max_volatility = params.get("max_volatility")
        
        if self.liquidity_monitor:
            try:
                volatility_data = await self.liquidity_monitor.get_historical_volatility(pair)
                volatility = volatility_data.get("volatility", 0)
                return volatility <= max_volatility
            except:
                return False
        return False
    
    async def _evaluate_external_flag(self, condition: Condition, context: Dict[str, Any]) -> bool:
        """Evaluate external flag (off-chain signal)"""
        params = condition.parameters
        flag_name = params.get("flag_name")
        
        # Check context for external flags
        flags = context.get("external_flags", {})
        return flags.get(flag_name, False)
    
    async def _evaluate_governance_flag(self, condition: Condition) -> bool:
        """Evaluate governance/DAO flag"""
        params = condition.parameters
        governance_contract = params.get("governance_contract")
        flag_name = params.get("flag_name")
        
        try:
            flag_value = await self._call_contract_view(
                governance_contract,
                f"getFlag(bytes32)",
                [flag_name]
            )
            return flag_value
        except:
            return False
    
    async def _evaluate_oracle_state(self, condition: Condition) -> bool:
        """Evaluate oracle state condition"""
        params = condition.parameters
        oracle_address = params.get("oracle_address")
        expected_state = params.get("expected_state")
        
        try:
            state = self._call_contract_view(
                oracle_address,
                "getState()",
                []
            )
            if state is None:
                return False  # Not implemented
            return state == expected_state
        except:
            return False
    
    async def _evaluate_composite(self, condition: Condition, context: Dict[str, Any]) -> bool:
        """Evaluate composite condition (AND/OR of sub-conditions)"""
        params = condition.parameters
        sub_conditions_data = params.get("conditions", [])
        logic = params.get("logic", "AND")  # AND or OR
        
        sub_conditions = [Condition.from_dict(c) for c in sub_conditions_data]
        results = [await self.evaluate_condition(c, context) for c in sub_conditions]
        
        if logic == "AND":
            return all(results)
        elif logic == "OR":
            return any(results)
        else:
            raise ValueError(f"Unknown logic operator: {logic}")
    
    # ==================== Helper Methods ====================
    
    async def _get_price(self, pair: str) -> float:
        """Get current price for a trading pair"""
        if self.liquidity_monitor:
            try:
                market_summary = await self.liquidity_monitor.get_market_summary(pair)
                return market_summary.get("current_price", 0.0)
            except:
                pass
        return 0.0
    
    def _get_balance(self, token_address: str, address: str) -> int:
        """Get token balance for an address"""
        if token_address.lower() == "native" or token_address == "0x0000000000000000000000000000000000000000":
            # Native token balance
            balance = self.w3.eth.get_balance(address)
            return balance
        else:
            # ERC20 token balance
            try:
                erc20_abi = [
                    {
                        "constant": True,
                        "inputs": [{"name": "_owner", "type": "address"}],
                        "name": "balanceOf",
                        "outputs": [{"name": "balance", "type": "uint256"}],
                        "type": "function"
                    }
                ]
                contract = self.w3.eth.contract(address=token_address, abi=erc20_abi)
                balance = contract.functions.balanceOf(address).call()
                return balance
            except:
                return 0
    
    async def _call_contract_view(self, contract_address: str, function_sig: str, args: List) -> Any:
        """Call a contract view function"""
        # This is a simplified version - would need full ABI in production
        # For now, return None (indicating not implemented)
        return None
