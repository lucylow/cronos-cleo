"""
Intelligent Settlement Service
Manages escrow deals with milestone-based settlement and AI agent integration
"""
import os
import asyncio
from typing import Dict, List, Optional, Any
from web3 import Web3, AsyncWeb3
from web3.middleware import geth_poa_middleware
from eth_account import Account
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class IntelligentSettlementService:
    """
    Service for interacting with IntelligentSettlement smart contract
    Handles deal creation, funding, milestone releases, and refunds
    """
    
    def __init__(self, rpc_url: str, contract_address: str, private_key: Optional[str] = None):
        self.w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(rpc_url))
        # Add POA middleware for Cronos
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        
        self.contract_address = Web3.to_checksum_address(contract_address)
        self.account = None
        
        if private_key:
            self.account = Account.from_key(private_key)
            self.w3.eth.default_account = self.account.address
        
        # Load contract ABI
        self.contract_abi = self._load_contract_abi()
        self.contract = self.w3.eth.contract(
            address=self.contract_address,
            abi=self.contract_abi
        )
    
    def _load_contract_abi(self) -> List[Dict]:
        """Load IntelligentSettlement contract ABI"""
        return [
            {
                "inputs": [
                    {"internalType": "address", "name": "_seller", "type": "address"},
                    {"internalType": "address", "name": "_token", "type": "address"},
                    {"internalType": "uint256", "name": "_totalAmount", "type": "uint256"},
                    {"internalType": "uint256", "name": "_deadline", "type": "uint256"},
                    {"internalType": "uint256[]", "name": "_milestoneAmounts", "type": "uint256[]"},
                    {"internalType": "uint256", "name": "_feeBps", "type": "uint256"},
                    {"internalType": "address", "name": "_arbitrator", "type": "address"}
                ],
                "name": "createDeal",
                "outputs": [{"internalType": "uint256", "name": "dealId", "type": "uint256"}],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"internalType": "uint256", "name": "_dealId", "type": "uint256"},
                    {"internalType": "uint256", "name": "_amount", "type": "uint256"}
                ],
                "name": "fundDeal",
                "outputs": [],
                "stateMutability": "payable",
                "type": "function"
            },
            {
                "inputs": [
                    {"internalType": "uint256", "name": "_dealId", "type": "uint256"},
                    {"internalType": "uint256", "name": "_milestoneIndex", "type": "uint256"},
                    {"internalType": "uint256", "name": "_minSellerAmount", "type": "uint256"},
                    {"internalType": "uint256", "name": "_agentNonce", "type": "uint256"}
                ],
                "name": "agentReleaseMilestone",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"internalType": "uint256", "name": "_dealId", "type": "uint256"},
                    {"internalType": "bool", "name": "releaseToSeller", "type": "bool"}
                ],
                "name": "arbitratorResolve",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [{"internalType": "uint256", "name": "_dealId", "type": "uint256"}],
                "name": "cancelUnfundedDeal",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [{"internalType": "uint256", "name": "_dealId", "type": "uint256"}],
                "name": "refundAfterDeadline",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [{"internalType": "uint256", "name": "_dealId", "type": "uint256"}],
                "name": "getDeal",
                "outputs": [
                    {
                        "components": [
                            {"internalType": "address", "name": "buyer", "type": "address"},
                            {"internalType": "address", "name": "seller", "type": "address"},
                            {"internalType": "address", "name": "token", "type": "address"},
                            {"internalType": "uint256", "name": "totalAmount", "type": "uint256"},
                            {"internalType": "uint256", "name": "fundedAmount", "type": "uint256"},
                            {"internalType": "uint256", "name": "createdAt", "type": "uint256"},
                            {"internalType": "uint256", "name": "deadline", "type": "uint256"},
                            {"internalType": "uint256", "name": "currentMilestone", "type": "uint256"},
                            {"internalType": "uint8", "name": "status", "type": "uint8"},
                            {"internalType": "uint256", "name": "feeBps", "type": "uint256"},
                            {"internalType": "uint256", "name": "agentNonce", "type": "uint256"},
                            {"internalType": "address", "name": "arbitrator", "type": "address"}
                        ],
                        "internalType": "struct IntelligentSettlement.Deal",
                        "name": "",
                        "type": "tuple"
                    }
                ],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [{"internalType": "uint256", "name": "_dealId", "type": "uint256"}],
                "name": "getMilestones",
                "outputs": [
                    {
                        "components": [
                            {"internalType": "uint256", "name": "amount", "type": "uint256"},
                            {"internalType": "bool", "name": "completed", "type": "bool"}
                        ],
                        "internalType": "struct IntelligentSettlement.Milestone[]",
                        "name": "",
                        "type": "tuple[]"
                    }
                ],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [{"internalType": "uint256", "name": "_dealId", "type": "uint256"}],
                "name": "milestonesCount",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "authorizedAgent",
                "outputs": [{"internalType": "address", "name": "", "type": "address"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]
    
    async def create_deal(
        self,
        seller: str,
        token: str,
        total_amount: int,
        deadline: int,
        milestone_amounts: List[int],
        fee_bps: int = 25,  # 0.25% default
        arbitrator: Optional[str] = None,
        buyer_private_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new intelligent settlement deal
        
        Args:
            seller: Seller address (payment recipient)
            token: Token address (0x0 for native CRO)
            total_amount: Total amount in wei/smallest unit
            deadline: Unix timestamp deadline
            milestone_amounts: List of milestone amounts (must sum to total_amount)
            fee_bps: Protocol fee in basis points (0-500)
            arbitrator: Optional arbitrator address
            buyer_private_key: Private key for buyer (if different from service account)
        
        Returns:
            Dict with deal_id and transaction info
        """
        if not buyer_private_key and not self.account:
            raise ValueError("Buyer private key required for deal creation")
        
        account = self.account
        if buyer_private_key:
            account = Account.from_key(buyer_private_key)
        
        seller_addr = Web3.to_checksum_address(seller)
        token_addr = Web3.to_checksum_address(token) if token != "0x0" and token != "0" else "0x0000000000000000000000000000000000000000"
        arbitrator_addr = Web3.to_checksum_address(arbitrator) if arbitrator else "0x0000000000000000000000000000000000000000"
        
        try:
            function_call = self.contract.functions.createDeal(
                seller_addr,
                token_addr,
                total_amount,
                deadline,
                milestone_amounts,
                fee_bps,
                arbitrator_addr
            )
            
            # Estimate gas
            gas_estimate = await function_call.estimate_gas({'from': account.address})
            
            # Get current nonce
            nonce = await self.w3.eth.get_transaction_count(account.address)
            
            # Build transaction
            transaction = await function_call.build_transaction({
                'from': account.address,
                'nonce': nonce,
                'gas': int(gas_estimate * 1.2),
                'gasPrice': await self.w3.eth.gas_price,
                'chainId': await self.w3.eth.chain_id
            })
            
            # Sign transaction
            signed_txn = account.sign_transaction(transaction)
            
            # Send transaction
            tx_hash = await self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Wait for receipt
            receipt = await self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            # Extract deal ID from events
            deal_id = None
            if receipt.status == 1:
                deal_created_event = self.contract.events.DealCreated()
                logs = deal_created_event.process_receipt(receipt)
                if logs:
                    deal_id = logs[0].args.dealId
            
            return {
                "success": receipt.status == 1,
                "tx_hash": tx_hash.hex(),
                "deal_id": deal_id,
                "gas_used": receipt.gasUsed,
                "block_number": receipt.blockNumber
            }
        except Exception as e:
            logger.error(f"Error creating deal: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def fund_deal(
        self,
        deal_id: int,
        amount: int,
        buyer_private_key: Optional[str] = None,
        is_native: bool = False
    ) -> Dict[str, Any]:
        """
        Fund an existing deal
        
        Args:
            deal_id: Deal ID to fund
            amount: Amount to fund in wei/smallest unit
            buyer_private_key: Private key for buyer
            is_native: True if funding with native token (CRO)
        
        Returns:
            Dict with transaction info
        """
        if not buyer_private_key and not self.account:
            raise ValueError("Buyer private key required for funding")
        
        account = self.account
        if buyer_private_key:
            account = Account.from_key(buyer_private_key)
        
        try:
            function_call = self.contract.functions.fundDeal(deal_id, amount)
            
            # Estimate gas
            gas_estimate = await function_call.estimate_gas({
                'from': account.address,
                'value': amount if is_native else 0
            })
            
            # Get current nonce
            nonce = await self.w3.eth.get_transaction_count(account.address)
            
            # Build transaction
            transaction = await function_call.build_transaction({
                'from': account.address,
                'nonce': nonce,
                'gas': int(gas_estimate * 1.2),
                'gasPrice': await self.w3.eth.gas_price,
                'chainId': await self.w3.eth.chain_id,
                'value': amount if is_native else 0
            })
            
            # Sign transaction
            signed_txn = account.sign_transaction(transaction)
            
            # Send transaction
            tx_hash = await self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Wait for receipt
            receipt = await self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            return {
                "success": receipt.status == 1,
                "tx_hash": tx_hash.hex(),
                "gas_used": receipt.gasUsed,
                "block_number": receipt.blockNumber
            }
        except Exception as e:
            logger.error(f"Error funding deal: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def agent_release_milestone(
        self,
        deal_id: int,
        milestone_index: int,
        min_seller_amount: int,
        agent_nonce: int
    ) -> Dict[str, Any]:
        """
        Release a milestone (called by authorized agent/AI)
        
        Args:
            deal_id: Deal ID
            milestone_index: Index of milestone to release
            min_seller_amount: Minimum amount to seller (slippage protection)
            agent_nonce: Monotonic nonce for this deal
        
        Returns:
            Dict with transaction info
        """
        if not self.account:
            raise ValueError("Agent account required for milestone release")
        
        try:
            function_call = self.contract.functions.agentReleaseMilestone(
                deal_id,
                milestone_index,
                min_seller_amount,
                agent_nonce
            )
            
            # Estimate gas
            gas_estimate = await function_call.estimate_gas({'from': self.account.address})
            
            # Get current nonce
            nonce = await self.w3.eth.get_transaction_count(self.account.address)
            
            # Build transaction
            transaction = await function_call.build_transaction({
                'from': self.account.address,
                'nonce': nonce,
                'gas': int(gas_estimate * 1.2),
                'gasPrice': await self.w3.eth.gas_price,
                'chainId': await self.w3.eth.chain_id
            })
            
            # Sign transaction
            signed_txn = self.account.sign_transaction(transaction)
            
            # Send transaction
            tx_hash = await self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Wait for receipt
            receipt = await self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            return {
                "success": receipt.status == 1,
                "tx_hash": tx_hash.hex(),
                "gas_used": receipt.gasUsed,
                "block_number": receipt.blockNumber
            }
        except Exception as e:
            logger.error(f"Error releasing milestone: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_deal(self, deal_id: int) -> Dict[str, Any]:
        """Get deal information"""
        try:
            deal = await self.contract.functions.getDeal(deal_id).call()
            milestones = await self.contract.functions.getMilestones(deal_id).call()
            
            # Convert status enum to string
            status_map = {
                0: "PendingFunding",
                1: "Active",
                2: "Completed",
                3: "Refunded",
                4: "Cancelled"
            }
            
            return {
                "deal_id": deal_id,
                "buyer": deal[0],
                "seller": deal[1],
                "token": deal[2],
                "total_amount": deal[3],
                "funded_amount": deal[4],
                "created_at": deal[5],
                "deadline": deal[6],
                "current_milestone": deal[7],
                "status": status_map.get(deal[8], "Unknown"),
                "fee_bps": deal[9],
                "agent_nonce": deal[10],
                "arbitrator": deal[11],
                "milestones": [
                    {
                        "amount": m[0],
                        "completed": m[1]
                    }
                    for m in milestones
                ]
            }
        except Exception as e:
            logger.error(f"Error getting deal: {e}", exc_info=True)
            return {
                "error": str(e),
                "deal_id": deal_id
            }
    
    async def refund_after_deadline(
        self,
        deal_id: int,
        buyer_private_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Refund remaining funds after deadline (buyer-initiated)
        
        Args:
            deal_id: Deal ID to refund
            buyer_private_key: Private key for buyer
        
        Returns:
            Dict with transaction info
        """
        if not buyer_private_key and not self.account:
            raise ValueError("Buyer private key required for refund")
        
        account = self.account
        if buyer_private_key:
            account = Account.from_key(buyer_private_key)
        
        try:
            function_call = self.contract.functions.refundAfterDeadline(deal_id)
            
            # Estimate gas
            gas_estimate = await function_call.estimate_gas({'from': account.address})
            
            # Get current nonce
            nonce = await self.w3.eth.get_transaction_count(account.address)
            
            # Build transaction
            transaction = await function_call.build_transaction({
                'from': account.address,
                'nonce': nonce,
                'gas': int(gas_estimate * 1.2),
                'gasPrice': await self.w3.eth.gas_price,
                'chainId': await self.w3.eth.chain_id
            })
            
            # Sign transaction
            signed_txn = account.sign_transaction(transaction)
            
            # Send transaction
            tx_hash = await self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Wait for receipt
            receipt = await self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            return {
                "success": receipt.status == 1,
                "tx_hash": tx_hash.hex(),
                "gas_used": receipt.gasUsed,
                "block_number": receipt.blockNumber
            }
        except Exception as e:
            logger.error(f"Error refunding deal: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def check_authorized_agent(self) -> str:
        """Check the authorized agent address"""
        try:
            agent_address = await self.contract.functions.authorizedAgent().call()
            return agent_address
        except Exception as e:
            logger.error(f"Error checking authorized agent: {e}")
            return ""
