"""
Pipeline Safety Service - Pre-execution validation, circuit breakers, and risk management
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from web3 import Web3
import asyncio

class SafetyCheckResult:
    """Result of a safety check"""
    def __init__(self, passed: bool, reason: Optional[str] = None, risk_score: float = 0.0):
        self.passed = passed
        self.reason = reason
        self.risk_score = risk_score  # 0.0 (safe) to 1.0 (high risk)

class PipelineSafetyService:
    """Service for pipeline safety checks and risk management"""
    
    def __init__(self, w3: Web3):
        self.w3 = w3
        self.circuit_breaker_active = False
        self.max_pipeline_value = 10**18 * 1000000  # 1M tokens default
        self.volatility_threshold = 0.1  # 10% volatility threshold
        self.min_liquidity_threshold = 10**18 * 10000  # 10k tokens minimum liquidity
        
    async def pre_execution_check(
        self,
        pipeline_type: str,
        steps: List[Dict],
        min_total_out: int,
        deadline: int,
        creator: str
    ) -> SafetyCheckResult:
        """Comprehensive pre-execution safety check"""
        
        # Check 1: Circuit breaker
        if self.circuit_breaker_active:
            return SafetyCheckResult(
                passed=False,
                reason="Circuit breaker is active",
                risk_score=1.0
            )
        
        # Check 2: Deadline validation
        if datetime.now().timestamp() > deadline:
            return SafetyCheckResult(
                passed=False,
                reason="Pipeline deadline has passed",
                risk_score=0.8
            )
        
        # Check 3: Value limits
        if min_total_out > self.max_pipeline_value:
            return SafetyCheckResult(
                passed=False,
                reason=f"Pipeline value exceeds maximum: {min_total_out} > {self.max_pipeline_value}",
                risk_score=0.9
            )
        
        # Check 4: Step validation
        for i, step in enumerate(steps):
            if not step.get('target') or not step.get('data'):
                return SafetyCheckResult(
                    passed=False,
                    reason=f"Invalid step {i}: missing target or data",
                    risk_score=0.7
                )
        
        # Check 5: High-value pipeline human approval (if >5% of treasury)
        # This would check against treasury balance in production
        if min_total_out > self.max_pipeline_value * 0.05:
            return SafetyCheckResult(
                passed=False,
                reason="High-value pipeline requires human approval",
                risk_score=0.6
            )
        
        # Check 6: Liquidity pre-check (for swap operations)
        if pipeline_type == "CrossDEXSettlement":
            liquidity_check = await self._check_liquidity_availability(steps)
            if not liquidity_check.passed:
                return liquidity_check
        
        # Check 7: Slippage validation
        slippage_check = await self._validate_slippage_limits(steps, min_total_out)
        if not slippage_check.passed:
            return slippage_check
        
        # All checks passed
        return SafetyCheckResult(
            passed=True,
            risk_score=0.1  # Low risk
        )
    
    async def _check_liquidity_availability(self, steps: List[Dict]) -> SafetyCheckResult:
        """Check if sufficient liquidity exists for swap operations"""
        # In production, this would query on-chain liquidity
        # For now, return passed
        return SafetyCheckResult(passed=True, risk_score=0.2)
    
    async def _validate_slippage_limits(
        self,
        steps: List[Dict],
        min_total_out: int
    ) -> SafetyCheckResult:
        """Validate that slippage limits are reasonable"""
        # Check that min outputs are within reasonable bounds
        # This is a simplified check - production would use real-time price data
        return SafetyCheckResult(passed=True, risk_score=0.1)
    
    async def check_volatility_bands(
        self,
        token_pair: str,
        max_volatility: float = 0.1
    ) -> SafetyCheckResult:
        """Check if volatility is within acceptable bands"""
        # In production, this would query market data
        # Mock implementation
        current_volatility = 0.05  # Mock 5% volatility
        
        if current_volatility > max_volatility:
            return SafetyCheckResult(
                passed=False,
                reason=f"Volatility {current_volatility} exceeds threshold {max_volatility}",
                risk_score=0.7
            )
        
        return SafetyCheckResult(passed=True, risk_score=0.2)
    
    async def check_liquidity_minimums(
        self,
        token_pair: str,
        trade_size: int
    ) -> SafetyCheckResult:
        """Check if minimum liquidity requirements are met"""
        # In production, this would query on-chain reserves
        mock_liquidity = 10**18 * 100000  # Mock 100k tokens
        
        if mock_liquidity < self.min_liquidity_threshold:
            return SafetyCheckResult(
                passed=False,
                reason=f"Insufficient liquidity: {mock_liquidity} < {self.min_liquidity_threshold}",
                risk_score=0.8
            )
        
        # Check if trade size is too large relative to liquidity
        if trade_size > mock_liquidity * 0.1:  # Max 10% of pool
            return SafetyCheckResult(
                passed=False,
                reason=f"Trade size {trade_size} exceeds 10% of liquidity {mock_liquidity}",
                risk_score=0.6
            )
        
        return SafetyCheckResult(passed=True, risk_score=0.2)
    
    def toggle_circuit_breaker(self, active: bool):
        """Toggle circuit breaker on/off"""
        self.circuit_breaker_active = active
    
    def set_max_pipeline_value(self, max_value: int):
        """Set maximum pipeline value"""
        self.max_pipeline_value = max_value
    
    def set_volatility_threshold(self, threshold: float):
        """Set volatility threshold"""
        self.volatility_threshold = threshold
    
    def set_min_liquidity_threshold(self, threshold: int):
        """Set minimum liquidity threshold"""
        self.min_liquidity_threshold = threshold

