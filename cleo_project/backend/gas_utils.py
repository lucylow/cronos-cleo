"""
Gas utilities for Cronos - handles EIP-1559 and legacy gas price recommendations
"""
import os
import logging
from typing import Optional, Dict, Any
from web3 import Web3
from web3.types import Wei, TxParams
import aiohttp

logger = logging.getLogger(__name__)

# Get RPC URL from environment
CRONOS_RPC = os.getenv("CRONOS_RPC", "https://evm-t3.cronos.org")

# Global provider instance (will be initialized on first use)
_provider: Optional[Web3] = None


def get_provider() -> Web3:
    """Get or create Web3 provider instance"""
    global _provider
    if _provider is None:
        _provider = Web3(Web3.HTTPProvider(CRONOS_RPC))
    return _provider


def to_gwei_string(value: Optional[Wei]) -> Optional[str]:
    """Convert Wei to Gwei string"""
    if value is None:
        return None
    return str(Web3.from_wei(value, 'gwei'))


async def fetch_third_party_gas() -> Optional[Dict[str, Any]]:
    """
    Fetch gas recommendations from third-party APIs (optional fallback)
    You can integrate QuickNode, Owlracle, or other gas oracles here
    """
    try:
        # Example placeholder - replace with your chosen service & API key
        # async with aiohttp.ClientSession() as session:
        #     async with session.get('https://some-gas-api.example.com/gas?chain=cronos') as resp:
        #         if resp.status == 200:
        #             data = await resp.json()
        #             return {
        #                 'maxFeePerGas': Web3.to_wei(data.get('fast', 1), 'gwei'),
        #                 'maxPriorityFeePerGas': Web3.to_wei(data.get('fast', 1), 'gwei'),
        #             }
        return None
    except Exception as e:
        logger.debug(f"Third-party gas API failed: {e}")
        return None


async def get_gas_recommendation() -> Dict[str, Any]:
    """
    Get gas recommendation for Cronos
    - Prefers EIP-1559 fields (maxFeePerGas, maxPriorityFeePerGas) if chain supports it
    - Falls back to legacy gasPrice
    - Last resort: safe defaults
    
    Returns:
        {
            'supports1559': bool,
            'maxFeePerGas': Wei (optional),
            'maxPriorityFeePerGas': Wei (optional),
            'legacyGasPrice': Wei (optional),
            'source': str
        }
    """
    provider = get_provider()
    
    try:
        # 1) Try to get fee data (EIP-1559 style)
        # Note: web3.py doesn't have a direct getFeeData() like ethers.js
        # We'll check the latest block to see if it has baseFeePerGas
        latest_block = provider.eth.get_block('latest')
        
        # Check if block has baseFeePerGas (indicates EIP-1559 support)
        if hasattr(latest_block, 'baseFeePerGas') and latest_block.baseFeePerGas is not None:
            base_fee = latest_block.baseFeePerGas
            
            # Get current gas price as a reference for priority fee
            current_gas_price = provider.eth.gas_price
            
            # Estimate priority fee (typically 1-2 gwei on Cronos)
            # You can adjust this based on network conditions
            priority_fee = Web3.to_wei(1, 'gwei')  # Default 1 gwei priority
            
            # maxFeePerGas = baseFee + priorityFee (with some margin)
            max_fee_per_gas = base_fee + priority_fee + Web3.to_wei(1, 'gwei')  # Add 1 gwei margin
            
            return {
                'supports1559': True,
                'maxFeePerGas': max_fee_per_gas,
                'maxPriorityFeePerGas': priority_fee,
                'legacyGasPrice': None,
                'source': 'provider.block.baseFeePerGas'
            }
        
        # 2) Fallback to legacy gasPrice
        gas_price = provider.eth.gas_price
        if gas_price:
            return {
                'supports1559': False,
                'maxFeePerGas': None,
                'maxPriorityFeePerGas': None,
                'legacyGasPrice': gas_price,
                'source': 'provider.gas_price'
            }
    except Exception as e:
        logger.warning(f"Provider gas recommendation failed: {e}")
    
    # 3) Third-party fallback
    third_party = await fetch_third_party_gas()
    if third_party:
        return {
            'supports1559': bool(third_party.get('maxFeePerGas')),
            'maxFeePerGas': third_party.get('maxFeePerGas'),
            'maxPriorityFeePerGas': third_party.get('maxPriorityFeePerGas'),
            'legacyGasPrice': third_party.get('legacyGasPrice'),
            'source': 'third-party'
        }
    
    # 4) Ultimate fallback: safe defaults
    return {
        'supports1559': True,
        'maxFeePerGas': Web3.to_wei(1, 'gwei'),
        'maxPriorityFeePerGas': Web3.to_wei(1, 'gwei'),
        'legacyGasPrice': None,
        'source': 'fallback-defaults'
    }
