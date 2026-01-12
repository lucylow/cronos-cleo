"""
Payment verification utilities
"""
import logging
from typing import Optional
from web3 import Web3
from web3.types import HexStr
from gas_utils import get_provider

logger = logging.getLogger(__name__)


async def verify_native_payment(
    tx_hash: str,
    expected_recipient: Optional[str] = None,
    min_value_wei: Optional[int] = None
) -> dict:
    """
    Verify native (CRO) payment transaction
    
    Args:
        tx_hash: Transaction hash
        expected_recipient: Expected recipient address (optional)
        min_value_wei: Minimum value in Wei (optional)
    
    Returns:
        {'receipt': dict, 'tx': dict}
    """
    provider = get_provider()
    
    receipt = provider.eth.get_transaction_receipt(HexStr(tx_hash))
    if not receipt:
        raise ValueError("Transaction not found")
    
    if receipt['status'] != 1:
        raise ValueError("Transaction failed")
    
    tx = provider.eth.get_transaction(HexStr(tx_hash))
    if not tx:
        raise ValueError("Transaction object not found")
    
    # Verify recipient
    if expected_recipient:
        if tx['to'] and tx['to'].lower() != expected_recipient.lower():
            raise ValueError("Recipient mismatch")
    
    # Verify value
    if min_value_wei is not None:
        if tx['value'] < min_value_wei:
            raise ValueError("Value too low")
    
    return {
        'receipt': {
            'blockNumber': receipt['blockNumber'],
            'status': receipt['status'],
            'gasUsed': receipt['gasUsed'],
        },
        'tx': {
            'to': tx['to'],
            'value': tx['value'],
            'from': tx['from'],
        }
    }


async def verify_erc20_payment(
    tx_hash: str,
    token_address: str,
    expected_to: Optional[str] = None,
    min_amount: Optional[int] = None
) -> dict:
    """
    Verify ERC20 token payment by checking Transfer event logs
    
    Args:
        tx_hash: Transaction hash
        token_address: ERC20 token contract address
        expected_to: Expected recipient address (optional)
        min_amount: Minimum amount in token units (optional)
    
    Returns:
        {'receipt': dict, 'parsed': dict}
    """
    provider = get_provider()
    
    receipt = provider.eth.get_transaction_receipt(HexStr(tx_hash))
    if not receipt:
        raise ValueError("Transaction not found")
    
    if receipt['status'] != 1:
        raise ValueError("Transaction failed")
    
    # ERC20 Transfer event signature: Transfer(address indexed from, address indexed to, uint256 value)
    transfer_event_signature = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
    
    token_address_checksum = Web3.to_checksum_address(token_address)
    
    # Check logs for Transfer event
    for log in receipt['logs']:
        if log['address'].lower() != token_address_checksum.lower():
            continue
        
        # Check if it's a Transfer event (first topic is event signature)
        if len(log['topics']) >= 3 and log['topics'][0].hex() == transfer_event_signature:
            # Parse Transfer event
            # topics[1] = from (indexed)
            # topics[2] = to (indexed)
            # data = value (uint256)
            from_address = '0x' + log['topics'][1].hex()[-40:]
            to_address = '0x' + log['topics'][2].hex()[-40:]
            value = int.from_bytes(log['data'], 'big')
            
            # Check recipient
            if expected_to and to_address.lower() != expected_to.lower():
                continue
            
            # Check amount
            if min_amount is not None and value < min_amount:
                continue
            
            return {
                'receipt': {
                    'blockNumber': receipt['blockNumber'],
                    'status': receipt['status'],
                    'gasUsed': receipt['gasUsed'],
                },
                'parsed': {
                    'from': from_address,
                    'to': to_address,
                    'value': value,
                }
            }
    
    raise ValueError("No matching Transfer event found")
