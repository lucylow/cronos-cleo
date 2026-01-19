"""
Payment verification utilities for EVM-native payments on Cronos
Supports native CRO and ERC-20 token payment verification
Enhanced with caching and batch verification support
"""
import logging
import time
from typing import Optional, Dict, Any, List
from web3 import Web3
from web3.types import HexStr
from gas_utils import get_provider
from functools import lru_cache

logger = logging.getLogger(__name__)

# Simple in-memory cache for payment verification results
# In production, this should be replaced with Redis or similar
_payment_cache: Dict[str, Dict[str, Any]] = {}
_cache_ttl = 3600  # 1 hour cache TTL
_cache_max_size = 1000  # Maximum cache entries


def _get_cache_key(tx_hash: str, token_address: Optional[str] = None) -> str:
    """Generate cache key for payment verification"""
    if token_address:
        return f"payment_verify:{tx_hash}:{token_address.lower()}"
    return f"payment_verify:{tx_hash}:native"


def _get_from_cache(cache_key: str) -> Optional[Dict[str, Any]]:
    """Get verification result from cache"""
    if cache_key in _payment_cache:
        entry = _payment_cache[cache_key]
        if time.time() - entry['timestamp'] < _cache_ttl:
            logger.debug(f"Cache hit for {cache_key}")
            return entry['result']
        else:
            # Expired entry
            del _payment_cache[cache_key]
            logger.debug(f"Cache expired for {cache_key}")
    return None


def _set_cache(cache_key: str, result: Dict[str, Any]):
    """Store verification result in cache"""
    # Simple LRU eviction if cache is too large
    if len(_payment_cache) >= _cache_max_size:
        # Remove oldest entry
        oldest_key = min(_payment_cache.keys(), key=lambda k: _payment_cache[k]['timestamp'])
        del _payment_cache[oldest_key]
        logger.debug(f"Evicted cache entry: {oldest_key}")
    
    _payment_cache[cache_key] = {
        'result': result,
        'timestamp': time.time(),
    }
    logger.debug(f"Cached verification result for {cache_key}")


def clear_cache():
    """Clear the payment verification cache"""
    global _payment_cache
    _payment_cache.clear()
    logger.info("Payment verification cache cleared")


async def verify_native_payment(
    tx_hash: str,
    expected_recipient: Optional[str] = None,
    min_value_wei: Optional[int] = None,
    use_cache: bool = True
) -> Dict[str, Any]:
    """
    Verify native (CRO) payment transaction on Cronos
    
    Args:
        tx_hash: Transaction hash (must be valid hex string starting with 0x)
        expected_recipient: Expected recipient address (optional, checksummed)
        min_value_wei: Minimum value in Wei (optional, for validation)
        use_cache: Whether to use cached results (default: True)
    
    Returns:
        Dictionary with receipt and transaction details
    
    Raises:
        ValueError: If transaction is invalid, failed, or doesn't match expected parameters
        Exception: If there's an error fetching transaction data
    """
    if not tx_hash or not tx_hash.startswith("0x"):
        raise ValueError(f"Invalid transaction hash format: {tx_hash}. Must start with 0x")
    
    if len(tx_hash) != 66:  # 0x + 64 hex chars
        raise ValueError(f"Invalid transaction hash length: {tx_hash}. Must be 66 characters")
    
    # Check cache first if no specific validation parameters
    if use_cache and expected_recipient is None and min_value_wei is None:
        cache_key = _get_cache_key(tx_hash)
        cached_result = _get_from_cache(cache_key)
        if cached_result:
            logger.debug(f"Using cached result for {tx_hash}")
            return cached_result
    
    try:
        provider = get_provider()
    except Exception as e:
        logger.error(f"Failed to get provider: {e}")
        raise ValueError(f"Unable to connect to blockchain: {e}")
    
    try:
        receipt = provider.eth.get_transaction_receipt(HexStr(tx_hash))
    except Exception as e:
        logger.error(f"Failed to fetch transaction receipt for {tx_hash}: {e}")
        raise ValueError(f"Transaction not found or not yet mined: {tx_hash}. Error: {e}")
    
    if not receipt:
        raise ValueError(f"Transaction receipt not found for hash: {tx_hash}")
    
    if receipt['status'] != 1:
        raise ValueError(f"Transaction failed (status: {receipt['status']}). Hash: {tx_hash}")
    
    try:
        tx = provider.eth.get_transaction(HexStr(tx_hash))
    except Exception as e:
        logger.error(f"Failed to fetch transaction for {tx_hash}: {e}")
        raise ValueError(f"Transaction object not found: {e}")
    
    if not tx:
        raise ValueError(f"Transaction object not found for hash: {tx_hash}")
    
    # Normalize addresses for comparison
    if expected_recipient:
        try:
            expected_recipient_checksum = Web3.to_checksum_address(expected_recipient)
            if tx['to']:
                tx_to_checksum = Web3.to_checksum_address(tx['to'])
                if tx_to_checksum.lower() != expected_recipient_checksum.lower():
                    raise ValueError(
                        f"Recipient mismatch: expected {expected_recipient_checksum}, "
                        f"got {tx_to_checksum} (tx hash: {tx_hash})"
                    )
            else:
                raise ValueError(f"Transaction has no recipient (contract creation), expected: {expected_recipient_checksum}")
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"Invalid recipient address format: {expected_recipient}. Error: {e}")
    
    # Verify value
    if min_value_wei is not None:
        actual_value = tx['value']
        if actual_value < min_value_wei:
            raise ValueError(
                f"Payment amount too low: got {actual_value} wei, "
                f"expected at least {min_value_wei} wei (tx hash: {tx_hash})"
            )
    
    logger.info(f"Successfully verified native payment: {tx_hash}, value: {tx['value']} wei")
    
    result = {
        'receipt': {
            'blockNumber': receipt['blockNumber'],
            'status': receipt['status'],
            'gasUsed': receipt['gasUsed'],
            'blockHash': receipt['blockHash'].hex() if receipt['blockHash'] else None,
            'transactionIndex': receipt['transactionIndex'],
        },
        'tx': {
            'to': tx['to'],
            'value': tx['value'],
            'from': tx['from'],
            'gasUsed': receipt['gasUsed'],
            'effectiveGasPrice': receipt.get('effectiveGasPrice', tx.get('gasPrice')),
        },
        'verified': True,
        'network': 'Cronos',
        'payment_type': 'native',
    }
    
    # Cache the result
    cache_key = _get_cache_key(tx_hash)
    _set_cache(cache_key, result)
    
    return result


