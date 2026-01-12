"""
DAO Executor
Handles interactions with the SimpleDAO smart contract
"""
import os
from typing import Dict, List, Optional, Any
from web3 import Web3, AsyncWeb3
from web3.middleware import geth_poa_middleware
from eth_account import Account
import json


class DAOExecutor:
    """
    Handles DAO operations: proposals, voting, execution
    """
    
    def __init__(self, rpc_url: str, dao_contract_address: str, private_key: Optional[str] = None):
        self.w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(rpc_url))
        # Add POA middleware for Cronos
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        
        self.dao_address = dao_contract_address
        self.account = None
        
        if private_key:
            self.account = Account.from_key(private_key)
            self.w3.eth.default_account = self.account.address
        
        # Load contract ABIs
        self.dao_abi = self._load_dao_abi()
        self.token_abi = self._load_token_abi()
        self.treasury_abi = self._load_treasury_abi()
        
        self.dao_contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(dao_contract_address),
            abi=self.dao_abi
        ) if dao_contract_address else None
        
        # Get token and treasury addresses
        if self.dao_contract:
            self.token_address = None
            self.treasury_address = None
    
    def _load_dao_abi(self) -> List[Dict]:
        """Load SimpleDAO contract ABI"""
        return [
            {
                "inputs": [
                    {"internalType": "address payable", "name": "recipient", "type": "address"},
                    {"internalType": "uint256", "name": "amount", "type": "uint256"},
                    {"internalType": "string", "name": "description", "type": "string"}
                ],
                "name": "proposeTreasuryETHTransfer",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"internalType": "address", "name": "token", "type": "address"},
                    {"internalType": "address", "name": "recipient", "type": "address"},
                    {"internalType": "uint256", "name": "amount", "type": "uint256"},
                    {"internalType": "string", "name": "description", "type": "string"}
                ],
                "name": "proposeTreasuryERC20Transfer",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"internalType": "address", "name": "target", "type": "address"},
                    {"internalType": "uint256", "name": "value", "type": "uint256"},
                    {"internalType": "bytes", "name": "callData", "type": "bytes"},
                    {"internalType": "string", "name": "description", "type": "string"}
                ],
                "name": "proposeArbitraryCall",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"internalType": "uint256", "name": "proposalId", "type": "uint256"},
                    {"internalType": "uint8", "name": "support", "type": "uint8"}
                ],
                "name": "vote",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [{"internalType": "uint256", "name": "proposalId", "type": "uint256"}],
                "name": "finalizeProposal",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [{"internalType": "uint256", "name": "proposalId", "type": "uint256"}],
                "name": "execute",
                "outputs": [],
                "stateMutability": "payable",
                "type": "function"
            },
            {
                "inputs": [{"internalType": "uint256", "name": "proposalId", "type": "uint256"}],
                "name": "getProposal",
                "outputs": [
                    {
                        "components": [
                            {"internalType": "uint256", "name": "id", "type": "uint256"},
                            {"internalType": "address", "name": "proposer", "type": "address"},
                            {"internalType": "uint256", "name": "startTime", "type": "uint256"},
                            {"internalType": "uint256", "name": "endTime", "type": "uint256"},
                            {"internalType": "uint256", "name": "forVotes", "type": "uint256"},
                            {"internalType": "uint256", "name": "againstVotes", "type": "uint256"},
                            {"internalType": "uint256", "name": "abstainVotes", "type": "uint256"},
                            {"internalType": "uint8", "name": "status", "type": "uint8"},
                            {"internalType": "uint8", "name": "pType", "type": "uint8"},
                            {"internalType": "address", "name": "target", "type": "address"},
                            {"internalType": "uint256", "name": "value", "type": "uint256"},
                            {"internalType": "address", "name": "token", "type": "address"},
                            {"internalType": "address", "name": "recipient", "type": "address"},
                            {"internalType": "bytes", "name": "callData", "type": "bytes"},
                            {"internalType": "string", "name": "description", "type": "string"}
                        ],
                        "internalType": "struct SimpleDAO.Proposal",
                        "name": "",
                        "type": "tuple"
                    }
                ],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [{"internalType": "uint256", "name": "proposalId", "type": "uint256"}],
                "name": "state",
                "outputs": [{"internalType": "uint8", "name": "", "type": "uint8"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "governanceToken",
                "outputs": [{"internalType": "address", "name": "", "type": "address"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "treasury",
                "outputs": [{"internalType": "address", "name": "", "type": "address"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "quorumPercentage",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "proposalThreshold",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "votingPeriod",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [
                    {"internalType": "uint256", "name": "proposalId", "type": "uint256"},
                    {"internalType": "address", "name": "voter", "type": "address"}
                ],
                "name": "hasVoted",
                "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [
                    {"internalType": "address", "name": "to", "type": "address"},
                    {"internalType": "uint256", "name": "amount", "type": "uint256"}
                ],
                "name": "mintGovToken",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            }
        ]
    
    def _load_token_abi(self) -> List[Dict]:
        """Load GovernanceToken ABI"""
        return [
            {
                "inputs": [{"internalType": "address", "name": "account", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "totalSupply",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "name",
                "outputs": [{"internalType": "string", "name": "", "type": "string"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "symbol",
                "outputs": [{"internalType": "string", "name": "", "type": "string"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]
    
    def _load_treasury_abi(self) -> List[Dict]:
        """Load Treasury ABI"""
        return [
            {
                "inputs": [],
                "name": "dao",
                "outputs": [{"internalType": "address", "name": "", "type": "address"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]
    
    async def get_dao_info(self) -> Dict[str, Any]:
        """Get DAO configuration and addresses"""
        if not self.dao_contract:
            raise ValueError("DAO contract not initialized")
        
        token_address = await self.dao_contract.functions.governanceToken().call()
        treasury_address = await self.dao_contract.functions.treasury().call()
        quorum = await self.dao_contract.functions.quorumPercentage().call()
        threshold = await self.dao_contract.functions.proposalThreshold().call()
        voting_period = await self.dao_contract.functions.votingPeriod().call()
        
        return {
            "dao_address": self.dao_address,
            "token_address": token_address,
            "treasury_address": treasury_address,
            "quorum_percentage": quorum,
            "proposal_threshold": str(threshold),
            "voting_period_seconds": voting_period
        }
    
    async def get_proposal(self, proposal_id: int) -> Dict[str, Any]:
        """Get proposal details"""
        if not self.dao_contract:
            raise ValueError("DAO contract not initialized")
        
        proposal = await self.dao_contract.functions.getProposal(proposal_id).call()
        status = await self.dao_contract.functions.state(proposal_id).call()
        
        return {
            "id": proposal[0],
            "proposer": proposal[1],
            "start_time": proposal[2],
            "end_time": proposal[3],
            "for_votes": str(proposal[4]),
            "against_votes": str(proposal[5]),
            "abstain_votes": str(proposal[6]),
            "status": status,
            "proposal_type": proposal[8],
            "target": proposal[9],
            "value": str(proposal[10]),
            "token": proposal[11],
            "recipient": proposal[12],
            "call_data": proposal[13].hex() if proposal[13] else "",
            "description": proposal[14]
        }
    
    async def get_user_voting_power(self, user_address: str) -> Dict[str, Any]:
        """Get user's voting power and token balance"""
        if not self.dao_contract:
            raise ValueError("DAO contract not initialized")
        
        token_address = await self.dao_contract.functions.governanceToken().call()
        token_contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(token_address),
            abi=self.token_abi
        )
        
        balance = await token_contract.functions.balanceOf(
            Web3.to_checksum_address(user_address)
        ).call()
        threshold = await self.dao_contract.functions.proposalThreshold().call()
        total_supply = await token_contract.functions.totalSupply().call()
        
        return {
            "balance": str(balance),
            "can_propose": balance >= threshold,
            "proposal_threshold": str(threshold),
            "total_supply": str(total_supply)
        }
    
    async def create_proposal_eth_transfer(
        self,
        recipient: str,
        amount: str,
        description: str,
        private_key: str
    ) -> Dict[str, Any]:
        """Create a proposal to transfer ETH from treasury"""
        if not self.dao_contract:
            raise ValueError("DAO contract not initialized")
        
        account = Account.from_key(private_key)
        amount_wei = int(amount)
        
        tx = await self.dao_contract.functions.proposeTreasuryETHTransfer(
            Web3.to_checksum_address(recipient),
            amount_wei,
            description
        ).build_transaction({
            'from': account.address,
            'gas': 500000,
            'gasPrice': await self.w3.eth.gas_price,
            'nonce': await self.w3.eth.get_transaction_count(account.address)
        })
        
        signed_tx = account.sign_transaction(tx)
        tx_hash = await self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        receipt = await self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        
        # Extract proposal ID from events
        proposal_id = None
        if receipt.status == 1:
            # Parse ProposalCreated event
            logs = self.dao_contract.events.ProposalCreated().process_receipt(receipt)
            if logs:
                proposal_id = logs[0]['args']['id']
        
        return {
            "tx_hash": tx_hash.hex(),
            "proposal_id": proposal_id,
            "status": "success" if receipt.status == 1 else "failed"
        }
    
    async def vote_on_proposal(
        self,
        proposal_id: int,
        support: int,  # 0 = Against, 1 = For, 2 = Abstain
        private_key: str
    ) -> Dict[str, Any]:
        """Vote on a proposal"""
        if not self.dao_contract:
            raise ValueError("DAO contract not initialized")
        
        if support not in [0, 1, 2]:
            raise ValueError("Support must be 0 (Against), 1 (For), or 2 (Abstain)")
        
        account = Account.from_key(private_key)
        
        tx = await self.dao_contract.functions.vote(proposal_id, support).build_transaction({
            'from': account.address,
            'gas': 200000,
            'gasPrice': await self.w3.eth.gas_price,
            'nonce': await self.w3.eth.get_transaction_count(account.address)
        })
        
        signed_tx = account.sign_transaction(tx)
        tx_hash = await self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        receipt = await self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        
        return {
            "tx_hash": tx_hash.hex(),
            "status": "success" if receipt.status == 1 else "failed"
        }
    
    async def execute_proposal(
        self,
        proposal_id: int,
        private_key: str
    ) -> Dict[str, Any]:
        """Execute a succeeded proposal"""
        if not self.dao_contract:
            raise ValueError("DAO contract not initialized")
        
        account = Account.from_key(private_key)
        
        tx = await self.dao_contract.functions.execute(proposal_id).build_transaction({
            'from': account.address,
            'gas': 500000,
            'gasPrice': await self.w3.eth.gas_price,
            'nonce': await self.w3.eth.get_transaction_count(account.address),
            'value': 0
        })
        
        signed_tx = account.sign_transaction(tx)
        tx_hash = await self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        receipt = await self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        
        return {
            "tx_hash": tx_hash.hex(),
            "status": "success" if receipt.status == 1 else "failed"
        }
    
    async def finalize_proposal(
        self,
        proposal_id: int,
        private_key: str
    ) -> Dict[str, Any]:
        """Finalize a proposal after voting period ends"""
        if not self.dao_contract:
            raise ValueError("DAO contract not initialized")
        
        account = Account.from_key(private_key)
        
        tx = await self.dao_contract.functions.finalizeProposal(proposal_id).build_transaction({
            'from': account.address,
            'gas': 100000,
            'gasPrice': await self.w3.eth.gas_price,
            'nonce': await self.w3.eth.get_transaction_count(account.address)
        })
        
        signed_tx = account.sign_transaction(tx)
        tx_hash = await self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        receipt = await self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        
        return {
            "tx_hash": tx_hash.hex(),
            "status": "success" if receipt.status == 1 else "failed"
        }
