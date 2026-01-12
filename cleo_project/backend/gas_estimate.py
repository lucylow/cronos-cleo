"""
Gas estimation utilities with safety buffers
"""
import logging
from typing import Dict, Any, Optional
from web3 import Web3
from web3.types import Wei, TxParams
from gas_utils import get_provider

logger = logging.getLogger(__name__)


async def estimate_gas_limit(
    tx_request: Dict[str, Any],
    buffer_percent: int = 20,
    cap: int = 10_000_000
) -> int:
    """
    Estimate gas limit for a transaction with safety buffer
    
    Args:
        tx_request: Transaction request dict with keys: to, data, value, from
        buffer_percent: Percentage buffer to add (default 20%)
        cap: Maximum gas limit cap (default 10M)
    
    Returns:
        Estimated gas limit as integer
    """
    provider = get_provider()
    
    # Prepare transaction params for estimation
    tx_params: TxParams = {
        'to': tx_request.get('to'),
        'data': tx_request.get('data'),
        'value': tx_request.get('value', 0),
    }
    
    # Include 'from' if provided (helps with more accurate estimation)
    if 'from' in tx_request:
        tx_params['from'] = tx_request['from']
    
    try:
        # Estimate gas
        estimated = provider.eth.estimate_gas(tx_params)
        
        # Apply buffer
        buffered = int(estimated * (100 + buffer_percent) / 100)
        
        # Cap at maximum
        return min(buffered, cap)
    except Exception as e:
        logger.error(f"Gas estimation failed: {e}")
        raise ValueError(f"Gas estimation failed: {str(e)}")
