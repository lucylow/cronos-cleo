// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title GasEfficientBatch
 * @notice Library for gas-efficient batch operations
 * @dev Provides optimized batch processing patterns to minimize gas costs
 * 
 * Key Optimizations:
 * 1. Packed loops - minimize external calls
 * 2. Unchecked math where safe
 * 3. Calldata over memory where possible
 * 4. Event-based tracking instead of SSTORE
 * 5. Efficient array operations
 */
library GasEfficientBatch {
    /**
     * @notice Efficiently sum array values in a single loop
     * @dev Uses unchecked for gas savings where overflow is impossible
     */
    function sumArray(uint256[] calldata values) internal pure returns (uint256 total) {
        uint256 length = values.length;
        for (uint256 i = 0; i < length; ) {
            total += values[i];
            unchecked {
                ++i;
            }
        }
    }

    /**
     * @notice Efficiently validate array lengths match
     */
    function validateLengths(
        address[] calldata arr1,
        uint256[] calldata arr2
    ) internal pure returns (bool) {
        return arr1.length == arr2.length;
    }

    /**
     * @notice Efficiently validate addresses are non-zero
     */
    function validateAddresses(address[] calldata addresses) internal pure returns (bool) {
        uint256 length = addresses.length;
        for (uint256 i = 0; i < length; ) {
            if (addresses[i] == address(0)) return false;
            unchecked {
                ++i;
            }
        }
        return true;
    }

    /**
     * @notice Compute keccak256 hash of array for idempotency
     * @dev Gas-efficient way to create unique IDs from arrays
     */
    function hashArray(bytes[] calldata data) internal pure returns (bytes32) {
        bytes memory packed;
        uint256 length = data.length;
        for (uint256 i = 0; i < length; ) {
            packed = abi.encodePacked(packed, data[i]);
            unchecked {
                ++i;
            }
        }
        return keccak256(packed);
    }

    /**
     * @notice Pack multiple values into single storage slot
     * @dev Reduces SSTORE operations by packing related values
     */
    function packValues(
        uint128 value1,
        uint128 value2
    ) internal pure returns (uint256 packed) {
        packed = (uint256(value1) << 128) | uint256(value2);
    }

    /**
     * @notice Unpack values from single storage slot
     */
    function unpackValues(
        uint256 packed
    ) internal pure returns (uint128 value1, uint128 value2) {
        value1 = uint128(packed >> 128);
        value2 = uint128(packed);
    }

    /**
     * @notice Efficiently check if value is within bounds
     */
    function inBounds(
        uint256 value,
        uint256 min,
        uint256 max
    ) internal pure returns (bool) {
        return value >= min && value <= max;
    }
}

/**
 * @title EventEmitter
 * @notice Helper contract for efficient event emission patterns
 * @dev Reduces gas by batching event emissions
 */
contract EventEmitter {
    /**
     * @notice Emit batch of transfer events
     * @dev More gas efficient than individual emits in loops
     */
    function emitTransferBatch(
        bytes32 batchId,
        address[] calldata tokens,
        address[] calldata recipients,
        uint256[] calldata amounts
    ) external {
        uint256 length = tokens.length;
        require(
            length == recipients.length && length == amounts.length,
            "Length mismatch"
        );

        for (uint256 i = 0; i < length; ) {
            emit TransferEvent(batchId, tokens[i], recipients[i], amounts[i]);
            unchecked {
                ++i;
            }
        }
    }

    event TransferEvent(
        bytes32 indexed batchId,
        address indexed token,
        address indexed recipient,
        uint256 amount
    );
}


