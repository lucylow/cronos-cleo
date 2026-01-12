"""
Pipeline Executor Service for Automated Settlement Pipelines
Handles pipeline creation, validation, execution, and monitoring
"""
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import json
from web3 import Web3
from web3.types import TxReceipt

class PipelineType(str, Enum):
    CROSS_DEX_SETTLEMENT = "CrossDEXSettlement"
    INVOICE_PAYMENT = "InvoicePayment"
    YIELD_HARVEST = "YieldHarvest"
    CUSTOM = "Custom"

class PipelineStatus(str, Enum):
    PENDING = "Pending"
    EXECUTING = "Executing"
    COMPLETED = "Completed"
    FAILED = "Failed"
    CANCELLED = "Cancelled"

class PipelineStep:
    """Represents a single step in a settlement pipeline"""
    def __init__(
        self,
        target: str,
        data: str,
        min_output: int = 0,
        is_critical: bool = True,
        condition: Optional[str] = None
    ):
        self.target = target
        self.data = data
        self.min_output = min_output
        self.is_critical = is_critical
        self.condition = condition

class SettlementPipeline:
    """Represents a complete settlement pipeline"""
    def __init__(
        self,
        pipeline_id: str,
        pipeline_type: PipelineType,
        creator: str,
        steps: List[PipelineStep],
        min_total_out: int,
        deadline: int,
        status: PipelineStatus = PipelineStatus.PENDING
    ):
        self.pipeline_id = pipeline_id
        self.pipeline_type = pipeline_type
        self.creator = creator
        self.steps = steps
        self.min_total_out = min_total_out
        self.deadline = deadline
        self.status = status
        self.created_at = int(datetime.now().timestamp())
        self.executed_at: Optional[int] = None
        self.tx_hash: Optional[str] = None
        self.error: Optional[str] = None

