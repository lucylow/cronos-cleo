"""
Transaction sending utilities - supports both signed tx broadcast and server-side sending
"""
import os
import logging
from typing import Dict, Any, Optional
from web3 import Web3
from web3.types import Wei, TxParams, HexStr
from gas_utils import get_provider, get_gas_recommendation
from gas_estimate import estimate_gas_limit

logger = logging.getLogger(__name__)

SERVER_PRIVATE_KEY = os.getenv("DEPLOY_PRIVATE_KEY") or os.getenv("EXECUTOR_PRIVATE_KEY")


async def send_signed_transaction(signed_tx_hex: str) -> Dict[str, Any]:
    """
    Broadcast a signed transaction
    
    Args:
        signed_tx_hex: Hex string of signed transaction
    
    Returns:
        {'hash': str, 'wait': callable}
    """
    provider = get_provider()
    
    try:
        # Send the signed transaction
        tx_hash = provider.eth.send_raw_transaction(HexStr(signed_tx_hex))
        
        return {
            'hash': tx_hash.hex(),
            'wait': lambda confirmations=1: _wait_for_confirmation(tx_hash, confirmations)
        }
    except Exception as e:
        logger.error(f"Failed to send signed transaction: {e}")
        raise ValueError(f"Failed to send transaction: {str(e)}")


async def send_from_server_wallet(
    tx_request: Dict[str, Any],
    buffer_percent: int = 20,
    cap: int = 10_000_000
) -> Dict[str, Any]:
    """
    Send transaction from server wallet (requires DEPLOY_PRIVATE_KEY or EXECUTOR_PRIVATE_KEY)
    
    Args:
        tx_request: Transaction request with to, data, value, nonce (optional)
        buffer_percent: Gas buffer percentage
        cap: Maximum gas limit
    
    Returns:
        {'hash': str, 'wait': callable}
    """
    if not SERVER_PRIVATE_KEY:
        raise ValueError("Server private key not configured (DEPLOY_PRIVATE_KEY or EXECUTOR_PRIVATE_KEY)")
    
    provider = get_provider()
    
    # Create account from private key
    account = provider.eth.account.from_key(SERVER_PRIVATE_KEY)
    wallet_address = account.address
    
    # 1) Estimate gas limit
    tx_with_from = {**tx_request, 'from': wallet_address}
    gas_limit = await estimate_gas_limit(tx_with_from, buffer_percent, cap)
    
    # 2) Get gas recommendation
    rec = await get_gas_recommendation()
    
    # 3) Get nonce
    nonce = tx_request.get('nonce')
    if nonce is None:
        nonce = provider.eth.get_transaction_count(wallet_address)
    
    # 4) Build transaction
    tx: TxParams = {
        'to': tx_request['to'],
        'data': tx_request.get('data', '0x'),
        'value': tx_request.get('value', 0),
        'gas': gas_limit,
        'nonce': nonce,
        'chainId': provider.eth.chain_id,
    }
    
    # Add gas price fields based on EIP-1559 support
    if rec['supports1559'] and rec['maxFeePerGas'] and rec['maxPriorityFeePerGas']:
        # Add margin to maxFeePerGas
        margin = Web3.to_wei(2, 'gwei')
        tx['maxPriorityFeePerGas'] = rec['maxPriorityFeePerGas']
        tx['maxFeePerGas'] = rec['maxFeePerGas'] + margin
    elif rec['legacyGasPrice']:
        tx['gasPrice'] = rec['legacyGasPrice']
    else:
        # Fallback: use current gas price
        tx['gasPrice'] = provider.eth.gas_price
    
    # 5) Sign and send
    try:
        signed_txn = account.sign_transaction(tx)
        tx_hash = provider.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        return {
            'hash': tx_hash.hex(),
            'wait': lambda confirmations=1: _wait_for_confirmation(tx_hash, confirmations)
        }
    except Exception as e:
        logger.error(f"Failed to send transaction from server wallet: {e}")
        raise ValueError(f"Failed to send transaction: {str(e)}")


async def _wait_for_confirmation(tx_hash: HexStr, confirmations: int = 1) -> Dict[str, Any]:
    """Wait for transaction confirmation"""
    provider = get_provider()
    receipt = provider.eth.wait_for_transaction_receipt(tx_hash, timeout=120, poll_latency=3)
    
    # Wait for additional confirmations if needed
    if confirmations > 1:
        current_block = provider.eth.block_number
        blocks_to_wait = confirmations - (current_block - receipt['blockNumber'] + 1)
        if blocks_to_wait > 0:
            # Wait for additional blocks
            target_block = current_block + blocks_to_wait
            while provider.eth.block_number < target_block:
                await asyncio.sleep(3)  # Wait 3 seconds between checks
            receipt = provider.eth.get_transaction_receipt(tx_hash)
    
    return {
        'blockNumber': receipt['blockNumber'],
        'blockHash': receipt['blockHash'].hex(),
        'transactionHash': receipt['transactionHash'].hex(),
        'status': receipt['status'],
        'gasUsed': receipt['gasUsed'],
    }
