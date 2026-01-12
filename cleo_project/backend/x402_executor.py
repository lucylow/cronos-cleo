"""
x402 Execution Orchestrator
Connects AI agent optimization results with smart contract execution
"""
import os
import asyncio
from typing import Dict, List, Optional, Any
from web3 import Web3, AsyncWeb3
from web3.middleware import geth_poa_middleware
from eth_account import Account
from eth_abi import encode, decode
import json

# Try to import facilitator client SDK
try:
    from facilitator_client import FacilitatorClient
    HAS_FACILITATOR_SDK = True
except ImportError:
    HAS_FACILITATOR_SDK = False
    print("Warning: Facilitator SDK not found, using mock implementation")


class X402Executor:
    """
    Orchestrates execution of optimized routes through x402 facilitator
    """
    
    def __init__(self, rpc_url: str, router_contract_address: str, private_key: Optional[str] = None):
        self.w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(rpc_url))
        # Add POA middleware for Cronos
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        
        self.router_address = router_contract_address
        self.account = None
        
        if private_key:
            self.account = Account.from_key(private_key)
            self.w3.eth.default_account = self.account.address
        
        # Load contract ABI (simplified)
        self.router_abi = self._load_router_abi()
        self.router_contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(router_contract_address),
            abi=self.router_abi
        ) if router_contract_address else None
        
        # Initialize facilitator client if available
        self.facilitator_client = None
        if HAS_FACILITATOR_SDK:
            try:
                facilitator_url = os.getenv("X402_FACILITATOR_URL", "https://facilitator.cronos.org")
                self.facilitator_client = FacilitatorClient(facilitator_url)
            except Exception as e:
                print(f"Warning: Could not initialize facilitator client: {e}")
    
    def _load_router_abi(self) -> List[Dict]:
        """Load router contract ABI"""
        # Simplified ABI for key functions
        return [
            {
                "inputs": [
                    {
                        "components": [
                            {"internalType": "string", "name": "dexId", "type": "string"},
                            {"internalType": "address[]", "name": "path", "type": "address[]"},
                            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                            {"internalType": "uint256", "name": "minAmountOut", "type": "uint256"}
                        ],
                        "internalType": "struct CrossDEXRouter.RouteSplit[]",
                        "name": "routes",
                        "type": "tuple[]"
                    },
                    {"internalType": "uint256", "name": "totalAmountIn", "type": "uint256"},
                    {"internalType": "address", "name": "tokenIn", "type": "address"},
                    {"internalType": "address", "name": "tokenOut", "type": "address"},
                    {"internalType": "uint256", "name": "minTotalOut", "type": "uint256"},
                    {"internalType": "uint256", "name": "deadline", "type": "uint256"}
                ],
                "name": "executeOptimizedSwap",
                "outputs": [{"internalType": "bytes32", "name": "orderId", "type": "bytes32"}],
                "stateMutability": "payable",
                "type": "function"
            },
            {
                "inputs": [{"internalType": "bytes32", "name": "orderId", "type": "bytes32"}],
                "name": "getOrder",
                "outputs": [
                    {
                        "components": [
                            {"internalType": "address", "name": "user", "type": "address"},
                            {"internalType": "address", "name": "tokenIn", "type": "address"},
                            {"internalType": "address", "name": "tokenOut", "type": "address"},
                            {"internalType": "uint256", "name": "totalAmountIn", "type": "uint256"},
                            {"internalType": "uint256", "name": "minTotalOut", "type": "uint256"},
                            {"internalType": "uint256", "name": "deadline", "type": "uint256"},
                            {"internalType": "bytes32", "name": "orderId", "type": "bytes32"},
                            {"internalType": "bool", "name": "executed", "type": "bool"},
                            {"internalType": "uint256", "name": "totalReceived", "type": "uint256"}
                        ],
                        "internalType": "struct CrossDEXRouter.SplitOrder",
                        "name": "",
                        "type": "tuple"
                    },
                    {
                        "components": [
                            {"internalType": "string", "name": "dexId", "type": "string"},
                            {"internalType": "address[]", "name": "path", "type": "address[]"},
                            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                            {"internalType": "uint256", "name": "minAmountOut", "type": "uint256"}
                        ],
                        "internalType": "struct CrossDEXRouter.RouteSplit[]",
                        "name": "",
                        "type": "tuple[]"
                    }
                ],
                "stateMutability": "view",
                "type": "function"
            }
        ]
    
    async def prepare_route_splits(
        self,
        optimized_split: Dict,
        token_in_address: str,
        token_out_address: str
    ) -> List[Dict]:
        """
        Convert AI agent optimization result to contract RouteSplit format
        
        Args:
            optimized_split: Result from AI agent's optimize_split
            token_in_address: Input token contract address
            token_out_address: Output token contract address
            
        Returns:
            List of RouteSplit dictionaries ready for contract call
        """
        routes = []
        splits = optimized_split.get("splits", [])
        
        # Token address mapping (common Cronos tokens)
        token_addresses = {
            "CRO": "0x5C7F8A570d578ED84E63fdFA7b1eE72dEae1AE23",  # Native CRO (wrapped)
            "USDC.e": "0xc21223249CA28397B4B6541dfFaEcC539BfF0c59",
            "USDC": "0xc21223249CA28397B4B6541dfFaEcC539BfF0c59",
            "USDT": "0x66e428c3f67a68878562e79A0234c1F83c208770",
        }
        
        # Resolve token addresses
        token_in_addr = token_addresses.get(token_in_address, token_in_address)
        token_out_addr = token_addresses.get(token_out_address, token_out_address)
        
        for split in splits:
            dex_id = split.get("dex", "").lower().replace(" ", "_")
            amount_in = int(float(split.get("amount", 0)) * 1e18)  # Assuming 18 decimals
            predicted_out = float(split.get("predicted_output", 0))
            
            # Calculate minimum output with slippage buffer (0.5% buffer)
            min_amount_out = int(predicted_out * 0.995 * 1e18)
            
            # Build path (direct swap for now, can be extended for multi-hop)
            path = [
                Web3.to_checksum_address(token_in_addr),
                Web3.to_checksum_address(token_out_addr)
            ]
            
            routes.append({
                "dexId": dex_id,
                "path": path,
                "amountIn": amount_in,
                "minAmountOut": min_amount_out
            })
        
        return routes
    
    async def execute_swap(
        self,
        routes: List[Dict],
        total_amount_in: float,
        token_in: str,
        token_out: str,
        min_total_out: float,
        max_slippage: float = 0.005
    ) -> Dict[str, Any]:
        """
        Execute optimized swap through x402-enabled router contract
        
        Args:
            routes: List of RouteSplit dictionaries
            total_amount_in: Total input amount (in token units)
            token_in: Input token symbol or address
            token_out: Output token symbol or address
            min_total_out: Minimum expected output
            max_slippage: Maximum acceptable slippage (default 0.5%)
            
        Returns:
            Execution result with transaction hash and order ID
        """
        if not self.account:
            raise ValueError("No account configured for execution")
        
        if not self.router_contract:
            raise ValueError("Router contract not initialized")
        
        # Prepare contract parameters
        token_addresses = {
            "CRO": "0x5C7F8A570d578ED84E63fdFA7b1eE72dEae1AE23",
            "USDC.e": "0xc21223249CA28397B4B6541dfFaEcC539BfF0c59",
            "USDC": "0xc21223249CA28397B4B6541dfFaEcC539BfF0c59",
        }
        
        token_in_addr = Web3.to_checksum_address(
            token_addresses.get(token_in, token_in)
        )
        token_out_addr = Web3.to_checksum_address(
            token_addresses.get(token_out, token_out)
        )
        
        # Convert amounts to wei (assuming 18 decimals)
        total_amount_wei = int(total_amount_in * 1e18)
        min_total_out_wei = int(min_total_out * (1 - max_slippage) * 1e18)
        
        # Set deadline (30 minutes from now)
        deadline = int(asyncio.get_event_loop().time()) + 1800
        
        try:
            # Build transaction
            function_call = self.router_contract.functions.executeOptimizedSwap(
                routes,
                total_amount_wei,
                token_in_addr,
                token_out_addr,
                min_total_out_wei,
                deadline
            )
            
            # Estimate gas
            gas_estimate = await function_call.estimate_gas({'from': self.account.address})
            
            # Get current nonce
            nonce = await self.w3.eth.get_transaction_count(self.account.address)
            
            # Build transaction
            transaction = await function_call.build_transaction({
                'from': self.account.address,
                'nonce': nonce,
                'gas': int(gas_estimate * 1.2),  # 20% buffer
                'gasPrice': await self.w3.eth.gas_price,
                'chainId': await self.w3.eth.chain_id
            })
            
            # Sign transaction
            signed_txn = self.account.sign_transaction(transaction)
            
            # Send transaction
            tx_hash = await self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Wait for receipt
            receipt = await self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            # Extract order ID from events
            order_id = None
            if receipt.status == 1:
                # Parse OrderCreated event
                order_created_event = self.router_contract.events.OrderCreated()
                logs = order_created_event.process_receipt(receipt)
                if logs:
                    order_id = logs[0].args.orderId.hex()
            
            return {
                "success": receipt.status == 1,
                "tx_hash": tx_hash.hex(),
                "order_id": order_id,
                "gas_used": receipt.gasUsed,
                "block_number": receipt.blockNumber,
                "status": "executed" if receipt.status == 1 else "failed"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "status": "failed"
            }
    
    async def check_order_status(self, order_id: str) -> Dict[str, Any]:
        """Check status of an executed order"""
        if not self.router_contract:
            raise ValueError("Router contract not initialized")
        
        try:
            order_id_bytes = bytes.fromhex(order_id.replace('0x', ''))
            result = await self.router_contract.functions.getOrder(order_id_bytes).call()
            
            order, routes = result
            
            return {
                "order_id": order_id,
                "executed": order[7],  # executed field
                "total_received": order[8],  # totalReceived field
                "user": order[0],
                "token_in": order[1],
                "token_out": order[2],
                "total_amount_in": order[3],
                "min_total_out": order[4],
                "deadline": order[5],
                "route_count": len(routes)
            }
        except Exception as e:
            return {
                "error": str(e),
                "order_id": order_id
            }
    
    async def simulate_execution(
        self,
        routes: List[Dict],
        total_amount_in: float,
        token_in: str,
        token_out: str
    ) -> Dict[str, Any]:
        """
        Simulate execution without actually sending transaction
        Useful for pre-execution validation
        """
        if not self.router_contract:
            raise ValueError("Router contract not initialized")
        
        # This would use a forked network or static call
        # For now, return estimated results
        total_estimated_out = sum(
            float(r.get("minAmountOut", 0)) / 1e18 for r in routes
        )
        
        estimated_slippage = abs(
            (total_estimated_out / total_amount_in - 1) * 100
        ) if total_amount_in > 0 else 0
        
        return {
            "total_in": total_amount_in,
            "estimated_out": total_estimated_out,
            "estimated_slippage_pct": estimated_slippage,
            "route_count": len(routes),
            "simulation": True
        }

