"""
Batching Service for Multi-Leg Transactions
Implements time-window, business logic, and gas optimization batching strategies
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from decimal import Decimal
import uuid
import json
from enum import Enum
from collections import defaultdict

from sqlalchemy.orm import Session
from web3 import Web3

from .models import (
    Base, Batch, BatchItem, AuditLog,
    BatchStatus, TransactionStatus, LegStatus
)

logger = logging.getLogger(__name__)


class BatchingStrategy(str, Enum):
    """Batching strategies"""
    TIME_WINDOW = "time_window"  # Batch by time window
    BUSINESS_LOGIC = "business_logic"  # Batch by business context
    GAS_OPTIMIZATION = "gas_optimization"  # Batch for gas savings
    SIZE_LIMIT = "size_limit"  # Batch until size limit reached
    HYBRID = "hybrid"  # Combination of strategies


class BatchingService:
    """
    Service for batching transactions and legs for optimized execution
    
    Features:
    - Multiple batching strategies
    - Automatic batch execution
    - Gas optimization
    - Queue management
    """
    
    def __init__(
        self,
        db_session: Session,
        w3: Optional[Web3] = None,
        batch_executor: Optional[Callable] = None
    ):
        self.db = db_session
        self.w3 = w3
        self.batch_executor = batch_executor
        
        # In-memory queues for different batch types
        self.pending_batches: Dict[str, List[Any]] = defaultdict(list)
        self.batch_timers: Dict[str, asyncio.Task] = {}
        
        # Configuration
        self.default_time_window = 60  # seconds
        self.default_max_size = 100
        self.default_gas_threshold = 100000  # Minimum gas to save by batching
    
    def add_to_batch(
        self,
        transaction_id: Optional[str] = None,
        leg_id: Optional[str] = None,
        batch_type: str = "time_window",
        strategy: BatchingStrategy = BatchingStrategy.TIME_WINDOW,
        time_window_seconds: Optional[int] = None,
        max_size: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a transaction or leg to a batch
        
        Args:
            transaction_id: Transaction ID to batch
            leg_id: Leg ID to batch (alternative to transaction_id)
            batch_type: Type of batch
            strategy: Batching strategy
            time_window_seconds: Time window for batching
            max_size: Maximum batch size
            metadata: Optional metadata
            
        Returns:
            Batch ID
        """
        if not transaction_id and not leg_id:
            raise ValueError("Either transaction_id or leg_id must be provided")
        
        # Determine batch key
        batch_key = f"{batch_type}_{strategy.value}"
        
        # Check for existing pending batch
        existing_batch = self._find_pending_batch(batch_key, strategy)
        
        if existing_batch and not self._should_create_new_batch(
            existing_batch, strategy, time_window_seconds, max_size
        ):
            # Add to existing batch
            batch_id = existing_batch.batch_id
            self._add_item_to_batch(batch_id, transaction_id, leg_id)
            return batch_id
        
        # Create new batch
        batch_id = f"batch_{uuid.uuid4().hex[:16]}_{int(datetime.now().timestamp())}"
        
        batch = Batch(
            batch_id=batch_id,
            status=BatchStatus.COLLECTING,
            batch_type=batch_type,
            strategy=strategy.value,
            max_size=max_size or self.default_max_size,
            time_window_seconds=time_window_seconds or self.default_time_window,
            deadline=datetime.utcnow() + timedelta(
                seconds=time_window_seconds or self.default_time_window
            ),
            metadata=json.dumps(metadata) if metadata else None
        )
        
        self.db.add(batch)
        
        # Add item to batch
        self._add_item_to_batch(batch_id, transaction_id, leg_id)
        
        self.db.commit()
        
        # Schedule batch execution if time-window strategy
        if strategy == BatchingStrategy.TIME_WINDOW:
            self._schedule_batch_execution(batch_id, time_window_seconds or self.default_time_window)
        
        logger.info(f"Created batch {batch_id} with strategy {strategy.value}")
        
        return batch_id
    
    def _find_pending_batch(
        self,
        batch_key: str,
        strategy: BatchingStrategy
    ) -> Optional[Batch]:
        """Find existing pending batch"""
        return self.db.query(Batch).filter(
            Batch.status == BatchStatus.COLLECTING,
            Batch.strategy == strategy.value
        ).first()
    
    def _should_create_new_batch(
        self,
        existing_batch: Batch,
        strategy: BatchingStrategy,
        time_window_seconds: Optional[int],
        max_size: Optional[int]
    ) -> bool:
        """Determine if a new batch should be created"""
        if strategy == BatchingStrategy.SIZE_LIMIT:
            item_count = len(existing_batch.batch_items) if existing_batch.batch_items else 0
            return item_count >= (max_size or self.default_max_size)
        
        if strategy == BatchingStrategy.TIME_WINDOW:
            if existing_batch.deadline and datetime.utcnow() >= existing_batch.deadline:
                return True
        
        return False
    
    def _add_item_to_batch(
        self,
        batch_id: str,
        transaction_id: Optional[str],
        leg_id: Optional[str]
    ):
        """Add item to batch"""
        batch = self.db.query(Batch).filter_by(batch_id=batch_id).first()
        if not batch:
            raise ValueError(f"Batch not found: {batch_id}")
        
        # Get sequence
        existing_items = batch.batch_items or []
        sequence = len(existing_items)
        
        item = BatchItem(
            batch_id=batch_id,
            transaction_id=transaction_id,
            leg_id=leg_id,
            item_type="transaction" if transaction_id else "leg",
            sequence=sequence
        )
        
        batch.batch_items.append(item)
        self.db.add(item)
        self.db.commit()
    
    def _schedule_batch_execution(self, batch_id: str, delay_seconds: int):
        """Schedule batch execution after delay"""
        async def execute_after_delay():
            await asyncio.sleep(delay_seconds)
            await self.execute_batch(batch_id)
        
        task = asyncio.create_task(execute_after_delay())
        self.batch_timers[batch_id] = task
    
    async def execute_batch(self, batch_id: str) -> Dict[str, Any]:
        """
        Execute a batch
        
        Args:
            batch_id: Batch ID to execute
            
        Returns:
            Execution result
        """
        batch = self.db.query(Batch).filter_by(batch_id=batch_id).first()
        if not batch:
            raise ValueError(f"Batch not found: {batch_id}")
        
        if batch.status != BatchStatus.COLLECTING and batch.status != BatchStatus.READY:
            raise ValueError(f"Batch not ready for execution: {batch.status}")
        
        batch.status = BatchStatus.EXECUTING
        batch.ready_at = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"Executing batch {batch_id} with {len(batch.batch_items)} items")
        
        success_count = 0
        failure_count = 0
        gas_used_total = 0
        
        try:
            if self.batch_executor:
                # Use custom executor
                result = await self.batch_executor(batch)
            else:
                # Use default executor
                result = await self._execute_batch_default(batch)
            
            success_count = result.get("success_count", 0)
            failure_count = result.get("failure_count", 0)
            gas_used_total = result.get("gas_used", 0)
            tx_hash = result.get("tx_hash")
            
            batch.status = BatchStatus.COMPLETED if failure_count == 0 else BatchStatus.FAILED
            batch.executed_at = datetime.utcnow()
            batch.on_chain_tx_hash = tx_hash
            batch.gas_used = gas_used_total
            batch.success_count = success_count
            batch.failure_count = failure_count
            
            # Calculate gas savings (estimate)
            if batch.batch_items:
                estimated_individual_gas = len(batch.batch_items) * 21000  # Base gas per tx
                batch.gas_saved = max(0, estimated_individual_gas - gas_used_total)
            
            self.db.commit()
            
            logger.info(
                f"Batch {batch_id} executed: {success_count} success, {failure_count} failed, "
                f"gas saved: {batch.gas_saved}"
            )
            
            return {
                "success": failure_count == 0,
                "batch_id": batch_id,
                "success_count": success_count,
                "failure_count": failure_count,
                "gas_used": gas_used_total,
                "gas_saved": batch.gas_saved,
                "tx_hash": tx_hash
            }
            
        except Exception as e:
            logger.error(f"Batch execution failed: {e}")
            batch.status = BatchStatus.FAILED
            batch.error_message = str(e)
            batch.executed_at = datetime.utcnow()
            self.db.commit()
            raise
    
    async def _execute_batch_default(self, batch: Batch) -> Dict[str, Any]:
        """Default batch execution (should be overridden with actual on-chain execution)"""
        # This is a placeholder - in production, this would:
        # 1. Build a multi-send transaction or use a batching contract
        # 2. Execute on-chain
        # 3. Track results
        
        success_count = 0
        failure_count = 0
        
        for item in sorted(batch.batch_items, key=lambda i: i.sequence):
            try:
                # Mock execution
                await asyncio.sleep(0.1)  # Simulate execution time
                item.executed = True
                item.success = True
                success_count += 1
            except Exception as e:
                item.executed = True
                item.success = False
                item.error_message = str(e)
                failure_count += 1
        
        return {
            "success_count": success_count,
            "failure_count": failure_count,
            "gas_used": 100000,  # Mock gas
            "tx_hash": f"0x{batch.batch_id[:64]}"
        }
    
    def get_batch(self, batch_id: str) -> Optional[Batch]:
        """Get batch by ID"""
        return self.db.query(Batch).filter_by(batch_id=batch_id).first()
    
    def get_pending_batches(self, strategy: Optional[BatchingStrategy] = None) -> List[Batch]:
        """Get all pending batches"""
        query = self.db.query(Batch).filter(
            Batch.status.in_([BatchStatus.PENDING, BatchStatus.COLLECTING, BatchStatus.READY])
        )
        
        if strategy:
            query = query.filter(Batch.strategy == strategy.value)
        
        return query.all()
    
    async def auto_execute_ready_batches(self):
        """Automatically execute batches that are ready"""
        ready_batches = self.db.query(Batch).filter(
            Batch.status == BatchStatus.READY
        ).all()
        
        for batch in ready_batches:
            try:
                await self.execute_batch(batch.batch_id)
            except Exception as e:
                logger.error(f"Failed to auto-execute batch {batch.batch_id}: {e}")

