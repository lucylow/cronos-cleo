
// SPDX-License-Identifier: MIT

pragma solidity \^0.8.20;

import
\"\@crypto.com/facilitator-client/contracts/interfaces/IFacilitatorClient.sol\";

import \"\@openzeppelin/contracts/token/ERC20/IERC20.sol\";

import \"\@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol\";

contract CrossDEXRouter {

using SafeERC20 for IERC20;

// x402 Integration

IFacilitatorClient public immutable facilitator;

// DEX Registry

struct DEXInfo {

address router;

bytes4 swapSelector;

bool isActive;

}

mapping(string =\> DEXInfo) public dexRegistry; // \"vvs\",
\"cronaswap\", etc.

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

}

mapping(bytes32 =\> SplitOrder) public orders;

mapping(bytes32 =\> RouteSplit\[\]) public orderRoutes;

struct RouteSplit {

string dexId;

address\[\] path;

uint256 amountIn;

uint256 minAmountOut;

}

event OrderCreated(bytes32 indexed orderId, address indexed user);

event OrderExecuted(bytes32 indexed orderId, uint256 totalReceived);

constructor(address _facilitator) {

facilitator = IFacilitatorClient(_facilitator);

}

// Core function using x402 conditional execution

function executeOptimizedSwap(

RouteSplit\[\] calldata routes,

uint256 totalAmountIn,

address tokenIn,

address tokenOut,

uint256 minTotalOut,

uint256 deadline

) external payable returns (bytes32 orderId) {

require(deadline \> block.timestamp, \"Deadline passed\");

require(routes.length \> 0, \"No routes provided\");

orderId = keccak256(abi.encodePacked(msg.sender, block.timestamp,
totalAmountIn));

// Store order

orders\[orderId\] = SplitOrder({

user: msg.sender,

tokenIn: tokenIn,

tokenOut: tokenOut,

totalAmountIn: totalAmountIn,

minTotalOut: minTotalOut,

deadline: deadline,

orderId: orderId,

executed: false

});

// Store routes

for (uint i = 0; i \< routes.length; i++) {

orderRoutes\[orderId\].push(routes\[i\]);

}

// Transfer tokens from user (using Permit2 for gas efficiency)

IERC20(tokenIn).safeTransferFrom(msg.sender, address(this),
totalAmountIn);

emit OrderCreated(orderId, msg.sender);

// The actual execution will be triggered by the AI Agent via x402

// This separation allows for pre-execution validation

}

// Called by AI Agent via x402

function _executeRoutes(bytes32 orderId) internal {

require(!orders\[orderId\].executed, \"Already executed\");

require(orders\[orderId\].deadline \>= block.timestamp, \"Order
expired\");

SplitOrder storage order = orders\[orderId\];

RouteSplit\[\] storage routes = orderRoutes\[orderId\];

uint256 totalReceived = 0;

// x402 Conditional Execution Block

facilitator.executeConditionalBatch(

_buildOperations(orderId, routes),

order.minTotalOut, // Condition: must receive at least this much

order.deadline

);

orders\[orderId\].executed = true;

emit OrderExecuted(orderId, totalReceived);

}

function _buildOperations(

bytes32 orderId,

RouteSplit\[\] storage routes

) internal view returns (IFacilitatorClient.Operation\[\] memory) {

IFacilitatorClient.Operation\[\] memory operations = new
IFacilitatorClient.Operation\[\](routes.length);

for (uint i = 0; i \< routes.length; i++) {

RouteSplit storage route = routes\[i\];

DEXInfo storage dex = dexRegistry\[route.dexId\];

operations\[i\] = IFacilitatorClient.Operation({

target: dex.router,

value: 0,

data: abi.encodeWithSelector(

dex.swapSelector,

route.amountIn,

route.minAmountOut,

route.path,

address(this),

block.timestamp + 1800 // 30 minute deadline for each swap

),

condition: bytes(\"\") // Can add per-route conditions

});

}

return operations;

}

}

