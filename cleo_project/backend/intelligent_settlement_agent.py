"""
Intelligent Settlement Agent
AI agent that monitors deals and automatically releases milestones when conditions are met
Integrates with x402 facilitator and existing AI infrastructure
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from web3 import Web3
from intelligent_settlement import IntelligentSettlementService

logger = logging.getLogger(__name__)


class SettlementAgent:
    """
    AI agent that monitors intelligent settlement deals and releases milestones
    when off-chain/on-chain conditions are satisfied
    """
    
    def __init__(
        self,
        settlement_service: IntelligentSettlementService,
        check_interval: int = 60,  # Check every 60 seconds
        enable_auto_release: bool = True
    ):
        self.settlement_service = settlement_service
        self.check_interval = check_interval
        self.enable_auto_release = enable_auto_release
        self.running = False
        self.monitored_deals: Dict[int, Dict[str, Any]] = {}
        self.condition_checkers: Dict[int, callable] = {}
    
    async def start(self):
        """Start the settlement agent monitoring loop"""
        if self.running:
            logger.warning("Settlement agent already running")
            return
        
        self.running = True
        logger.info("Starting intelligent settlement agent...")
        
        # Start monitoring loop
        asyncio.create_task(self._monitoring_loop())
    
    async def stop(self):
        """Stop the settlement agent"""
        self.running = False
        logger.info("Stopping intelligent settlement agent...")
    
    async def _monitoring_loop(self):
        """Main monitoring loop that checks deals and releases milestones"""
        while self.running:
            try:
                await self._check_all_deals()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                await asyncio.sleep(self.check_interval)
    
    async def _check_all_deals(self):
        """Check all monitored deals for milestone release conditions"""
        for deal_id, deal_info in list(self.monitored_deals.items()):
            try:
                # Get current deal state
                deal = await self.settlement_service.get_deal(deal_id)
                
                if "error" in deal:
                    logger.warning(f"Deal {deal_id} not found, removing from monitoring")
                    self.monitored_deals.pop(deal_id, None)
                    continue
                
                # Check if deal is still active
                if deal["status"] not in ["Active", "PendingFunding"]:
                    logger.info(f"Deal {deal_id} is {deal['status']}, removing from monitoring")
                    self.monitored_deals.pop(deal_id, None)
                    continue
                
                # Check each incomplete milestone
                for idx, milestone in enumerate(deal["milestones"]):
                    if milestone["completed"]:
                        continue
                    
                    # Check if conditions are met for this milestone
                    if await self._check_milestone_conditions(deal_id, idx, deal, milestone):
                        if self.enable_auto_release:
                            await self._release_milestone(deal_id, idx, deal)
                        else:
                            logger.info(f"Conditions met for deal {deal_id} milestone {idx}, but auto-release disabled")
                
            except Exception as e:
                logger.error(f"Error checking deal {deal_id}: {e}", exc_info=True)
    
    async def _check_milestone_conditions(
        self,
        deal_id: int,
        milestone_index: int,
        deal: Dict[str, Any],
        milestone: Dict[str, Any]
    ) -> bool:
        """
        Check if conditions are met for releasing a milestone
        Override this method or register custom condition checkers
        """
        # Check if custom condition checker is registered
        if deal_id in self.condition_checkers:
            try:
                return await self.condition_checkers[deal_id](deal_id, milestone_index, deal, milestone)
            except Exception as e:
                logger.error(f"Error in custom condition checker: {e}")
                return False
        
        # Default condition: check if deadline has passed (for testing)
        # In production, this would check off-chain conditions like:
        # - Delivery confirmation
        # - KYC verification
        # - Oracle data
        # - Risk scores
        # - x402 facilitator verification
        
        current_time = int(datetime.now().timestamp())
        
        # Example: Release milestone if deal has been active for a certain period
        # This is just a placeholder - replace with actual condition logic
        if deal["status"] == "Active":
            time_active = current_time - deal["created_at"]
            # Example: Release first milestone after 1 hour (for testing)
            if milestone_index == 0 and time_active >= 3600:
                return True
        
        return False
    
    async def _release_milestone(
        self,
        deal_id: int,
        milestone_index: int,
        deal: Dict[str, Any]
    ):
        """Release a milestone when conditions are met"""
        try:
            milestone = deal["milestones"][milestone_index]
            
            # Calculate minimum seller amount (with 1% slippage protection)
            min_seller_amount = int(milestone["amount"] * 0.99)
            
            # Get next agent nonce
            agent_nonce = deal["agent_nonce"] + 1
            
            logger.info(
                f"Releasing milestone {milestone_index} for deal {deal_id} "
                f"(amount: {milestone['amount']}, nonce: {agent_nonce})"
            )
            
            result = await self.settlement_service.agent_release_milestone(
                deal_id=deal_id,
                milestone_index=milestone_index,
                min_seller_amount=min_seller_amount,
                agent_nonce=agent_nonce
            )
            
            if result.get("success"):
                logger.info(
                    f"Successfully released milestone {milestone_index} for deal {deal_id}. "
                    f"Tx: {result.get('tx_hash')}"
                )
            else:
                logger.error(
                    f"Failed to release milestone {milestone_index} for deal {deal_id}: "
                    f"{result.get('error')}"
                )
        
        except Exception as e:
            logger.error(f"Error releasing milestone: {e}", exc_info=True)
    
    def register_deal(
        self,
        deal_id: int,
        metadata: Optional[Dict[str, Any]] = None,
        condition_checker: Optional[callable] = None
    ):
        """
        Register a deal for monitoring
        
        Args:
            deal_id: Deal ID to monitor
            metadata: Optional metadata about the deal
            condition_checker: Optional custom function to check milestone conditions
                Should be async and return bool
        """
        self.monitored_deals[deal_id] = {
            "deal_id": deal_id,
            "metadata": metadata or {},
            "registered_at": int(datetime.now().timestamp())
        }
        
        if condition_checker:
            self.condition_checkers[deal_id] = condition_checker
        
        logger.info(f"Registered deal {deal_id} for monitoring")
    
    def unregister_deal(self, deal_id: int):
        """Unregister a deal from monitoring"""
        self.monitored_deals.pop(deal_id, None)
        self.condition_checkers.pop(deal_id, None)
        logger.info(f"Unregistered deal {deal_id} from monitoring")
    
    async def check_deal_conditions(self, deal_id: int) -> Dict[str, Any]:
        """
        Manually check conditions for a specific deal
        Returns status of all milestones
        """
        try:
            deal = await self.settlement_service.get_deal(deal_id)
            
            if "error" in deal:
                return {"error": deal["error"]}
            
            milestone_statuses = []
            for idx, milestone in enumerate(deal["milestones"]):
                conditions_met = await self._check_milestone_conditions(
                    deal_id, idx, deal, milestone
                )
                milestone_statuses.append({
                    "index": idx,
                    "amount": milestone["amount"],
                    "completed": milestone["completed"],
                    "conditions_met": conditions_met
                })
            
            return {
                "deal_id": deal_id,
                "status": deal["status"],
                "milestones": milestone_statuses
            }
        except Exception as e:
            logger.error(f"Error checking deal conditions: {e}", exc_info=True)
            return {"error": str(e)}


# Integration with x402 facilitator
async def create_x402_condition_checker(
    x402_executor,
    deal_id: int,
    verification_data: Dict[str, Any]
) -> callable:
    """
    Create a condition checker that uses x402 facilitator verification
    
    Args:
        x402_executor: X402Executor instance
        deal_id: Deal ID
        verification_data: Data needed for x402 verification
    
    Returns:
        Async function that checks conditions via x402
    """
    async def x402_condition_checker(
        deal_id: int,
        milestone_index: int,
        deal: Dict[str, Any],
        milestone: Dict[str, Any]
    ) -> bool:
        """
        Check conditions using x402 facilitator
        This would verify payee/payor intents and other on-chain conditions
        """
        try:
            # Example: Check if x402 facilitator has verified the payment intent
            # In production, this would call x402 facilitator APIs or check on-chain state
            
            # Placeholder: Check if deal has been active for required time
            # Replace with actual x402 verification logic
            current_time = int(datetime.now().timestamp())
            time_active = current_time - deal["created_at"]
            
            # Example condition: Release after verification period
            required_time = verification_data.get("required_time", 3600)
            return time_active >= required_time
        
        except Exception as e:
            logger.error(f"Error in x402 condition checker: {e}")
            return False
    
    return x402_condition_checker
