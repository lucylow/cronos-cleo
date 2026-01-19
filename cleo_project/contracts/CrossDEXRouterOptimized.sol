// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@crypto.com/facilitator-client/contracts/interfaces/IFacilitatorClient.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "./GasEfficientBatch.sol";

/**
 * @title CrossDEXRouterOptimized
 * @notice Gas-optimized cross-DEX router with minimal on-chain state
 * @dev Key Improvements:
 *      - Minimal SSTORE: Only essential state (nonces, paused flag)
 *      - Event-based tracking: All execution data in events (off-chain indexing)
 *      - Atomic execution: All routes execute atomically or revert
 *      - Off-chain routing: Complex routing decisions made off-chain, contract validates & executes
 * 
 * Design Principles:
 * 1. Atomicity: All legs in single x402 batch - all succeed or revert
 * 2. Gas Efficiency: Minimize state writes, use events for tracking
 * 3. Minimal Logic: Validate inputs, execute via x402, emit events
 * 4. Off-chain Intelligence: Routing optimization happens off-chain
 */
contract CrossDEXRouterOptimized is Ownable {
    using SafeERC20 for IERC20;
    using GasEfficientBatch for uint256[];

    // ========== IMMUTABLES ==========
    IFacilitatorClient public immutable facilitator;
    address public immutable treasury;

    // ========== MINIMAL STATE (Only essential) ==========
    mapping(address => uint256) public nonces; // Replay protection
    mapping(string => address) public dexRouters; // DEX registry (minimal)
    bool public paused;

    // ========== EVENTS (All tracking via events, no SSTORE) ==========
    event SwapExecuted(
        bytes32 indexed orderId,
        address indexed user,
        address indexed tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 amountOut,
        uint256 routeCount,
        uint256 gasUsed,
        uint256 timestamp
    );

    event SwapFailed(
        bytes32 indexed orderId,
        address indexed user,
        string reason
    );

    event RouteExecuted(
        bytes32 indexed orderId,
        uint256 routeIndex,
        address dexRouter,
        uint256 amountIn,
        uint256 amountOut
    );

    event DEXRegistered(string indexed dexId, address router);
    event DEXUnregistered(string indexed dexId);

    // ========== STRUCTS ==========
    struct Route {
        address dexRouter;      // DEX router address
        address[] path;         // Token path
        uint256 amountIn;       // Input amount for this route
        uint256 minAmountOut;   // Minimum output (slippage protection)
    }

    struct SwapRequest {
        Route[] routes;         // Pre-optimized routes (off-chain decision)
        address tokenIn;        // Input token
        address tokenOut;       // Output token
        uint256 totalAmountIn;  // Total input (must equal sum of route amounts)
        uint256 minTotalOut;    // Minimum total output
        uint256 deadline;       // Execution deadline
    }

    // ========== MODIFIERS ==========
    modifier whenNotPaused() {
        require(!paused, "Paused");
        _;
    }

    // ========== CONSTRUCTOR ==========
    constructor(address _facilitator, address _treasury, address _owner) Ownable(_owner) {
        require(_facilitator != address(0), "Invalid facilitator");
        require(_treasury != address(0), "Invalid treasury");
        facilitator = IFacilitatorClient(_facilitator);
        treasury = _treasury;
    }

    // ========== CORE FUNCTIONS ==========

    /**
     * @notice Execute optimized swap across multiple DEXs atomically
     * @dev All routes execute atomically via x402 - if any fails, entire tx reverts
     *      Minimal state: Only increments nonce (1 SSTORE)
     *      All other data emitted as events for off-chain tracking
     * 
     * @param request Swap request with pre-optimized routes (off-chain decision)
     * @return orderId Unique order identifier
     * @return amountOut Actual output amount
     */
    function executeSwap(
        SwapRequest calldata request
    ) external whenNotPaused returns (bytes32 orderId, uint256 amountOut) {
        // ===== VALIDATION =====
        require(block.timestamp <= request.deadline, "Deadline passed");
        require(request.routes.length > 0 && request.routes.length <= 20, "Invalid route count");
        require(request.tokenIn != address(0) && request.tokenOut != address(0), "Invalid tokens");
        require(request.totalAmountIn > 0 && request.minTotalOut > 0, "Invalid amounts");

        // Validate route amounts sum to total (off-chain should calculate correctly, but verify)
        uint256 routeSum = 0;
        for (uint256 i = 0; i < request.routes.length; ) {
            Route calldata route = request.routes[i];
            require(route.dexRouter != address(0), "Invalid router");
            require(route.path.length >= 2, "Invalid path");
            require(route.path[0] == request.tokenIn, "Path start mismatch");
            require(route.path[route.path.length - 1] == request.tokenOut, "Path end mismatch");
            require(dexRouters[_getDexId(route.dexRouter)] != address(0), "DEX not registered");
            
            unchecked {
                routeSum += route.amountIn;
                ++i;
            }
        }
        require(routeSum == request.totalAmountIn, "Amount mismatch");

        // Generate order ID (deterministic, no SSTORE)
        orderId = keccak256(abi.encodePacked(
            msg.sender,
            request.tokenIn,
            request.tokenOut,
            request.totalAmountIn,
            block.timestamp,
            nonces[msg.sender]
        ));

        // Increment nonce (only SSTORE operation)
        unchecked {
            nonces[msg.sender]++;
        }

        // Transfer input tokens from user
        IERC20(request.tokenIn).safeTransferFrom(
            msg.sender,
            address(this),
            request.totalAmountIn
        );

        // Execute atomically
        uint256 gasStart = gasleft();
        amountOut = _executeRoutesAtomically(orderId, request);

        // Emit success event (all data in event, no SSTORE)
        emit SwapExecuted(
            orderId,
            msg.sender,
            request.tokenIn,
            request.tokenOut,
            request.totalAmountIn,
            amountOut,
            request.routes.length,
            gasStart - gasleft(),
            block.timestamp
        );

        // Transfer output to user
        IERC20(request.tokenOut).safeTransfer(msg.sender, amountOut);
    }

    /**
     * @notice Internal function to execute routes atomically via x402
     * @dev All routes execute in single atomic batch
     *      If any route fails, entire transaction reverts (atomicity guarantee)
     */
    function _executeRoutesAtomically(
        bytes32 orderId,
        SwapRequest calldata request
    ) internal returns (uint256 totalOutput) {
        // Build x402 operations array
        IFacilitatorClient.Operation[] memory operations = new IFacilitatorClient.Operation[](request.routes.length);
        
        // Efficiently build operations array (single loop)
        for (uint256 i = 0; i < request.routes.length; ) {
            Route calldata route = request.routes[i];
            
            // Approve router (if needed - can be optimized further)
            IERC20(route.path[0]).safeApprove(route.dexRouter, route.amountIn);

            // Build swap call data (Uniswap V2 style)
            operations[i] = IFacilitatorClient.Operation({
                target: route.dexRouter,
                value: 0,
                data: abi.encodeWithSelector(
                    0x38ed1739, // swapExactTokensForTokens(uint,uint,address[],address,uint)
                    route.amountIn,
                    route.minAmountOut,
                    route.path,
                    address(this),
                    request.deadline
                ),
                condition: abi.encode(route.minAmountOut) // Per-route condition
            });

            unchecked {
                ++i;
            }
        }

        // Track balance before execution
        uint256 balanceBefore = IERC20(request.tokenOut).balanceOf(address(this));

        // Execute atomically via x402 facilitator
        // All routes succeed or entire transaction reverts
        try facilitator.executeConditionalBatch(
            operations,
            abi.encode(request.minTotalOut), // Global condition: minimum total output
            request.deadline
        ) returns (bytes[] memory) {
            // All routes succeeded atomically
            uint256 balanceAfter = IERC20(request.tokenOut).balanceOf(address(this));
            totalOutput = balanceAfter - balanceBefore;

            require(totalOutput >= request.minTotalOut, "Slippage exceeded");

            // Emit route events (for off-chain tracking)
            for (uint256 i = 0; i < request.routes.length; ) {
                // Note: Individual route outputs not tracked on-chain (query events off-chain)
                emit RouteExecuted(
                    orderId,
                    i,
                    request.routes[i].dexRouter,
                    request.routes[i].amountIn,
                    0 // Calculate from events off-chain
                );
                unchecked {
                    ++i;
                }
            }

        } catch Error(string memory reason) {
            // Atomic failure - refund input tokens
            IERC20(request.tokenIn).safeTransfer(msg.sender, request.totalAmountIn);
            emit SwapFailed(orderId, msg.sender, reason);
            revert(string(abi.encodePacked("Swap failed: ", reason)));
        } catch {
            // Atomic failure - refund input tokens
            IERC20(request.tokenIn).safeTransfer(msg.sender, request.totalAmountIn);
            emit SwapFailed(orderId, msg.sender, "Execution failed");
            revert("Swap execution failed");
        }
    }

    // ========== ADMIN FUNCTIONS ==========

    /**
     * @notice Register DEX router
     */
    function registerDEX(string calldata dexId, address router) external onlyOwner {
        require(router != address(0), "Invalid router");
        require(bytes(dexId).length > 0, "Invalid DEX ID");
        dexRouters[dexId] = router;
        routerToDexId[router] = dexId; // Store reverse mapping
        emit DEXRegistered(dexId, router);
    }

    /**
     * @notice Unregister DEX router
     */
    function unregisterDEX(string calldata dexId) external onlyOwner {
        address router = dexRouters[dexId];
        require(router != address(0), "DEX not registered");
        delete dexRouters[dexId];
        delete routerToDexId[router]; // Clean up reverse mapping
        emit DEXUnregistered(dexId);
    }

    /**
     * @notice Pause contract
     */
    function pause() external onlyOwner {
        paused = true;
    }

    /**
     * @notice Unpause contract
     */
    function unpause() external onlyOwner {
        paused = false;
    }

    // ========== HELPER FUNCTIONS ==========

    // Reverse mapping: router address -> dexId (for efficient lookup)
    mapping(address => string) private routerToDexId;

    /**
     * @notice Get DEX ID from router address
     */
    function _getDexId(address router) internal view returns (string memory) {
        string memory dexId = routerToDexId[router];
        require(bytes(dexId).length > 0, "Router not registered");
        return dexId;
    }

    // ========== VIEW FUNCTIONS ==========

    /**
     * @notice Check if DEX is registered
     */
    function isDEXRegistered(string calldata dexId) external view returns (bool) {
        return dexRouters[dexId] != address(0);
    }

    /**
     * @notice Get DEX router address
     */
    function getDEXRouter(string calldata dexId) external view returns (address) {
        return dexRouters[dexId];
    }
}