async def verify_erc20_payment(
    tx_hash: str,
    token_address: str,
    expected_to: Optional[str] = None,
    min_amount: Optional[int] = None,
    use_cache: bool = True
) -> Dict[str, Any]:
    """
    Verify ERC20 token payment by checking Transfer event logs
    
    Args:
        tx_hash: Transaction hash (must be valid hex string starting with 0x)
        token_address: ERC20 token contract address (checksummed)
        expected_to: Expected recipient address (optional, checksummed)
        min_amount: Minimum amount in token units/wei (optional, for validation)
        use_cache: Whether to use cached results (default: True)
    
    Returns:
        Dictionary with receipt and parsed transfer event details
    
    Raises:
        ValueError: If transaction is invalid, failed, or doesn't match expected parameters
        Exception: If there's an error fetching or parsing transaction data
    """
    if not tx_hash or not tx_hash.startswith("0x"):
        raise ValueError(f"Invalid transaction hash format: {tx_hash}. Must start with 0x")
    
    if len(tx_hash) != 66:
        raise ValueError(f"Invalid transaction hash length: {tx_hash}. Must be 66 characters")
    
    if not token_address or not token_address.startswith("0x"):
        raise ValueError(f"Invalid token address format: {token_address}. Must start with 0x")
    
    # Check cache first if no specific validation parameters
    if use_cache and expected_to is None and min_amount is None:
        cache_key = _get_cache_key(tx_hash, token_address)
        cached_result = _get_from_cache(cache_key)
        if cached_result:
            logger.debug(f"Using cached result for {tx_hash} (token: {token_address})")
            return cached_result
    
    try:
        provider = get_provider()
        token_address_checksum = Web3.to_checksum_address(token_address)
    except Exception as e:
        logger.error(f"Failed to get provider or checksum token address: {e}")
        raise ValueError(f"Invalid token address or unable to connect to blockchain: {e}")
    
    try:
        receipt = provider.eth.get_transaction_receipt(HexStr(tx_hash))
    except Exception as e:
        logger.error(f"Failed to fetch transaction receipt for {tx_hash}: {e}")
        raise ValueError(f"Transaction not found or not yet mined: {tx_hash}. Error: {e}")
    
    if not receipt:
        raise ValueError(f"Transaction receipt not found for hash: {tx_hash}")
    
    if receipt['status'] != 1:
        raise ValueError(f"Transaction failed (status: {receipt['status']}). Hash: {tx_hash}")
    
    # ERC20 Transfer event signature: Transfer(address indexed from, address indexed to, uint256 value)
    # keccak256("Transfer(address,address,uint256)")
    transfer_event_signature = "0xddf252ad1be2c89b69c2b068fc378daa952b7f163c4a11628f55a4df523b3ef"
    
    # Check logs for Transfer event
    matching_transfers = []
    
    for log in receipt['logs']:
        # Check if log is from the token contract
        if log['address'].lower() != token_address_checksum.lower():
            continue
        
        # Check if it's a Transfer event (first topic is event signature)
        if len(log['topics']) >= 3:
            # Get event signature from first topic
            event_sig = log['topics'][0].hex()
            
            if event_sig == transfer_event_signature:
                try:
                    # Parse Transfer event
                    from_address = '0x' + log['topics'][1].hex()[-40:]
                    to_address = '0x' + log['topics'][2].hex()[-40:]
                    
                    # Parse value from data
                    if isinstance(log['data'], bytes):
                        value = int.from_bytes(log['data'], 'big')
                    else:
                        value = int(log['data'].hex(), 16) if hasattr(log['data'], 'hex') else int(log['data'], 16)
                    
                    # Normalize addresses
                    from_address_checksum = Web3.to_checksum_address(from_address)
                    to_address_checksum = Web3.to_checksum_address(to_address)
                    
                    # Check recipient if specified
                    if expected_to:
                        expected_to_checksum = Web3.to_checksum_address(expected_to)
                        if to_address_checksum.lower() != expected_to_checksum.lower():
                            logger.debug(f"Transfer event found but recipient mismatch")
                            continue
                    
                    # Check amount if specified
                    if min_amount is not None and value < min_amount:
                        logger.debug(f"Transfer event found but amount too low")
                        continue
                    
                    matching_transfers.append({
                        'from': from_address_checksum,
                        'to': to_address_checksum,
                        'value': value,
                    })
                    
                except Exception as e:
                    logger.warning(f"Error parsing Transfer event in log {log}: {e}")
                    continue
    
    if not matching_transfers:
        error_msg = f"No matching Transfer event found for token {token_address_checksum} in transaction {tx_hash}"
        if expected_to:
            error_msg += f" to recipient {expected_to}"
        if min_amount:
            error_msg += f" with minimum amount {min_amount}"
        raise ValueError(error_msg)
    
    # Use the first matching transfer
    parsed = matching_transfers[0] if len(matching_transfers) == 1 else {
        'from': matching_transfers[0]['from'],
        'to': matching_transfers[0]['to'],
        'value': sum(t['value'] for t in matching_transfers),
        'transfers_count': len(matching_transfers),
    }
    
    logger.info(f"Successfully verified ERC20 payment: {tx_hash}, token: {token_address_checksum}")
    
    result = {
        'receipt': {
            'blockNumber': receipt['blockNumber'],
            'status': receipt['status'],
            'gasUsed': receipt['gasUsed'],
            'blockHash': receipt['blockHash'].hex() if receipt['blockHash'] else None,
            'transactionIndex': receipt['transactionIndex'],
        },
        'parsed': parsed,
        'verified': True,
        'network': 'Cronos',
        'payment_type': 'ERC20',
        'token_address': token_address_checksum,
        'gasUsed': receipt['gasUsed'],
    }
    
    # Cache the result
    cache_key = _get_cache_key(tx_hash, token_address)
    _set_cache(cache_key, result)
    
    return result


