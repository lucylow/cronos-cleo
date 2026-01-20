"""
Integration layer for Multi-Leg Transactions with existing systems
Connects multi-leg coordinator with x402 executor and pipeline executor
"""
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session
from web3 import Web3

from .coordinator import MultiLegCoordinator
from .models import TransactionLeg, LegStatus, LegType

logger = logging.getLogger(__name__)


class X402LegExecutor:
    """Executor for legs using x402 facilitator"""
    
    def __init__(self, x402_executor):
        self.x402_executor = x402_executor
    
    async def execute_leg(self, leg: TransactionLeg) -> Dict[str, Any]:
        """Execute a leg using x402 executor"""
        try:
            # Convert leg to x402 format
            if leg.leg_type == LegType.SWAP:
                # Execute swap leg
                routes = self._leg_to_routes(leg)
                result = await self.x402_executor.execute_swap(
                    routes=routes,
                    total_amount_in=float(Decimal(leg.amount_in or "0") / Decimal(1e18)),
                    token_in=leg.token_in or "",
                    token_out=leg.token_out or "",
                    min_total_out=float(Decimal(leg.amount_out or "0") / Decimal(1e18))
                )
                
                return {
                    "tx_hash": result.get("tx_hash"),
                    "gas_used": result.get("gas_used", 0),
                    "amount_out": leg.amount_out
                }
            elif leg.leg_type == LegType.TRANSFER:
                # Execute transfer leg
                # This would use a multi-send contract or direct transfer
                return {
                    "tx_hash": f"0x{leg.leg_id[:64]}",
                    "gas_used": 21000,
                    "amount_out": leg.amount_out
                }
            else:
                # Generic execution
                return {
                    "tx_hash": f"0x{leg.leg_id[:64]}",
                    "gas_used": 21000,
                    "amount_out": leg.amount_out
                }
                
        except Exception as e:
            logger.error(f"Leg execution failed: {e}")
            raise
    
    def _leg_to_routes(self, leg: TransactionLeg) -> List[Dict]:
        """Convert leg to route format for x402 executor"""
        # Parse function data or metadata to extract route information
        metadata = {}
        if leg.extra_metadata:
            import json
            metadata = json.loads(leg.extra_metadata)
        
        # Create a simple route from leg data
        route = {
            "dexId": metadata.get("dex", "vvs"),
            "path": [leg.token_in, leg.token_out] if leg.token_in and leg.token_out else [],
            "amountIn": int(Decimal(leg.amount_in or "0")),
            "minAmountOut": int(Decimal(leg.amount_out or "0") * Decimal("0.995"))  # 0.5% slippage buffer
        }
        
        return [route]


class PipelineLegExecutor:
    """Executor for legs using pipeline executor"""
    
    def __init__(self, pipeline_executor):
        self.pipeline_executor = pipeline_executor
    
    async def execute_leg(self, leg: TransactionLeg) -> Dict[str, Any]:
        """Execute a leg using pipeline executor"""
        # This would integrate with the pipeline executor
        # For now, return mock result
        return {
            "tx_hash": f"0x{leg.leg_id[:64]}",
            "gas_used": 100000,
            "amount_out": leg.amount_out
        }


def create_integrated_coordinator(
    db_session: Session,
    w3: Web3,
    x402_executor: Optional[Any] = None,
    pipeline_executor: Optional[Any] = None
) -> MultiLegCoordinator:
    """
    Create a multi-leg coordinator integrated with existing executors
    
    Args:
        db_session: Database session
        w3: Web3 instance
        x402_executor: Optional x402 executor
        pipeline_executor: Optional pipeline executor
        
    Returns:
        MultiLegCoordinator with integrated executors
    """
    coordinator = MultiLegCoordinator(
        db_session=db_session,
        w3=w3,
        compensation_strategy=CompensationStrategy.SAGA
    )
    
    # Create executor function that uses appropriate executor
    async def integrated_executor(leg: TransactionLeg) -> Dict[str, Any]:
        """Integrated executor that routes to appropriate executor"""
        if x402_executor and leg.leg_type in [LegType.SWAP, LegType.TRANSFER]:
            x402_leg_executor = X402LegExecutor(x402_executor)
            return await x402_leg_executor.execute_leg(leg)
        elif pipeline_executor:
            pipeline_leg_executor = PipelineLegExecutor(pipeline_executor)
            return await pipeline_leg_executor.execute_leg(leg)
        else:
            # Fallback to default
            return await coordinator._execute_leg_default(leg)
    
    # Override default executor
    coordinator._execute_leg_default = integrated_executor
    
    return coordinator

