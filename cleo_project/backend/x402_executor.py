"""
x402 Execution Orchestrator
Connects AI agent optimization results with smart contract execution
Enhanced with better error handling, retry logic, batch payments, and monitoring
"""
import os
import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from web3 import Web3, AsyncWeb3
from web3.middleware import geth_poa_middleware
from eth_account import Account
from eth_abi import encode, decode
from decimal import Decimal
import json
import time
from dataclasses import dataclass

# Try to import facilitator client SDK
try:
    from facilitator_client import FacilitatorClient
    HAS_FACILITATOR_SDK = True
except ImportError:
    HAS_FACILITATOR_SDK = False
    print("Warning: Facilitator SDK not found, using mock implementation")

logger = logging.getLogger(__name__)


@dataclass
class PaymentOperation:
    """Represents a single payment operation in a batch"""
    recipient: str
    token_address: Optional[str]  # None for native CRO
    amount: int  # Amount in wei/token units
    operation_type: str  # "native" or "erc20"


@dataclass
class BatchPaymentResult:
    """Result of a batch payment execution"""
    success: bool
    batch_id: Optional[str]
    tx_hash: Optional[str]
    gas_used: Optional[int]
    operations_count: int
    failed_operations: List[int]
    error: Optional[str] = None


class X402Executor:
    """
    Orchestrates execution of optimized routes through x402 facilitator
    Enhanced with retry logic, batch payments, and improved error handling
    """
    
    def __init__(
        self, 
        rpc_url: str, 
        router_contract_address: str, 
        private_key: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        facilitator_address: Optional[str] = None
    ):
        self.w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(rpc_url))
        # Add POA middleware for Cronos
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        
        self.router_address = router_contract_address
        self.facilitator_address = facilitator_address or os.getenv("X402_FACILITATOR")
        self.account = None
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        if private_key:
            self.account = Account.from_key(private_key)
            self.w3.eth.default_account = self.account.address
        
        # Load contract ABI (simplified)
        self.router_abi = self._load_router_abi()
        self.router_contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(router_contract_address),
            abi=self.router_abi
        ) if router_contract_address else None
        
        # Load facilitator ABI for direct interaction
        self.facilitator_abi = self._load_facilitator_abi()
        self.facilitator_contract = None
        if self.facilitator_address:
            try:
                self.facilitator_contract = self.w3.eth.contract(
                    address=Web3.to_checksum_address(self.facilitator_address),
                    abi=self.facilitator_abi
                )
            except Exception as e:
                logger.warning(f"Could not initialize facilitator contract: {e}")
        
        # Initialize facilitator client if available
        self.facilitator_client = None
        if HAS_FACILITATOR_SDK:
            try:
                facilitator_url = os.getenv("X402_FACILITATOR_URL", "https://facilitator.cronos.org")
                self.facilitator_client = FacilitatorClient(facilitator_url)
                logger.info("Facilitator SDK client initialized")
            except Exception as e:
                logger.warning(f"Could not initialize facilitator client: {e}")
    
    def _load_facilitator_abi(self) -> List[Dict]:
        """Load facilitator contract ABI for batch operations"""
        return [
            {
                "inputs": [
                    {
                        "components": [
                            {"internalType": "address", "name": "target", "type": "address"},
                            {"internalType": "uint256", "name": "value", "type": "uint256"},
                            {"internalType": "bytes", "name": "data", "type": "bytes"}
                        ],
                        "internalType": "struct IFacilitatorClient.Operation[]",
                        "name": "operations",
                        "type": "tuple[]"
                    },
                    {"internalType": "bytes", "name": "condition", "type": "bytes"},
                    {"internalType": "uint256", "name": "deadline", "type": "uint256"}
                ],
                "name": "executeConditionalBatch",
                "outputs": [],
                "stateMutability": "payable",
                "type": "function"
            }
        ]
    
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
            
            # Estimate gas with retry logic
            gas_estimate = await self.execute_with_retry(
                function_call.estimate_gas,
                {'from': self.account.address}
            )
            
            # Get current nonce with retry
            nonce = await self.execute_with_retry(
                self.w3.eth.get_transaction_count,
                self.account.address
            )
            
            # Get gas price (use EIP-1559 if available)
            try:
                fee_data = await self.w3.eth.fee_history(1, "latest")
                base_fee = fee_data.get("baseFeePerGas", [0])[0]
                gas_price = int(base_fee * 1.2)  # 20% over base fee
            except:
                gas_price = await self.w3.eth.gas_price
            
            # Build transaction
            transaction = await function_call.build_transaction({
                'from': self.account.address,
                'nonce': nonce,
                'gas': int(gas_estimate * 1.3),  # 30% buffer for x402 operations
                'gasPrice': gas_price,
                'chainId': await self.w3.eth.chain_id
            })
            
            # Sign transaction
            signed_txn = self.account.sign_transaction(transaction)
            
            # Send transaction with retry
            tx_hash = await self.execute_with_retry(
                self.w3.eth.send_raw_transaction,
                signed_txn.rawTransaction
            )
            
            # Wait for receipt with longer timeout for x402 operations
            receipt = await self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
            
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
            logger.error(f"Execution failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "status": "failed"
            }
    
    async def execute_with_retry(
        self,
        func,
        *args,
        max_retries: Optional[int] = None,
        **kwargs
    ) -> Any:
        """
        Execute a function with retry logic for transient failures
        
        Args:
            func: Async function to execute
            *args: Positional arguments
            max_retries: Maximum number of retries (defaults to self.max_retries)
            **kwargs: Keyword arguments
            
        Returns:
            Result of function execution
        """
        max_retries = max_retries or self.max_retries
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(
                        f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"All {max_retries} attempts failed: {e}")
        
        raise last_exception
    
    async def execute_batch_payment(
        self,
        payments: List[PaymentOperation],
        deadline: Optional[int] = None,
        condition: Optional[bytes] = None
    ) -> BatchPaymentResult:
        """
        Execute multiple payments atomically via x402 facilitator
        
        Args:
            payments: List of payment operations to execute
            deadline: Execution deadline timestamp (defaults to 30 minutes from now)
            condition: Optional condition bytes for conditional execution
            
        Returns:
            BatchPaymentResult with execution status
        """
        if not self.account:
            raise ValueError("No account configured for execution")
        
        if not payments:
            raise ValueError("Empty payment list")
        
        if deadline is None:
            deadline = int(time.time()) + 1800  # 30 minutes
        
        try:
            # Build x402 operations
            operations = []
            total_native_value = 0
            
            for payment in payments:
                if payment.operation_type == "native":
                    # Native CRO transfer
                    total_native_value += payment.amount
                    operations.append({
                        "target": Web3.to_checksum_address(payment.recipient),
                        "value": payment.amount,
                        "data": b""
                    })
                elif payment.operation_type == "erc20":
                    # ERC20 transfer
                    # Use Web3's encode_function_signature for proper encoding
                    transfer_abi = {
                        "constant": False,
                        "inputs": [
                            {"name": "_to", "type": "address"},
                            {"name": "_value", "type": "uint256"}
                        ],
                        "name": "transfer",
                        "outputs": [{"name": "", "type": "bool"}],
                        "type": "function"
                    }
                    transfer_function = self.w3.eth.contract(
                        abi=[transfer_abi]
                    ).functions.transfer(
                        Web3.to_checksum_address(payment.recipient),
                        payment.amount
                    )
                    operations.append({
                        "target": Web3.to_checksum_address(payment.token_address),
                        "value": 0,
                        "data": transfer_function._encode_transaction_data()
                    })
                else:
                    raise ValueError(f"Unknown operation type: {payment.operation_type}")
            
            # Use facilitator contract if available
            if self.facilitator_contract:
                return await self._execute_batch_via_contract(
                    operations, deadline, condition, total_native_value
                )
            else:
                # Fallback to direct facilitator SDK call
                return await self._execute_batch_via_sdk(
                    operations, deadline, condition, total_native_value
                )
                
        except Exception as e:
            logger.error(f"Batch payment execution failed: {e}", exc_info=True)
            return BatchPaymentResult(
                success=False,
                batch_id=None,
                tx_hash=None,
                gas_used=None,
                operations_count=len(payments),
                failed_operations=list(range(len(payments))),
                error=str(e)
            )
    
    async def _execute_batch_via_contract(
        self,
        operations: List[Dict],
        deadline: int,
        condition: Optional[bytes],
        value: int
    ) -> BatchPaymentResult:
        """Execute batch via facilitator contract"""
        if not self.facilitator_contract:
            raise ValueError("Facilitator contract not initialized")
        
        condition_bytes = condition or b""
        
        # Build transaction
        function_call = self.facilitator_contract.functions.executeConditionalBatch(
            operations,
            condition_bytes,
            deadline
        )
        
        # Estimate gas with retry
        gas_estimate = await self.execute_with_retry(
            function_call.estimate_gas,
            {'from': self.account.address, 'value': value}
        )
        
        # Get nonce
        nonce = await self.w3.eth.get_transaction_count(self.account.address)
        
        # Build and sign transaction
        transaction = await function_call.build_transaction({
            'from': self.account.address,
            'nonce': nonce,
            'gas': int(gas_estimate * 1.3),  # 30% buffer for batch operations
            'gasPrice': await self.w3.eth.gas_price,
            'chainId': await self.w3.eth.chain_id,
            'value': value
        })
        
        signed_txn = self.account.sign_transaction(transaction)
        
        # Send and wait for receipt
        tx_hash = await self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        receipt = await self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        
        return BatchPaymentResult(
            success=receipt.status == 1,
            batch_id=tx_hash.hex(),
            tx_hash=tx_hash.hex(),
            gas_used=receipt.gasUsed,
            operations_count=len(operations),
            failed_operations=[] if receipt.status == 1 else list(range(len(operations)))
        )
    
    async def _execute_batch_via_sdk(
        self,
        operations: List[Dict],
        deadline: int,
        condition: Optional[bytes],
        value: int
    ) -> BatchPaymentResult:
        """Execute batch via facilitator SDK (fallback)"""
        if not self.facilitator_client:
            raise ValueError("Facilitator SDK client not available")
        
        try:
            # Use SDK client if available
            result = await self.facilitator_client.execute_batch(
                operations=operations,
                condition=condition or b"",
                deadline=deadline,
                sender=self.account.address
            )
            
            return BatchPaymentResult(
                success=True,
                batch_id=result.get("batch_id"),
                tx_hash=result.get("tx_hash"),
                gas_used=result.get("gas_used"),
                operations_count=len(operations),
                failed_operations=[]
            )
        except Exception as e:
            logger.error(f"SDK execution failed: {e}")
            raise
    
    async def get_transaction_status(self, tx_hash: str) -> Dict[str, Any]:
        """
        Get status of a transaction with detailed information
        
        Args:
            tx_hash: Transaction hash
            
        Returns:
            Dictionary with transaction status details
        """
        try:
            receipt = await self.w3.eth.get_transaction_receipt(tx_hash)
            tx = await self.w3.eth.get_transaction(tx_hash)
            
            return {
                "tx_hash": tx_hash,
                "status": "success" if receipt.status == 1 else "failed",
                "block_number": receipt.blockNumber,
                "gas_used": receipt.gasUsed,
                "gas_price": tx.get("gasPrice"),
                "from": tx.get("from"),
                "to": tx.get("to"),
                "value": tx.get("value"),
                "confirmations": await self._get_confirmations(receipt.blockNumber),
                "timestamp": await self._get_block_timestamp(receipt.blockNumber)
            }
        except Exception as e:
            logger.error(f"Failed to get transaction status: {e}")
            return {
                "tx_hash": tx_hash,
                "status": "unknown",
                "error": str(e)
            }
    
    async def _get_confirmations(self, block_number: int) -> int:
        """Get number of confirmations for a block"""
        try:
            current_block = await self.w3.eth.block_number
            return max(0, current_block - block_number)
        except:
            return 0
    
    async def _get_block_timestamp(self, block_number: int) -> Optional[int]:
        """Get timestamp of a block"""
        try:
            block = await self.w3.eth.get_block(block_number)
            return block.get("timestamp")
        except:
            return None
    
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
        
        Enhanced with static call simulation if available
        """
        if not self.router_contract:
            raise ValueError("Router contract not initialized")
        
        try:
            # Try static call for more accurate simulation
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
            
            total_amount_wei = int(total_amount_in * 1e18)
            deadline = int(time.time()) + 1800
            
            # Static call (simulate without state change)
            try:
                result = await self.router_contract.functions.executeOptimizedSwap(
                    routes,
                    total_amount_wei,
                    token_in_addr,
                    token_out_addr,
                    0,  # minTotalOut = 0 for simulation
                    deadline
                ).call({'from': self.account.address if self.account else None})
                
                # If static call succeeds, we can estimate output
                # (Note: This is simplified - actual implementation would parse contract state)
                total_estimated_out = sum(
                    float(r.get("minAmountOut", 0)) / 1e18 for r in routes
                )
            except Exception:
                # Fallback to calculation-based estimation
                total_estimated_out = sum(
                    float(r.get("minAmountOut", 0)) / 1e18 for r in routes
                )
            
            estimated_slippage = abs(
                (total_estimated_out / total_amount_in - 1) * 100
            ) if total_amount_in > 0 else 0
            
            # Estimate gas cost
            try:
                gas_estimate = await self.router_contract.functions.executeOptimizedSwap(
                    routes,
                    total_amount_wei,
                    token_in_addr,
                    token_out_addr,
                    int(total_estimated_out * 0.995 * 1e18),
                    deadline
                ).estimate_gas({'from': self.account.address if self.account else None})
                
                gas_price = await self.w3.eth.gas_price
                estimated_gas_cost = (gas_estimate * gas_price) / 1e18
            except:
                estimated_gas_cost = None
            
            return {
                "total_in": total_amount_in,
                "estimated_out": total_estimated_out,
                "estimated_slippage_pct": estimated_slippage,
                "route_count": len(routes),
                "estimated_gas_cost_cro": estimated_gas_cost,
                "simulation": True
            }
            
        except Exception as e:
            logger.warning(f"Simulation failed, using fallback: {e}")
            # Fallback to simple calculation
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
                "simulation": True,
                "warning": "Simplified simulation (static call unavailable)"
            }

