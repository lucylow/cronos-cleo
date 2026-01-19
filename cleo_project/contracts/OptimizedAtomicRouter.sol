// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@crypto.com/facilitator-client/contracts/interfaces/IFacilitatorClient.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/utils/cryptography/EIP712.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title OptimizedAtomicRouter
 * @notice Gas-optimized atomic router with meta-transaction support
 * @dev Implements:
 *      - Atomic multi-leg execution (all succeed or revert)
 *      - Minimal SSTORE operations (favor events)
 *      - EIP-712 meta-transactions for relayer support
 *      - Off-chain decisioning (on-chain only validates & executes)
 * 
 * Design Principles:
 * 1. Atomicity: All legs execute atomically via x402 facilitator
 * 2. Gas Efficiency: Minimize state writes, use events for tracking
 * 3. Relayer Support: EIP-712 signatures enable meta-transactions
 * 4. Minimal Logic: Complex routing decided off-chain, contract only validates & executes
 */
contract OptimizedAtomicRouter is Ownable, EIP712 {
    using SafeERC20 for IERC20;
    using ECDSA for bytes32;

    // ========== IMMUTABLES ==========
    IFacilitatorClient public immutable facilitator;

    // ========== CONSTANTS ==========
    bytes32 private constant EXECUTE_BATCH_TYPEHASH = keccak256(
        "ExecuteBatch(address user,Leg[] legs,uint256 deadline,uint256 nonce)"
        "Leg(address target,uint256 value,bytes data)"
    );
    bytes32 private constant LEG_TYPEHASH = keccak256(
        "Leg(address target,uint256 value,bytes data)"
    );
    uint256 private constant MAX_LEGS = 50; // Prevent gas limit issues

    // ========== STATE VARIABLES (MINIMAL) ==========
    mapping(address => uint256) public nonces; // Only state needed for replay protection
    bool public paused;

    // ========== EVENTS (NO SSTORE - Events for tracking) ==========
    event BatchExecuted(
        bytes32 indexed batchId,
        address indexed user,
        uint256 legCount,
        uint256 totalInput,
        uint256 totalOutput,
        uint256 gasUsed
    );

    event BatchFailed(
        bytes32 indexed batchId,
        address indexed user,
        string reason
    );

    event LegExecuted(
        bytes32 indexed batchId,
        uint256 legIndex,
        address target,
        bool success
    );

    event MetaTransactionExecuted(
        bytes32 indexed batchId,
        address indexed user,
        address indexed relayer
    );

    // ========== STRUCTS ==========
    struct Leg {
        address target;        // Contract to call
        uint256 value;         // Native value to send
        bytes data;            // Calldata
    }

    struct BatchRequest {
        address user;          // Original user (for meta-tx)
        Leg[] legs;            // Array of legs to execute
        uint256 deadline;      // Execution deadline
        uint256 nonce;         // Replay protection
        bytes signature;       // EIP-712 signature (if meta-tx)
    }

    struct ExecutionResult {
        bool success;
        uint256 totalOutput;
        uint256 gasUsed;
        bytes revertReason;
    }

    // ========== MODIFIERS ==========
    modifier whenNotPaused() {
        require(!paused, "Contract paused");
        _;
    }

    // ========== CONSTRUCTOR ==========
    constructor(
        address _facilitator,
        address _owner
    ) Ownable(_owner) EIP712("OptimizedAtomicRouter", "1") {
        require(_facilitator != address(0), "Invalid facilitator");
        facilitator = IFacilitatorClient(_facilitator);
    }

    // ========== CORE EXECUTION FUNCTIONS ==========

    /**
     * @notice Execute atomic batch (direct call from user)
     * @dev All legs execute atomically via x402 - if any fails, entire tx reverts
     * @param legs Array of legs to execute
     * @param deadline Execution deadline
     * @return result Execution result
     */
    function executeBatch(
        Leg[] calldata legs,
        uint256 deadline
    ) external payable whenNotPaused returns (ExecutionResult memory result) {
        require(block.timestamp <= deadline, "Deadline passed");
        require(legs.length > 0 && legs.length <= MAX_LEGS, "Invalid leg count");

        bytes32 batchId = _computeBatchId(msg.sender, legs, deadline, nonces[msg.sender]);
        nonces[msg.sender]++; // Increment nonce (only SSTORE)

        return _executeBatchInternal(batchId, msg.sender, legs, deadline);
    }

    /**
     * @notice Execute atomic batch via meta-transaction (relayer)
     * @dev Relayer pays gas, user signs request with EIP-712
     * @param request Batch request with signature
     * @return result Execution result
     */
    function executeBatchMeta(
        BatchRequest calldata request
    ) external whenNotPaused returns (ExecutionResult memory result) {
        require(block.timestamp <= request.deadline, "Deadline passed");
        require(request.legs.length > 0 && request.legs.length <= MAX_LEGS, "Invalid leg count");
        require(request.nonce == nonces[request.user], "Invalid nonce");

        // Verify EIP-712 signature
        bytes32 batchId = _computeBatchId(
            request.user,
            request.legs,
            request.deadline,
            request.nonce
        );
        _verifySignature(batchId, request.user, request.signature);

        nonces[request.user]++; // Increment nonce (only SSTORE)

        emit MetaTransactionExecuted(batchId, request.user, msg.sender);

        return _executeBatchInternal(batchId, request.user, request.legs, request.deadline);
    }

    /**
     * @notice Internal execution logic (shared by direct and meta-tx)
     * @dev Executes all legs atomically via x402 facilitator
     *      If any leg fails, entire transaction reverts (atomicity guarantee)
     */
    function _executeBatchInternal(
        bytes32 batchId,
        address user,
        Leg[] calldata legs,
        uint256 deadline
    ) internal returns (ExecutionResult memory result) {
        uint256 gasStart = gasleft();

        // Build x402 operations array
        IFacilitatorClient.Operation[] memory operations = new IFacilitatorClient.Operation[](legs.length);
        
        // Efficiently build operations in single loop
        for (uint256 i = 0; i < legs.length; i++) {
            operations[i] = IFacilitatorClient.Operation({
                target: legs[i].target,
                value: legs[i].value,
                data: legs[i].data,
                condition: "" // Per-leg conditions handled off-chain
            });
        }

        // Execute atomically via x402 facilitator
        // If ANY leg fails, entire transaction reverts (atomicity)
        try facilitator.executeConditionalBatch(
            operations,
            abi.encode(deadline), // Global condition: deadline check
            deadline
        ) returns (bytes[] memory results) {
            // All legs succeeded atomically
            result.success = true;
            result.gasUsed = gasStart - gasleft();

            // Emit events for each leg (no SSTORE)
            for (uint256 i = 0; i < legs.length; i++) {
                emit LegExecuted(batchId, i, legs[i].target, true);
            }

            // Calculate total output (if tracking needed, do it off-chain via events)
            // No SSTORE - all data available in events
            emit BatchExecuted(
                batchId,
                user,
                legs.length,
                0, // totalInput calculated off-chain
                0, // totalOutput calculated off-chain
                result.gasUsed
            );

        } catch Error(string memory reason) {
            // Execution failed - entire batch reverted (atomicity)
            result.success = false;
            result.revertReason = bytes(reason);
            result.gasUsed = gasStart - gasleft();

            emit BatchFailed(batchId, user, reason);
            revert(string(abi.encodePacked("Batch execution failed: ", reason)));

        } catch (bytes memory lowLevelData) {
            // Low-level revert
            result.success = false;
            result.revertReason = lowLevelData;
            result.gasUsed = gasStart - gasleft();

            emit BatchFailed(batchId, user, "Low-level revert");
            revert("Batch execution failed");
        }
    }

    // ========== EIP-712 SIGNATURE VERIFICATION ==========

    /**
     * @notice Verify EIP-712 signature for meta-transaction
     */
    function _verifySignature(
        bytes32 batchId,
        address signer,
        bytes calldata signature
    ) internal view {
        bytes32 digest = _hashTypedDataV4(batchId);
        address recovered = digest.recover(signature);
        require(recovered == signer, "Invalid signature");
    }

    /**
     * @notice Compute batch ID for signature verification
     */
    function _computeBatchId(
        address user,
        Leg[] calldata legs,
        uint256 deadline,
        uint256 nonce
    ) internal pure returns (bytes32) {
        bytes32 legsHash = keccak256(abi.encode(legs));
        return keccak256(abi.encodePacked(user, legsHash, deadline, nonce));
    }

    /**
     * @notice Get current nonce for a user (for off-chain signature generation)
     */
    function getNonce(address user) external view returns (uint256) {
        return nonces[user];
    }

    // ========== ADMIN FUNCTIONS ==========

    /**
     * @notice Pause contract (emergency only)
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

    // ========== VIEW FUNCTIONS ==========

    /**
     * @notice Get domain separator for EIP-712
     */
    function getDomainSeparator() external view returns (bytes32) {
        return _domainSeparatorV4();
    }

    /**
     * @notice Verify a batch signature without executing
     */
    function verifyBatchSignature(
        address user,
        Leg[] calldata legs,
        uint256 deadline,
        uint256 nonce,
        bytes calldata signature
    ) external view returns (bool) {
        bytes32 batchId = _computeBatchId(user, legs, deadline, nonce);
        bytes32 digest = _hashTypedDataV4(batchId);
        address recovered = digest.recover(signature);
        return recovered == user;
    }
}

/**
 * @title BatchExecutorHelper
 * @notice Helper library for efficient batch operations
 * @dev Off-chain helper functions for building batches
 */
library BatchExecutorHelper {
    /**
     * @notice Calculate optimal gas estimate for batch
     */
    function estimateGas(
        uint256 legCount
    ) internal pure returns (uint256) {
        // Base cost + per-leg cost
        uint256 baseGas = 21000;
        uint256 perLegGas = 50000;
        return baseGas + (legCount * perLegGas);
    }

    /**
     * @notice Validate leg array (off-chain helper)
     */
    function validateLegs(
        OptimizedAtomicRouter.Leg[] memory legs
    ) internal pure returns (bool) {
        if (legs.length == 0 || legs.length > 50) return false;
        for (uint256 i = 0; i < legs.length; i++) {
            if (legs[i].target == address(0)) return false;
        }
        return true;
    }
}

