// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@crypto.com/facilitator-client/contracts/interfaces/IFacilitatorClient.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/token/ERC721/IERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

/**
 * @title SettlementPipeline
 * @notice Automated settlement pipelines for multi-step, atomic financial operations
 * @dev Supports cross-DEX settlement, invoice payment, yield harvest patterns
 */
contract SettlementPipeline is Ownable, Pausable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    // x402 Integration
    IFacilitatorClient public immutable facilitator;

    // Pipeline Management
    enum PipelineStatus {
        Pending,
        Executing,
        Completed,
        Failed,
        Cancelled
    }

    enum PipelineType {
        CrossDEXSettlement,
        InvoicePayment,
        YieldHarvest,
        Custom
    }

    struct PipelineStep {
        address target;           // Contract to call
        bytes data;               // Calldata for the operation
        uint256 minOutput;        // Minimum output (if applicable)
        bool isCritical;          // Fail entire pipeline if this fails
        bytes condition;          // Optional condition check
    }

    struct Pipeline {
        bytes32 pipelineId;
        PipelineType pipelineType;
        address creator;
        PipelineStatus status;
        uint256 deadline;
        uint256 minTotalOut;     // Global minimum output condition
        uint256 createdAt;
        uint256 executedAt;
        PipelineStep[] steps;
        mapping(address => uint256) balances; // Token balances for accounting
    }

    mapping(bytes32 => Pipeline) public pipelines;
    mapping(address => bytes32[]) public userPipelines;
    mapping(bytes32 => bool) public pipelineExists;

    // Recurring Pipelines
    struct RecurringPipeline {
        bytes32 pipelineId;
        uint256 interval;         // Seconds between executions
        uint256 nextExecution;
        uint256 maxExecutions;
        uint256 executionCount;
        bool isActive;
    }

    mapping(bytes32 => RecurringPipeline) public recurringPipelines;

    // Circuit Breaker
    bool public circuitBreakerActive = false;
    uint256 public maxPipelineValue = type(uint256).max; // Max value per pipeline

    // Events
    event PipelineCreated(
        bytes32 indexed pipelineId,
        address indexed creator,
        PipelineType pipelineType
    );

    event PipelineExecuted(
        bytes32 indexed pipelineId,
        uint256 totalOutput,
        bool success
    );

    event PipelineStepExecuted(
        bytes32 indexed pipelineId,
        uint256 stepIndex,
        bool success
    );

    event RecurringPipelineScheduled(
        bytes32 indexed pipelineId,
        uint256 nextExecution
    );

    event CircuitBreakerToggled(bool active);

    constructor(address _facilitator) {
        facilitator = IFacilitatorClient(_facilitator);
    }

    // ==================== Pipeline Creation ====================

    /**
     * @notice Create a new settlement pipeline
     * @param pipelineType Type of pipeline (CrossDEX, Invoice, Yield, Custom)
     * @param steps Array of pipeline steps to execute
     * @param minTotalOut Global minimum output requirement
     * @param deadline Execution deadline
     * @return pipelineId Unique identifier for the pipeline
     */
    function createPipeline(
        PipelineType pipelineType,
        PipelineStep[] calldata steps,
        uint256 minTotalOut,
        uint256 deadline
    ) external whenNotPaused returns (bytes32 pipelineId) {
        require(steps.length > 0, "No steps provided");
        require(deadline > block.timestamp, "Invalid deadline");
        require(!circuitBreakerActive, "Circuit breaker active");

        pipelineId = keccak256(
            abi.encodePacked(msg.sender, block.timestamp, block.number)
        );

        require(!pipelineExists[pipelineId], "Pipeline ID collision");

        Pipeline storage pipeline = pipelines[pipelineId];
        pipeline.pipelineId = pipelineId;
        pipeline.pipelineType = pipelineType;
        pipeline.creator = msg.sender;
        pipeline.status = PipelineStatus.Pending;
        pipeline.deadline = deadline;
        pipeline.minTotalOut = minTotalOut;
        pipeline.createdAt = block.timestamp;

        // Copy steps
        for (uint256 i = 0; i < steps.length; i++) {
            pipeline.steps.push(steps[i]);
        }

        pipelineExists[pipelineId] = true;
        userPipelines[msg.sender].push(pipelineId);

        emit PipelineCreated(pipelineId, msg.sender, pipelineType);
    }

    /**
     * @notice Execute a settlement pipeline atomically via x402
     * @param pipelineId Pipeline to execute
     */
    function executePipeline(
        bytes32 pipelineId
    ) external nonReentrant whenNotPaused {
        require(pipelineExists[pipelineId], "Pipeline not found");
        require(!circuitBreakerActive, "Circuit breaker active");

        Pipeline storage pipeline = pipelines[pipelineId];
        require(
            pipeline.status == PipelineStatus.Pending,
            "Pipeline not pending"
        );
        require(block.timestamp <= pipeline.deadline, "Pipeline expired");

        pipeline.status = PipelineStatus.Executing;

        // Build x402 operations from pipeline steps
        IFacilitatorClient.Operation[] memory operations = _buildOperations(
            pipeline
        );

        // Execute atomically via x402
        try facilitator.executeConditionalBatch(
            operations,
            pipeline.minTotalOut, // Global condition
            pipeline.deadline
        ) {
            pipeline.status = PipelineStatus.Completed;
            pipeline.executedAt = block.timestamp;

            emit PipelineExecuted(pipelineId, pipeline.minTotalOut, true);
        } catch {
            pipeline.status = PipelineStatus.Failed;
            emit PipelineExecuted(pipelineId, 0, false);
            revert("Pipeline execution failed");
        }
    }

    /**
     * @notice Build x402 operations from pipeline steps
     */
    function _buildOperations(
        Pipeline storage pipeline
    ) internal view returns (IFacilitatorClient.Operation[] memory) {
        IFacilitatorClient.Operation[] memory operations = new IFacilitatorClient.Operation[](
            pipeline.steps.length
        );

        for (uint256 i = 0; i < pipeline.steps.length; i++) {
            PipelineStep storage step = pipeline.steps[i];

            operations[i] = IFacilitatorClient.Operation({
                target: step.target,
                value: 0,
                data: step.data,
                condition: step.condition
            });

            emit PipelineStepExecuted(pipeline.pipelineId, i, true);
        }

        return operations;
    }

    // ==================== Pipeline Patterns ====================

    /**
     * @notice Create a cross-DEX settlement pipeline
     * @param routes Array of DEX routes to execute
     * @param tokenIn Input token address
     * @param tokenOut Output token address
     * @param totalAmountIn Total amount to swap
     * @param minTotalOut Minimum total output
     * @param deadline Execution deadline
     */
    function createCrossDEXSettlement(
        RouteSplit[] calldata routes,
        address tokenIn,
        address tokenOut,
        uint256 totalAmountIn,
        uint256 minTotalOut,
        uint256 deadline
    ) external returns (bytes32 pipelineId) {
        require(routes.length > 0, "No routes provided");

        // Transfer tokens from user
        IERC20(tokenIn).safeTransferFrom(
            msg.sender,
            address(this),
            totalAmountIn
        );

        // Build pipeline steps
        PipelineStep[] memory steps = new PipelineStep[](routes.length + 1);

        // Step 1-N: Execute swaps on each DEX
        for (uint256 i = 0; i < routes.length; i++) {
            steps[i] = PipelineStep({
                target: routes[i].router,
                data: abi.encodeWithSelector(
                    0x38ed1739, // swapExactTokensForTokens
                    routes[i].amountIn,
                    routes[i].minAmountOut,
                    routes[i].path,
                    address(this),
                    deadline
                ),
                minOutput: routes[i].minAmountOut,
                isCritical: true,
                condition: bytes("")
            });
        }

        // Final step: Aggregate and transfer output
        steps[routes.length] = PipelineStep({
            target: address(this),
            data: abi.encodeWithSelector(
                this._settleOutput.selector,
                tokenOut,
                msg.sender,
                minTotalOut
            ),
            minOutput: minTotalOut,
            isCritical: true,
            condition: bytes("")
        });

        pipelineId = createPipeline(
            PipelineType.CrossDEXSettlement,
            steps,
            minTotalOut,
            deadline
        );
    }

    /**
     * @notice Internal function to settle output tokens
     */
    function _settleOutput(
        address tokenOut,
        address recipient,
        uint256 minAmount
    ) external {
        require(msg.sender == address(this), "Internal only");
        uint256 balance = IERC20(tokenOut).balanceOf(address(this));
        require(balance >= minAmount, "Insufficient output");
        IERC20(tokenOut).safeTransfer(recipient, balance);
    }

    /**
     * @notice Create an invoice payment pipeline
     * @param invoiceId Invoice identifier
     * @param currency Payment token address
     * @param amount Payment amount
     * @param recipient Invoice recipient
     * @param deliveryTokenId NFT token ID for delivery confirmation
     * @param deliveryNFT Delivery NFT contract address
     * @param receiptNFT Receipt NFT contract address
     */
    function createInvoicePayment(
        uint256 invoiceId,
        address currency,
        uint256 amount,
        address recipient,
        uint256 deliveryTokenId,
        address deliveryNFT,
        address receiptNFT
    ) external returns (bytes32 pipelineId) {
        // Transfer payment from payer
        IERC20(currency).safeTransferFrom(msg.sender, address(this), amount);

        // Build pipeline steps
        PipelineStep[] memory steps = new PipelineStep[](4);

        // Step 1: Verify delivery NFT exists and is owned by recipient
        steps[0] = PipelineStep({
            target: deliveryNFT,
            data: abi.encodeWithSelector(
                IERC721.ownerOf.selector,
                deliveryTokenId
            ),
            minOutput: 0,
            isCritical: true,
            condition: abi.encodePacked(recipient) // Owner must match
        });

        // Step 2: Transfer payment to supplier
        steps[1] = PipelineStep({
            target: currency,
            data: abi.encodeWithSelector(
                IERC20.transfer.selector,
                recipient,
                amount
            ),
            minOutput: 0,
            isCritical: true,
            condition: bytes("")
        });

        // Step 3: Burn delivery NFT
        steps[2] = PipelineStep({
            target: deliveryNFT,
            data: abi.encodeWithSelector(
                0x42966c68, // burn(uint256)
                deliveryTokenId
            ),
            minOutput: 0,
            isCritical: true,
            condition: bytes("")
        });

        // Step 4: Mint receipt NFT
        steps[3] = PipelineStep({
            target: receiptNFT,
            data: abi.encodeWithSelector(
                0x40c10f19, // mint(address,uint256)
                recipient,
                invoiceId
            ),
            minOutput: 0,
            isCritical: true,
            condition: bytes("")
        });

        pipelineId = createPipeline(
            PipelineType.InvoicePayment,
            steps,
            amount, // minTotalOut = payment amount
            block.timestamp + 30 days
        );
    }

    /**
     * @notice Create a yield harvest + compound pipeline
     * @param farmAddress Staking farm contract
     * @param rewardToken Reward token address
     * @param lpToken LP token address
     * @param token0 First token in LP pair
     * @param token1 Second token in LP pair
     * @param router DEX router for adding liquidity
     * @param minRewardThreshold Minimum reward to trigger harvest
     */
    function createYieldHarvest(
        address farmAddress,
        address rewardToken,
        address lpToken,
        address token0,
        address token1,
        address router,
        uint256 minRewardThreshold
    ) external returns (bytes32 pipelineId) {
        // Build pipeline steps
        PipelineStep[] memory steps = new PipelineStep[](5);

        // Step 1: Check rewards > threshold
        steps[0] = PipelineStep({
            target: farmAddress,
            data: abi.encodeWithSelector(
                0x70a08231, // balanceOf(address)
                address(this)
            ),
            minOutput: minRewardThreshold,
            isCritical: true,
            condition: bytes("")
        });

        // Step 2: Claim rewards
        steps[1] = PipelineStep({
            target: farmAddress,
            data: abi.encodeWithSelector(0x379607f5), // claim() or getReward()
            minOutput: 0,
            isCritical: true,
            condition: bytes("")
        });

        // Step 3: Swap rewards to token1 if needed (for balance)
        steps[2] = PipelineStep({
            target: router,
            data: abi.encodeWithSelector(
                0x38ed1739, // swapExactTokensForTokens
                0, // Will be calculated
                0,
                _buildPath(rewardToken, token1),
                address(this),
                block.timestamp + 1800
            ),
            minOutput: 0,
            isCritical: false, // Non-critical if already balanced
            condition: bytes("")
        });

        // Step 4: Add liquidity
        steps[3] = PipelineStep({
            target: router,
            data: abi.encodeWithSelector(
                0xe8e33700, // addLiquidity
                token0,
                token1,
                0, // Will use available balance
                0,
                0,
                0,
                address(this),
                block.timestamp + 1800
            ),
            minOutput: 0,
            isCritical: true,
            condition: bytes("")
        });

        // Step 5: Stake LP tokens back
        steps[4] = PipelineStep({
            target: farmAddress,
            data: abi.encodeWithSelector(
                0xa694fc3a, // stake(uint256)
                type(uint256).max // Stake all
            ),
            minOutput: 0,
            isCritical: true,
            condition: bytes("")
        });

        pipelineId = createPipeline(
            PipelineType.YieldHarvest,
            steps,
            minRewardThreshold,
            block.timestamp + 1 hours
        );
    }

    function _buildPath(
        address tokenA,
        address tokenB
    ) internal pure returns (address[] memory) {
        address[] memory path = new address[](2);
        path[0] = tokenA;
        path[1] = tokenB;
        return path;
    }

    // ==================== Recurring Pipelines ====================

    /**
     * @notice Schedule a pipeline for recurring execution
     */
    function scheduleRecurringPipeline(
        bytes32 pipelineId,
        uint256 interval,
        uint256 maxExecutions
    ) external {
        require(pipelineExists[pipelineId], "Pipeline not found");
        Pipeline storage pipeline = pipelines[pipelineId];
        require(pipeline.creator == msg.sender, "Not pipeline creator");

        recurringPipelines[pipelineId] = RecurringPipeline({
            pipelineId: pipelineId,
            interval: interval,
            nextExecution: block.timestamp + interval,
            maxExecutions: maxExecutions,
            executionCount: 0,
            isActive: true
        });

        emit RecurringPipelineScheduled(pipelineId, block.timestamp + interval);
    }

    /**
     * @notice Execute recurring pipeline if due
     */
    function executeRecurringPipeline(bytes32 pipelineId) external {
        RecurringPipeline storage recurring = recurringPipelines[pipelineId];
        require(recurring.isActive, "Not active");
        require(
            block.timestamp >= recurring.nextExecution,
            "Not yet due"
        );
        require(
            recurring.executionCount < recurring.maxExecutions,
            "Max executions reached"
        );

        // Reset pipeline status for re-execution
        Pipeline storage pipeline = pipelines[pipelineId];
        pipeline.status = PipelineStatus.Pending;
        pipeline.deadline = block.timestamp + 1 hours;

        executePipeline(pipelineId);

        recurring.executionCount++;
        recurring.nextExecution = block.timestamp + recurring.interval;

        if (recurring.executionCount >= recurring.maxExecutions) {
            recurring.isActive = false;
        }
    }

    // ==================== Safety Mechanisms ====================

    /**
     * @notice Toggle circuit breaker
     */
    function toggleCircuitBreaker() external onlyOwner {
        circuitBreakerActive = !circuitBreakerActive;
        emit CircuitBreakerToggled(circuitBreakerActive);
    }

    /**
     * @notice Set maximum pipeline value
     */
    function setMaxPipelineValue(uint256 _maxValue) external onlyOwner {
        maxPipelineValue = _maxValue;
    }

    /**
     * @notice Pause contract
     */
    function pause() external onlyOwner {
        _pause();
    }

    /**
     * @notice Unpause contract
     */
    function unpause() external onlyOwner {
        _unpause();
    }

    // ==================== View Functions ====================

    function getPipeline(
        bytes32 pipelineId
    ) external view returns (
        PipelineType pipelineType,
        address creator,
        PipelineStatus status,
        uint256 deadline,
        uint256 minTotalOut,
        uint256 stepCount
    ) {
        require(pipelineExists[pipelineId], "Pipeline not found");
        Pipeline storage pipeline = pipelines[pipelineId];
        return (
            pipeline.pipelineType,
            pipeline.creator,
            pipeline.status,
            pipeline.deadline,
            pipeline.minTotalOut,
            pipeline.steps.length
        );
    }

    function getPipelineSteps(
        bytes32 pipelineId
    ) external view returns (PipelineStep[] memory) {
        require(pipelineExists[pipelineId], "Pipeline not found");
        Pipeline storage pipeline = pipelines[pipelineId];
        return pipeline.steps;
    }

    // Helper struct for cross-DEX routes
    struct RouteSplit {
        address router;
        address[] path;
        uint256 amountIn;
        uint256 minAmountOut;
    }
}

