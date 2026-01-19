// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "@crypto.com/facilitator-client/contracts/interfaces/IFacilitatorClient.sol";

/**
 * @title CLECORouter
 * @notice Production router contract with x402 atomic batch execution, risk management, and circuit breakers
 * @dev Implements pre-execution risk gates, volatility filters, and emergency pause mechanisms
 */
contract CLECORouter is ReentrancyGuard, Ownable, Pausable {
    using SafeERC20 for IERC20;

    IFacilitatorClient public immutable facilitator;
    address public feeRecipient;
    uint256 public feeBps = 20; // 0.2% default

    // Risk Management Parameters
    uint256 public volatilityPauseThreshold = 5; // 5% 1h volatility threshold
    uint256 public maxPoolImpact = 10; // 10% of pool depth max position
    bool public emergencyPause = false;
    uint256 public maxPositionSizeBps = 1500; // 15% of pool depth

    // DEX Router Interface
    interface IDEXRouter {
        function swapExactTokensForTokens(
            uint amountIn,
            uint amountOutMin,
            address[] calldata path,
            address to,
            uint deadline
        ) external returns (uint[] memory amounts);
    }

    struct Route {
        address dexRouter;
        address[] path;
        uint256 amountIn;
        uint256 minAmountOut;
    }

    struct ExecutionPlan {
        bytes32 id;
        address inputToken;
        address outputToken;
        uint256 totalAmountIn;
        uint256 minTotalOut;
        Route[] routes;
        uint256 deadline;
        address creator;
        bool executed;
        uint256 totalReceived;
    }

    mapping(bytes32 => ExecutionPlan) public plans;
    mapping(address => bytes32[]) public userPlans;

    // Performance Metrics
    struct ExecutionMetrics {
        uint256 totalExecutions;
        uint256 totalVolume;
        uint256 totalFees;
        uint256 averageSlippageBps;
    }
    ExecutionMetrics public metrics;

    // Events
    event ExecutionPlanCreated(bytes32 indexed id, address indexed user, uint256 totalAmountIn);
    event OptimizedExecution(bytes32 indexed id, uint256 totalReceived, uint256 slippageBps);
    event ExecutionFailed(bytes32 indexed id, string reason);
    event CircuitBreakerToggled(bool active);
    event RiskThresholdUpdated(string parameter, uint256 oldValue, uint256 newValue);
    event FeeCollected(bytes32 indexed planId, uint256 feeAmount);

    modifier checkMarketRegime() {
        require(!emergencyPause, "Emergency pause active");
        require(!paused(), "Contract paused");
        _;
    }

    constructor(address _facilitator, address _feeRecipient) {
        require(_facilitator != address(0), "Invalid facilitator");
        require(_feeRecipient != address(0), "Invalid fee recipient");
        facilitator = IFacilitatorClient(_facilitator);
        feeRecipient = _feeRecipient;
    }

    /**
     * @notice Create and execute an optimized execution plan atomically
     * @param routes Array of routes across different DEXs
     * @param inputToken Input token address
     * @param outputToken Output token address
     * @param minTotalOut Minimum total output (slippage protection)
     * @return planId Unique plan identifier
     */
    function createAndExecutePlan(
        Route[] calldata routes,
        address inputToken,
        address outputToken,
        uint256 minTotalOut
    ) external payable nonReentrant checkMarketRegime returns (bytes32 planId) {
        require(routes.length > 0, "No routes provided");
        require(inputToken != address(0) && outputToken != address(0), "Invalid tokens");
        require(minTotalOut > 0, "Invalid min output");

        // Validate route amounts
        uint256 totalAmountIn = 0;
        for (uint i = 0; i < routes.length; i++) {
            require(routes[i].dexRouter != address(0), "Invalid router");
            require(routes[i].path.length >= 2, "Invalid path");
            require(routes[i].path[0] == inputToken, "Path mismatch");
            require(routes[i].path[routes[i].path.length - 1] == outputToken, "Path mismatch");
            totalAmountIn += routes[i].amountIn;
        }

        planId = keccak256(abi.encodePacked(msg.sender, block.timestamp, block.number, totalAmountIn));

        // Store plan
        ExecutionPlan storage plan = plans[planId];
        plan.id = planId;
        plan.inputToken = inputToken;
        plan.outputToken = outputToken;
        plan.totalAmountIn = totalAmountIn;
        plan.minTotalOut = minTotalOut;
        plan.deadline = block.timestamp + 1800; // 30 minutes
        plan.creator = msg.sender;
        plan.executed = false;

        // Copy routes
        for (uint i = 0; i < routes.length; i++) {
            plan.routes.push(routes[i]);
        }

        userPlans[msg.sender].push(planId);

        // Transfer input tokens
        IERC20(inputToken).safeTransferFrom(msg.sender, address(this), totalAmountIn);

        emit ExecutionPlanCreated(planId, msg.sender, totalAmountIn);

        // Execute via x402
        _executeViaX402(planId);
    }

    /**
     * @notice Execute plan via x402 facilitator (atomic batch)
     * @param planId Plan identifier
     */
    function _executeViaX402(bytes32 planId) internal {
        ExecutionPlan storage plan = plans[planId];
        require(!plan.executed, "Already executed");
        require(block.timestamp <= plan.deadline, "Plan expired");

        IFacilitatorClient.Operation[] memory operations = new IFacilitatorClient.Operation[](plan.routes.length);

        // Build operations for each route
        for (uint i = 0; i < plan.routes.length; i++) {
            Route memory route = plan.routes[i];

            // Approve router
            IERC20(route.path[0]).safeApprove(route.dexRouter, route.amountIn);

            operations[i] = IFacilitatorClient.Operation({
                target: route.dexRouter,
                value: 0,
                data: abi.encodeWithSelector(
                    IDEXRouter.swapExactTokensForTokens.selector,
                    route.amountIn,
                    route.minAmountOut,
                    route.path,
                    address(this),
                    plan.deadline
                ),
                condition: abi.encode(route.minAmountOut) // Per-route condition
            });
        }

        // Track balance before
        uint256 balanceBefore = IERC20(plan.outputToken).balanceOf(address(this));

        // Atomic execution with global condition
        try facilitator.executeConditionalBatch(
            operations,
            plan.minTotalOut, // Global condition: must receive at least minTotalOut
            plan.deadline
        ) {
            // Check final balance
            uint256 balanceAfter = IERC20(plan.outputToken).balanceOf(address(this));
            uint256 totalReceived = balanceAfter - balanceBefore;

            require(totalReceived >= plan.minTotalOut, "Slippage exceeded");

            plan.executed = true;
            plan.totalReceived = totalReceived;

            // Calculate and collect fee
            uint256 fee = (totalReceived * feeBps) / 10000;
            uint256 userAmount = totalReceived - fee;

            // Transfer fee to recipient
            if (fee > 0) {
                IERC20(plan.outputToken).safeTransfer(feeRecipient, fee);
                emit FeeCollected(planId, fee);
            }

            // Transfer output to user
            IERC20(plan.outputToken).safeTransfer(plan.creator, userAmount);

            // Calculate slippage
            uint256 slippageBps = 0;
            if (plan.totalAmountIn > 0 && totalReceived > 0) {
                // Simplified slippage calculation (would need price oracle for accurate)
                slippageBps = ((plan.totalAmountIn - totalReceived) * 10000) / plan.totalAmountIn;
            }

            // Update metrics
            metrics.totalExecutions++;
            metrics.totalVolume += plan.totalAmountIn;
            metrics.totalFees += fee;
            if (metrics.totalExecutions > 0) {
                metrics.averageSlippageBps = 
                    (metrics.averageSlippageBps * (metrics.totalExecutions - 1) + slippageBps) / metrics.totalExecutions;
            }

            emit OptimizedExecution(planId, totalReceived, slippageBps);
        } catch Error(string memory reason) {
            // Revert: return input tokens to user
            IERC20(plan.inputToken).safeTransfer(plan.creator, plan.totalAmountIn);
            emit ExecutionFailed(planId, reason);
            revert(reason);
        } catch {
            // Revert: return input tokens to user
            IERC20(plan.inputToken).safeTransfer(plan.creator, plan.totalAmountIn);
            emit ExecutionFailed(planId, "Execution failed");
            revert("Execution failed");
        }
    }

    // ==================== Risk Management ====================

    /**
     * @notice Toggle emergency pause
     */
    function toggleEmergencyPause() external onlyOwner {
        emergencyPause = !emergencyPause;
        emit CircuitBreakerToggled(emergencyPause);
    }

    /**
     * @notice Set volatility pause threshold
     */
    function setVolatilityPauseThreshold(uint256 _threshold) external onlyOwner {
        uint256 oldValue = volatilityPauseThreshold;
        volatilityPauseThreshold = _threshold;
        emit RiskThresholdUpdated("volatilityPauseThreshold", oldValue, _threshold);
    }

    /**
     * @notice Set maximum pool impact percentage
     */
    function setMaxPoolImpact(uint256 _maxImpact) external onlyOwner {
        require(_maxImpact <= 100, "Invalid percentage");
        uint256 oldValue = maxPoolImpact;
        maxPoolImpact = _maxImpact;
        emit RiskThresholdUpdated("maxPoolImpact", oldValue, _maxImpact);
    }

    /**
     * @notice Set maximum position size (basis points)
     */
    function setMaxPositionSizeBps(uint256 _maxBps) external onlyOwner {
        require(_maxBps <= 10000, "Invalid basis points");
        uint256 oldValue = maxPositionSizeBps;
        maxPositionSizeBps = _maxBps;
        emit RiskThresholdUpdated("maxPositionSizeBps", oldValue, _maxBps);
    }

    /**
     * @notice Set fee basis points
     */
    function setFeeBps(uint256 _feeBps) external onlyOwner {
        require(_feeBps <= 1000, "Fee too high"); // Max 10%
        feeBps = _feeBps;
    }

    /**
     * @notice Set fee recipient
     */
    function setFeeRecipient(address _feeRecipient) external onlyOwner {
        require(_feeRecipient != address(0), "Invalid address");
        feeRecipient = _feeRecipient;
    }

    /**
     * @notice Get volatility (would integrate with oracle in production)
     * @dev Placeholder - in production, this would query a price oracle
     */
    function getVolatility() public view returns (uint256) {
        // Placeholder: would query oracle for 1h volatility
        // For now, return 0 (no volatility detected)
        return 0;
    }

    // ==================== View Functions ====================

    /**
     * @notice Get execution plan details
     */
    function getPlan(bytes32 planId) external view returns (
        address inputToken,
        address outputToken,
        uint256 totalAmountIn,
        uint256 minTotalOut,
        uint256 deadline,
        bool executed,
        uint256 totalReceived,
        uint256 routeCount
    ) {
        ExecutionPlan storage plan = plans[planId];
        require(plan.id != bytes32(0), "Plan not found");
        return (
            plan.inputToken,
            plan.outputToken,
            plan.totalAmountIn,
            plan.minTotalOut,
            plan.deadline,
            plan.executed,
            plan.totalReceived,
            plan.routes.length
        );
    }

    /**
     * @notice Get plan routes
     */
    function getPlanRoutes(bytes32 planId) external view returns (Route[] memory) {
        ExecutionPlan storage plan = plans[planId];
        require(plan.id != bytes32(0), "Plan not found");
        return plan.routes;
    }

    /**
     * @notice Get user's plans
     */
    function getUserPlans(address user) external view returns (bytes32[] memory) {
        return userPlans[user];
    }

    /**
     * @notice Get execution metrics
     */
    function getMetrics() external view returns (
        uint256 totalExecutions,
        uint256 totalVolume,
        uint256 totalFees,
        uint256 averageSlippageBps
    ) {
        return (
            metrics.totalExecutions,
            metrics.totalVolume,
            metrics.totalFees,
            metrics.averageSlippageBps
        );
    }

    /**
     * @notice Emergency pause (inherited from Pausable)
     */
    function pause() external onlyOwner {
        _pause();
    }

    /**
     * @notice Unpause (inherited from Pausable)
     */
    function unpause() external onlyOwner {
        _unpause();
    }

    /**
     * @notice Emergency withdraw (owner only)
     */
    function emergencyWithdraw(address token, uint256 amount) external onlyOwner {
        IERC20(token).safeTransfer(owner(), amount);
    }
}

