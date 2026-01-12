"""
Transaction monitoring utilities
"""
import logging
import asyncio
from typing import Dict, Any, Optional
from web3 import Web3
from web3.types import HexStr
from gas_utils import get_provider

logger = logging.getLogger(__name__)


async def monitor_tx(
    tx_hash: str,
    confirmations: int = 1,
    poll_interval_ms: int = 3000,
    timeout_ms: int = 120000
) -> Dict[str, Any]:
    """
    Monitor transaction until confirmation
    
    Args:
        tx_hash: Transaction hash
        confirmations: Number of confirmations required
        poll_interval_ms: Polling interval in milliseconds
        timeout_ms: Timeout in milliseconds
    
    Returns:
        Transaction receipt dict
    """
    provider = get_provider()
    import time
    start_time = time.time() * 1000  # Convert to ms
    
    while True:
        # Check timeout
        elapsed = (time.time() * 1000) - start_time
        if elapsed > timeout_ms:
            raise TimeoutError(f"Transaction monitoring timeout after {timeout_ms}ms")
        
        try:
            receipt = provider.eth.get_transaction_receipt(HexStr(tx_hash))
            
            if receipt and receipt.get('blockNumber'):
                if confirmations <= 1:
                    return {
                        'blockNumber': receipt['blockNumber'],
                        'blockHash': receipt['blockHash'].hex(),
                        'transactionHash': receipt['transactionHash'].hex(),
                        'status': receipt['status'],
                        'gasUsed': receipt['gasUsed'],
                    }
                
                # Check confirmations
                current_block = provider.eth.block_number
                confirmations_count = current_block - receipt['blockNumber'] + 1
                
                if confirmations_count >= confirmations:
                    return {
                        'blockNumber': receipt['blockNumber'],
                        'blockHash': receipt['blockHash'].hex(),
                        'transactionHash': receipt['transactionHash'].hex(),
                        'status': receipt['status'],
                        'gasUsed': receipt['gasUsed'],
                        'confirmations': confirmations_count,
                    }
        except Exception as e:
            # Transaction not found yet, continue polling
            if 'not found' not in str(e).lower():
                logger.warning(f"Error checking transaction receipt: {e}")
        
        # Wait before next poll
        await asyncio.sleep(poll_interval_ms / 1000)
