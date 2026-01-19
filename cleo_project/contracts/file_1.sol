// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@crypto.com/facilitator-client/contracts/interfaces/IFacilitatorClient.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title CrossDEXRouter
 * @notice Intelligent routing contract that splits large trades across multiple DEXs
 *         using x402 facilitator for atomic execution
 */
contract CrossDEXRouter is Ownable {
    using SafeERC20 for IERC20;

    // x402 Integration
    IFacilitatorClient public immutable facilitator;

    // DEX Registry
    struct DEXInfo {
        address router;
        bytes4 swapSelector; // Function selector for swap function
        bool isActive;
        string name;
    }

    mapping(string => DEXInfo) public dexRegistry; // "vvs", "cronaswap", "mm_finance"
    string[] public registeredDexIds;

    // Order Management
    struct SplitOrder {
        address user;
        address tokenIn;
        address tokenOut;
        uint256 totalAmountIn;
        uint256 minTotalOut;
        uint256 deadline;
        bytes32 orderId;
        bool executed;
        uint256 totalReceived;
    }

    mapping(bytes32 => SplitOrder) public orders;
    mapping(bytes32 => RouteSplit[]) public orderRoutes;

    struct RouteSplit {
        string dexId;
        address[] path;
        uint256 amountIn;
        uint256 minAmountOut;
    }

    // Events
    event OrderCreated(bytes32 indexed orderId, address indexed user, uint256 totalAmountIn);
    event OrderExecuted(bytes32 indexed orderId, uint256 totalReceived);
    event OrderFailed(bytes32 indexed orderId, string reason);
    event DEXRegistered(string indexed dexId, address router);
    event DEXDeactivated(string indexed dexId);

    constructor(address _facilitator, address _owner) Ownable(_owner) {
        require(_facilitator != address(0), "Invalid facilitator");
        facilitator = IFacilitatorClient(_facilitator);
        
        // Initialize with common Cronos DEXs
        _registerDEX("vvs", 0x145863Eb42Cf62847A6Ca784e6416C1682B1b2Ae, 0x38ed1739, "VVS Finance");
        _registerDEX("cronaswap", 0xcd7d16fB918511BF72679eC3eC2f2f39c33C2F45, 0x38ed1739, "CronaSwap");
        _registerDEX("mm_finance", 0x145677FC4d9b8F19B5D56d1820c48e0443049a30, 0x38ed1739, "MM Finance");
    }

    /**
     * @notice Register a new DEX router
     */
    function registerDEX(
        string calldata dexId,
        address router,
        bytes4 swapSelector,
        string calldata name
    ) external onlyOwner {
        _registerDEX(dexId, router, swapSelector, name);
    }

    function _registerDEX(string memory dexId, address router, bytes4 swapSelector, string memory name) internal {
        require(router != address(0), "Invalid router");
        dexRegistry[dexId] = DEXInfo({
            router: router,
            swapSelector: swapSelector,
            isActive: true,
            name: name
        });
        
        // Track registered DEXs
        bool exists = false;
        for (uint i = 0; i < registeredDexIds.length; i++) {
            if (keccak256(bytes(registeredDexIds[i])) == keccak256(bytes(dexId))) {
                exists = true;
                break;
            }
        }
        if (!exists) {
            registeredDexIds.push(dexId);
        }
        
        emit DEXRegistered(dexId, router);
    }

    /**
     * @notice Deactivate a DEX (for emergency or maintenance)
     */
    function deactivateDEX(string calldata dexId) external onlyOwner {
        require(dexRegistry[dexId].router != address(0), "DEX not registered");
        dexRegistry[dexId].isActive = false;
        emit DEXDeactivated(dexId);
    }

    /**
     * @notice Core function: Execute optimized swap across multiple DEXs atomically
     * @param routes Array of route splits across different DEXs
     * @param totalAmountIn Total input amount (must match sum of route amounts)
     * @param tokenIn Input token address
     * @param tokenOut Output token address
     * @param minTotalOut Minimum total output (slippage protection)
     * @param deadline Transaction deadline
     * @return orderId Unique order identifier
     */
    function executeOptimizedSwap(
        RouteSplit[] calldata routes,
        uint256 totalAmountIn,
        address tokenIn,
        address tokenOut,
        uint256 minTotalOut,
        uint256 deadline
    ) external payable returns (bytes32 orderId) {
        require(deadline > block.timestamp, "Deadline passed");
        require(routes.length > 0, "No routes provided");
        require(tokenIn != address(0) && tokenOut != address(0), "Invalid tokens");
        
        // Validate route amounts sum to total
        uint256 routeSum = 0;
        for (uint i = 0; i < routes.length; i++) {
            require(dexRegistry[routes[i].dexId].isActive, "DEX not active");
            require(routes[i].path.length >= 2, "Invalid path");
            require(routes[i].path[0] == tokenIn, "Path mismatch");
            require(routes[i].path[routes[i].path.length - 1] == tokenOut, "Path mismatch");
            routeSum += routes[i].amountIn;
        }
        require(routeSum == totalAmountIn, "Amount mismatch");

        orderId = keccak256(abi.encodePacked(
            msg.sender,
            block.timestamp,
            block.number,
            totalAmountIn,
            tokenIn,
            tokenOut
        ));

        // Store order
        orders[orderId] = SplitOrder({
            user: msg.sender,
            tokenIn: tokenIn,
            tokenOut: tokenOut,
            totalAmountIn: totalAmountIn,
            minTotalOut: minTotalOut,
            deadline: deadline,
            orderId: orderId,
            executed: false,
            totalReceived: 0
        });

        // Store routes
        for (uint i = 0; i < routes.length; i++) {
            orderRoutes[orderId].push(routes[i]);
        }

        // Transfer tokens from user
        IERC20(tokenIn).safeTransferFrom(msg.sender, address(this), totalAmountIn);

        emit OrderCreated(orderId, msg.sender, totalAmountIn);

        // Execute routes atomically via x402
        _executeRoutes(orderId);
    }

    /**
     * @notice Execute routes for an order using x402 facilitator
     * @param orderId Order identifier
     */
    function _executeRoutes(bytes32 orderId) internal {
        SplitOrder storage order = orders[orderId];
        require(!order.executed, "Already executed");
        require(order.deadline >= block.timestamp, "Order expired");

        RouteSplit[] storage routes = orderRoutes[orderId];
        require(routes.length > 0, "No routes");

        // Build operations for x402
        IFacilitatorClient.Operation[] memory operations = _buildOperations(orderId, routes);

        // Track balance before
        uint256 balanceBefore = IERC20(order.tokenOut).balanceOf(address(this));

        // Execute via x402 facilitator (atomic batch)
        try facilitator.executeConditionalBatch(
            operations,
            order.minTotalOut, // Condition: must receive at least minTotalOut
            order.deadline
        ) {
            // Check final balance
            uint256 balanceAfter = IERC20(order.tokenOut).balanceOf(address(this));
            uint256 totalReceived = balanceAfter - balanceBefore;

            require(totalReceived >= order.minTotalOut, "Slippage exceeded");

            order.executed = true;
            order.totalReceived = totalReceived;

            // Transfer output tokens to user
            IERC20(order.tokenOut).safeTransfer(order.user, totalReceived);

            emit OrderExecuted(orderId, totalReceived);
        } catch Error(string memory reason) {
            // Revert token transfer on failure
            IERC20(order.tokenIn).safeTransfer(order.user, order.totalAmountIn);
            emit OrderFailed(orderId, reason);
            revert(reason);
        } catch {
            // Revert token transfer on failure
            IERC20(order.tokenIn).safeTransfer(order.user, order.totalAmountIn);
            emit OrderFailed(orderId, "Execution failed");
            revert("Execution failed");
        }
    }

    /**
     * @notice Build x402 operations from route splits
     */
    function _buildOperations(
        bytes32 orderId,
        RouteSplit[] storage routes
    ) internal view returns (IFacilitatorClient.Operation[] memory) {
        SplitOrder storage order = orders[orderId];
        IFacilitatorClient.Operation[] memory operations = new IFacilitatorClient.Operation[](routes.length);

        for (uint i = 0; i < routes.length; i++) {
            RouteSplit storage route = routes[i];
            DEXInfo storage dex = dexRegistry[route.dexId];
            require(dex.isActive, "DEX inactive");

            // Approve router to spend tokens
            IERC20(route.path[0]).approve(dex.router, route.amountIn);

            // Build swap call data (Uniswap V2 style: swapExactTokensForTokens)
            // Function signature: swapExactTokensForTokens(uint amountIn, uint amountOutMin, address[] calldata path, address to, uint deadline)
            operations[i] = IFacilitatorClient.Operation({
                target: dex.router,
                value: 0,
                data: abi.encodeWithSelector(
                    dex.swapSelector,
                    route.amountIn,
                    route.minAmountOut,
                    route.path,
                    address(this),
                    order.deadline
                ),
                condition: abi.encode(route.minAmountOut) // Per-route minimum output condition
            });
        }

        return operations;
    }

    /**
     * @notice Get order details
     */
    function getOrder(bytes32 orderId) external view returns (SplitOrder memory, RouteSplit[] memory) {
        return (orders[orderId], orderRoutes[orderId]);
    }

    /**
     * @notice Get registered DEX count
     */
    function getRegisteredDEXCount() external view returns (uint256) {
        return registeredDexIds.length;
    }

    /**
     * @notice Emergency withdraw (owner only)
     */
    function emergencyWithdraw(address token, uint256 amount) external onlyOwner {
        IERC20(token).safeTransfer(owner(), amount);
    }
}