# ==================== Batch Verification Functions ====================

async def verify_payments_batch(
    requests: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Verify multiple payments in batch
    
    Args:
        requests: List of payment verification requests, each containing:
            - tx_hash: Transaction hash
            - token_address: Optional token address (for ERC20)
            - expected_recipient: Optional expected recipient
            - min_amount_wei: Optional minimum amount
    
    Returns:
        List of verification results with 'success' and 'result'/'error' keys
    """
    results = []
    
    for request in requests:
        tx_hash = request.get('tx_hash')
        token_address = request.get('token_address')
        expected_recipient = request.get('expected_recipient')
        min_amount_wei = request.get('min_amount_wei')
        
        if not tx_hash:
            results.append({
                'success': False,
                'error': 'Missing tx_hash',
                'tx_hash': tx_hash,
            })
            continue
        
        # Check cache first
        cache_key = _get_cache_key(tx_hash, token_address)
        cached_result = _get_from_cache(cache_key)
        
        if cached_result:
            # Still need to validate against expected parameters if provided
            if expected_recipient or min_amount_wei is not None:
                try:
                    # Re-verify with parameters
                    if token_address:
                        result = await verify_erc20_payment(
                            tx_hash=tx_hash,
                            token_address=token_address,
                            expected_to=expected_recipient,
                            min_amount=int(min_amount_wei) if min_amount_wei else None
                        )
                    else:
                        result = await verify_native_payment(
                            tx_hash=tx_hash,
                            expected_recipient=expected_recipient,
                            min_value_wei=int(min_amount_wei) if min_amount_wei else None
                        )
                    results.append({
                        'success': True,
                        'result': result,
                        'tx_hash': tx_hash,
                        'cached': True,
                    })
                except ValueError as e:
                    results.append({
                        'success': False,
                        'error': str(e),
                        'tx_hash': tx_hash,
                    })
            else:
                # Use cached result directly
                results.append({
                    'success': True,
                    'result': cached_result,
                    'tx_hash': tx_hash,
                    'cached': True,
                })
        else:
            # Not in cache, verify
            try:
                if token_address:
                    result = await verify_erc20_payment(
                        tx_hash=tx_hash,
                        token_address=token_address,
                        expected_to=expected_recipient,
                        min_amount=int(min_amount_wei) if min_amount_wei else None
                    )
                else:
                    result = await verify_native_payment(
                        tx_hash=tx_hash,
                        expected_recipient=expected_recipient,
                        min_value_wei=int(min_amount_wei) if min_amount_wei else None
                    )
                results.append({
                    'success': True,
                    'result': result,
                    'tx_hash': tx_hash,
                    'cached': False,
                })
            except Exception as e:
                logger.error(f"Batch verification failed for {tx_hash}: {e}")
                results.append({
                    'success': False,
                    'error': str(e),
                    'tx_hash': tx_hash,
                })
    
    return results