class PipelineExecutor:
    """Executes settlement pipelines with validation and monitoring"""
    
    def __init__(self, w3: Web3, contract_address: str, abi: List[Dict]):
        self.w3 = w3
        self.contract_address = contract_address
        self.contract = w3.eth.contract(address=contract_address, abi=abi)
        self.pipelines: Dict[str, SettlementPipeline] = {}
        
    async def create_cross_dex_settlement(
        self,
        creator: str,
        routes: List[Dict],
        token_in: str,
        token_out: str,
        total_amount_in: int,
        min_total_out: int,
        deadline: int
    ) -> str:
        """Create a cross-DEX settlement pipeline"""
        # Validate routes
        total_route_amount = sum(r['amountIn'] for r in routes)
        assert total_route_amount == total_amount_in, "Route amounts don't match total"
        
        # Build pipeline steps from routes
        steps = []
        for route in routes:
            step = PipelineStep(
                target=route['router'],
                data=self._encode_swap_call(
                    route['amountIn'],
                    route['minAmountOut'],
                    route['path'],
                    deadline
                ),
                min_output=route['minAmountOut'],
                is_critical=True
            )
            steps.append(step)
        
        # Create pipeline
        pipeline_id = self._generate_pipeline_id(creator)
        pipeline = SettlementPipeline(
            pipeline_id=pipeline_id,
            pipeline_type=PipelineType.CROSS_DEX_SETTLEMENT,
            creator=creator,
            steps=steps,
            min_total_out=min_total_out,
            deadline=deadline
        )
        
        self.pipelines[pipeline_id] = pipeline
        return pipeline_id
    
    async def create_invoice_payment(
        self,
        creator: str,
        invoice_id: int,
        currency: str,
        amount: int,
        recipient: str,
        delivery_token_id: int,
        delivery_nft: str,
        receipt_nft: str
    ) -> str:
        """Create an invoice payment pipeline"""
        pipeline_id = self._generate_pipeline_id(creator)
        
        # Build steps for invoice payment
        steps = [
            PipelineStep(
                target=delivery_nft,
                data=self._encode_owner_of(delivery_token_id),
                is_critical=True,
                condition=recipient.lower()  # Owner must match recipient
            ),
            PipelineStep(
                target=currency,
                data=self._encode_transfer(recipient, amount),
                is_critical=True
            ),
            PipelineStep(
                target=delivery_nft,
                data=self._encode_burn(delivery_token_id),
                is_critical=True
            ),
            PipelineStep(
                target=receipt_nft,
                data=self._encode_mint(recipient, invoice_id),
                is_critical=True
            )
        ]
        
        pipeline = SettlementPipeline(
            pipeline_id=pipeline_id,
            pipeline_type=PipelineType.INVOICE_PAYMENT,
            creator=creator,
            steps=steps,
            min_total_out=amount,
            deadline=int((datetime.now() + timedelta(days=30)).timestamp())
        )
        
        self.pipelines[pipeline_id] = pipeline
        return pipeline_id
    
    async def create_yield_harvest(
        self,
        creator: str,
        farm_address: str,
        reward_token: str,
        lp_token: str,
        token0: str,
        token1: str,
        router: str,
        min_reward_threshold: int
    ) -> str:
        """Create a yield harvest + compound pipeline"""
        pipeline_id = self._generate_pipeline_id(creator)
        
        steps = [
            # Step 1: Check rewards
            PipelineStep(
                target=farm_address,
                data=self._encode_balance_of(creator),
                min_output=min_reward_threshold,
                is_critical=True
            ),
            # Step 2: Claim rewards
            PipelineStep(
                target=farm_address,
                data=self._encode_claim(),
                is_critical=True
            ),
            # Step 3: Swap if needed (optional)
            PipelineStep(
                target=router,
                data=self._encode_swap_call(0, 0, [reward_token, token1], 0),
                is_critical=False  # Non-critical
            ),
            # Step 4: Add liquidity
            PipelineStep(
                target=router,
                data=self._encode_add_liquidity(token0, token1, 0, 0, 0, 0, creator, 0),
                is_critical=True
            ),
            # Step 5: Stake LP tokens
            PipelineStep(
                target=farm_address,
                data=self._encode_stake(2**256 - 1),  # Max uint
                is_critical=True
            )
        ]
        
        pipeline = SettlementPipeline(
            pipeline_id=pipeline_id,
            pipeline_type=PipelineType.YIELD_HARVEST,
            creator=creator,
            steps=steps,
            min_total_out=min_reward_threshold,
            deadline=int((datetime.now() + timedelta(hours=1)).timestamp())
        )
        
        self.pipelines[pipeline_id] = pipeline
        return pipeline_id
    
    async def validate_pipeline(self, pipeline_id: str) -> Dict[str, Any]:
        """Pre-execution validation of pipeline"""
        if pipeline_id not in self.pipelines:
            return {"valid": False, "error": "Pipeline not found"}
        
        pipeline = self.pipelines[pipeline_id]
        
        # Check deadline
        if datetime.now().timestamp() > pipeline.deadline:
            return {"valid": False, "error": "Pipeline expired"}
        
        # Check status
        if pipeline.status != PipelineStatus.PENDING:
            return {"valid": False, "error": f"Pipeline not pending: {pipeline.status}"}
        
        # Validate steps
        for i, step in enumerate(pipeline.steps):
            if not step.target or not step.data:
                return {"valid": False, "error": f"Invalid step {i}"}
        
        return {"valid": True, "pipeline": pipeline}
    
    async def simulate_pipeline(self, pipeline_id: str) -> Dict[str, Any]:
        """Simulate pipeline execution without on-chain call"""
        validation = await self.validate_pipeline(pipeline_id)
        if not validation["valid"]:
            return validation
        
        pipeline = validation["pipeline"]
        
        # Estimate gas
        gas_estimate = 120000 + len(pipeline.steps) * 12000
        
        # Mock execution result
        return {
            "pipeline_id": pipeline_id,
            "estimated_gas": gas_estimate,
            "steps_count": len(pipeline.steps),
            "min_total_out": pipeline.min_total_out,
            "deadline": pipeline.deadline,
            "simulation_success": True
        }
    
    async def execute_pipeline(
        self,
        pipeline_id: str,
        private_key: str
    ) -> Dict[str, Any]:
        """Execute pipeline on-chain via x402"""
        validation = await self.validate_pipeline(pipeline_id)
        if not validation["valid"]:
            return validation
        
        pipeline = validation["pipeline"]
        pipeline.status = PipelineStatus.EXECUTING
        
        try:
            # Build transaction
            account = self.w3.eth.account.from_key(private_key)
            
            # Call contract's executePipeline function
            tx = self.contract.functions.executePipeline(
                bytes.fromhex(pipeline_id.replace('0x', ''))
            ).build_transaction({
                'from': account.address,
                'gas': 500000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(account.address)
            })
            
            # Sign and send
            signed_tx = account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            # Wait for receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            pipeline.tx_hash = receipt['transactionHash'].hex()
            pipeline.executed_at = int(datetime.now().timestamp())
            
            if receipt['status'] == 1:
                pipeline.status = PipelineStatus.COMPLETED
                return {
                    "success": True,
                    "pipeline_id": pipeline_id,
                    "tx_hash": pipeline.tx_hash,
                    "gas_used": receipt['gasUsed']
                }
            else:
                pipeline.status = PipelineStatus.FAILED
                return {
                    "success": False,
                    "pipeline_id": pipeline_id,
                    "tx_hash": pipeline.tx_hash,
                    "error": "Transaction reverted"
                }
                
        except Exception as e:
            pipeline.status = PipelineStatus.FAILED
            pipeline.error = str(e)
            return {
                "success": False,
                "pipeline_id": pipeline_id,
                "error": str(e)
            }
    
    async def schedule_recurring_pipeline(
        self,
        pipeline_id: str,
        interval_seconds: int,
        max_executions: int
    ) -> Dict[str, Any]:
        """Schedule a pipeline for recurring execution"""
        if pipeline_id not in self.pipelines:
            return {"success": False, "error": "Pipeline not found"}
        
        # In production, this would interact with a scheduler service
        # For now, return success
        return {
            "success": True,
            "pipeline_id": pipeline_id,
            "interval_seconds": interval_seconds,
            "max_executions": max_executions,
            "next_execution": int((datetime.now() + timedelta(seconds=interval_seconds)).timestamp())
        }
    
    def get_pipeline(self, pipeline_id: str) -> Optional[SettlementPipeline]:
        """Get pipeline by ID"""
        return self.pipelines.get(pipeline_id)
    
    def get_user_pipelines(self, user_address: str) -> List[SettlementPipeline]:
        """Get all pipelines for a user"""
        return [
            p for p in self.pipelines.values()
            if p.creator.lower() == user_address.lower()
        ]
    
    # ==================== Helper Methods ====================
    
    def _generate_pipeline_id(self, creator: str) -> str:
        """Generate unique pipeline ID"""
        import hashlib
        timestamp = int(datetime.now().timestamp())
        data = f"{creator}{timestamp}{len(self.pipelines)}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def _encode_swap_call(
        self,
        amount_in: int,
        amount_out_min: int,
        path: List[str],
        deadline: int
    ) -> str:
        """Encode swapExactTokensForTokens call"""
        from eth_abi import encode
        from eth_utils import keccak
        
        selector = keccak(b"swapExactTokensForTokens(uint256,uint256,address[],address,uint256)")[:4]
        encoded = encode(
            ['uint256', 'uint256', 'address[]', 'address', 'uint256'],
            [amount_in, amount_out_min, path, self.contract_address, deadline]
        )
        return (selector + encoded).hex()
    
    def _encode_transfer(self, to: str, amount: int) -> str:
        """Encode ERC20 transfer call"""
        from eth_abi import encode
        from eth_utils import keccak
        
        selector = keccak(b"transfer(address,uint256)")[:4]
        encoded = encode(['address', 'uint256'], [to, amount])
        return (selector + encoded).hex()
    
    def _encode_owner_of(self, token_id: int) -> str:
        """Encode ERC721 ownerOf call"""
        from eth_abi import encode
        from eth_utils import keccak
        
        selector = keccak(b"ownerOf(uint256)")[:4]
        encoded = encode(['uint256'], [token_id])
        return (selector + encoded).hex()
    
    def _encode_burn(self, token_id: int) -> str:
        """Encode burn call"""
        from eth_abi import encode
        from eth_utils import keccak
        
        selector = keccak(b"burn(uint256)")[:4]
        encoded = encode(['uint256'], [token_id])
        return (selector + encoded).hex()
    
    def _encode_mint(self, to: str, token_id: int) -> str:
        """Encode mint call"""
        from eth_abi import encode
        from eth_utils import keccak
        
        selector = keccak(b"mint(address,uint256)")[:4]
        encoded = encode(['address', 'uint256'], [to, token_id])
        return (selector + encoded).hex()
    
    def _encode_balance_of(self, owner: str) -> str:
        """Encode balanceOf call"""
        from eth_abi import encode
        from eth_utils import keccak
        
        selector = keccak(b"balanceOf(address)")[:4]
        encoded = encode(['address'], [owner])
        return (selector + encoded).hex()
    
    def _encode_claim(self) -> str:
        """Encode claim/getReward call"""
        from eth_utils import keccak
        
        selector = keccak(b"getReward()")[:4]
        return selector.hex()
    
    def _encode_stake(self, amount: int) -> str:
        """Encode stake call"""
        from eth_abi import encode
        from eth_utils import keccak
        
        selector = keccak(b"stake(uint256)")[:4]
        encoded = encode(['uint256'], [amount])
        return (selector + encoded).hex()
    
    def _encode_add_liquidity(
        self,
        token_a: str,
        token_b: str,
        amount_a_desired: int,
        amount_b_desired: int,
        amount_a_min: int,
        amount_b_min: int,
        to: str,
        deadline: int
    ) -> str:
        """Encode addLiquidity call"""
        from eth_abi import encode
        from eth_utils import keccak
        
        selector = keccak(b"addLiquidity(address,address,uint256,uint256,uint256,uint256,address,uint256)")[:4]
        encoded = encode(
            ['address', 'address', 'uint256', 'uint256', 'uint256', 'uint256', 'address', 'uint256'],
            [token_a, token_b, amount_a_desired, amount_b_desired, amount_a_min, amount_b_min, to, deadline]
        )
        return (selector + encoded).hex()

