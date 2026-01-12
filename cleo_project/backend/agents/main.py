"""
Main entry point for C.L.E.O. Multi-Agent System
"""
import asyncio
import logging
import os
from decimal import Decimal
from dotenv import load_dotenv

from .orchestrator import OrchestratorAgent
from .message_bus import message_bus

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Main application entry point"""
    logger.info("Starting C.L.E.O. Multi-Agent System...")
    
    # Configuration (use environment variables in production)
    config = {
        "cronos_rpc": os.getenv("CRONOS_RPC", "https://evm-t3.cronos.org"),  # Testnet
        "private_key": os.getenv("PRIVATE_KEY", ""),  # Never hardcode in production!
        "x402_facilitator": os.getenv("X402_FACILITATOR", ""),  # x402 facilitator address on Cronos
        "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379")
    }
    
    if not config["private_key"]:
        logger.error("PRIVATE_KEY environment variable not set!")
        return
    
    if not config["x402_facilitator"]:
        logger.warning("X402_FACILITATOR not set, execution will fail")
    
    try:
        # Create orchestrator
        orchestrator = OrchestratorAgent(
            cronos_rpc=config["cronos_rpc"],
            private_key=config["private_key"],
            x402_facilitator=config["x402_facilitator"],
            redis_url=config["redis_url"]
        )
        
        # Register orchestrator with message bus
        message_bus.register_agent(orchestrator)
        
        # Start orchestrator (which starts all child agents)
        await orchestrator.start()
        
        # Example: Execute a test swap (commented out for safety)
        # Uncomment and configure for testing
        """
        test_token_in = "0x5C7F8A570d578ED84E63fdFA7b1eE72dEae1AE23"  # WCRO on testnet
        test_token_out = "0xc21223249CA28397B4B6541dfFaEcC539BfF0c59"  # USDC on testnet
        
        logger.info("Executing test swap...")
        
        result = await orchestrator.execute_swap(
            token_in=test_token_in,
            token_out=test_token_out,
            amount_in=Decimal("1000"),  # 1000 CRO
            max_slippage=Decimal("0.01"),  # 1% max slippage
            strategy="ai_optimized"
        )
        
        logger.info(f"Swap result: {result}")
        """
        
        # Keep the system running
        logger.info("C.L.E.O. Multi-Agent System is running. Press Ctrl+C to stop.")
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down C.L.E.O. system...")
        await orchestrator.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        logger.info("C.L.E.O. system stopped")


if __name__ == "__main__":
    asyncio.run(main())

