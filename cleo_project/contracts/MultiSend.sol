// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@crypto.com/facilitator-client/contracts/interfaces/IFacilitatorClient.sol";

/**
 * @title CronosMultiSend
 * @notice Gas-optimized multi-send contract for batching multiple transfers/swaps
 *         Supports native CRO and ERC20 tokens
 *         Designed for multi-leg transaction batching on Cronos
 */
contract CronosMultiSend is Ownable {
    using SafeERC20 for IERC20;

    // x402 Integration for atomic execution
    IFacilitatorClient public immutable facilitator;

    // Transfer structure
    struct Transfer {
        address token;      // Token address (address(0) for native CRO)
        address recipient;
        uint256 amount;
    }

    // Batch execution structure
    struct BatchTransfer {
        Transfer[] transfers;
        uint256 deadline;
    }

    // Events
    event BatchExecuted(
        bytes32 indexed batchId,
        uint256 indexed transferCount,
        uint256 totalGasUsed
    );

    event TransferExecuted(
        bytes32 indexed batchId,
        address indexed token,
        address indexed recipient,
        uint256 amount
    );

    event BatchFailed(
        bytes32 indexed batchId,
        string reason
    );

    constructor(address _facilitator, address _owner) Ownable(_owner) {
        require(_facilitator != address(0), "Invalid facilitator");
        facilitator = IFacilitatorClient(_facilitator);
    }

    /**
     * @notice Execute multiple native CRO transfers in a single transaction
     * @param recipients Array of recipient addresses
     * @param amounts Array of amounts (must match recipients length)
     */
    function multiNativeSend(
        address[] calldata recipients,
        uint256[] calldata amounts
    ) external payable {
        require(recipients.length == amounts.length, "Length mismatch");
        require(recipients.length > 0, "Empty batch");

        uint256 total;
        for (uint256 i = 0; i < amounts.length; i++) {
            total += amounts[i];
        }
        require(msg.value == total, "Wrong total");

        bytes32 batchId = keccak256(abi.encodePacked(block.timestamp, msg.sender, recipients.length));

        for (uint256 i = 0; i < recipients.length; i++) {
            (bool sent, ) = recipients[i].call{value: amounts[i]}("");
            require(sent, "Send failed");
            
            emit TransferExecuted(batchId, address(0), recipients[i], amounts[i]);
        }

        emit BatchExecuted(batchId, recipients.length, gasleft());
    }

    /**
     * @notice Execute multiple ERC20 transfers in a single transaction
     * @param token Token contract address
     * @param recipients Array of recipient addresses
     * @param amounts Array of amounts
     */
    function multiTokenSend(
        address token,
        address[] calldata recipients,
        uint256[] calldata amounts
    ) external {
        require(recipients.length == amounts.length, "Length mismatch");
        require(recipients.length > 0, "Empty batch");
        require(token != address(0), "Invalid token");

        IERC20 tokenContract = IERC20(token);
        bytes32 batchId = keccak256(abi.encodePacked(block.timestamp, msg.sender, recipients.length));

        uint256 total;
        for (uint256 i = 0; i < amounts.length; i++) {
            total += amounts[i];
        }

        // Transfer total from sender to contract
        tokenContract.safeTransferFrom(msg.sender, address(this), total);

        // Distribute to recipients
        for (uint256 i = 0; i < recipients.length; i++) {
            tokenContract.safeTransfer(recipients[i], amounts[i]);
            emit TransferExecuted(batchId, token, recipients[i], amounts[i]);
        }

        emit BatchExecuted(batchId, recipients.length, gasleft());
    }

    /**
     * @notice Execute mixed batch (native + ERC20) via x402 facilitator for atomicity
     * @param batchId Unique batch identifier
     * @param transfers Array of transfers (can mix native and ERC20)
     * @param deadline Execution deadline
     */
    function executeBatchAtomic(
        bytes32 batchId,
        Transfer[] calldata transfers,
        uint256 deadline
    ) external {
        require(transfers.length > 0, "Empty batch");
        require(block.timestamp <= deadline, "Deadline passed");

        // Build operations for x402 facilitator
        IFacilitatorClient.Operation[] memory operations = new IFacilitatorClient.Operation[](transfers.length);

        for (uint256 i = 0; i < transfers.length; i++) {
            Transfer memory transfer = transfers[i];

            if (transfer.token == address(0)) {
                // Native CRO transfer
                operations[i] = IFacilitatorClient.Operation({
                    target: transfer.recipient,
                    value: transfer.amount,
                    data: ""
                });
            } else {
                // ERC20 transfer
                bytes memory data = abi.encodeWithSelector(
                    IERC20.transfer.selector,
                    transfer.recipient,
                    transfer.amount
                );
                
                operations[i] = IFacilitatorClient.Operation({
                    target: transfer.token,
                    value: 0,
                    data: data
                });
            }
        }

        // Execute via x402 facilitator (atomic batch)
        try facilitator.executeConditionalBatch(
            operations,
            abi.encode(batchId), // Condition data
            deadline
        ) {
            // All transfers succeeded atomically
            for (uint256 i = 0; i < transfers.length; i++) {
                emit TransferExecuted(
                    batchId,
                    transfers[i].token,
                    transfers[i].recipient,
                    transfers[i].amount
                );
            }

            emit BatchExecuted(batchId, transfers.length, gasleft());
        } catch Error(string memory reason) {
            emit BatchFailed(batchId, reason);
            revert(reason);
        } catch {
            emit BatchFailed(batchId, "Execution failed");
            revert("Execution failed");
        }
    }

    /**
     * @notice Estimate gas savings from batching
     * @param transferCount Number of transfers in batch
     * @return estimatedGas Estimated gas for batch
     * @return individualGas Estimated gas if done individually
     * @return gasSaved Estimated gas saved
     */
    function estimateGasSavings(uint256 transferCount) external pure returns (
        uint256 estimatedGas,
        uint256 individualGas,
        uint256 gasSaved
    ) {
        // Base transaction cost
        uint256 baseGas = 21000;
        
        // Per-transfer cost in batch (much lower than individual)
        uint256 perTransferGas = 5000;
        
        // Individual transaction cost per transfer
        uint256 individualTxGas = 65000; // Base + transfer operation
        
        estimatedGas = baseGas + (transferCount * perTransferGas);
        individualGas = transferCount * individualTxGas;
        gasSaved = individualGas > estimatedGas ? individualGas - estimatedGas : 0;
    }

    /**
     * @notice Emergency withdraw (owner only)
     */
    function emergencyWithdraw(address token, uint256 amount) external onlyOwner {
        if (token == address(0)) {
            payable(owner()).transfer(amount);
        } else {
            IERC20(token).safeTransfer(owner(), amount);
        }
    }

    // Receive native CRO
    receive() external payable {}
}

