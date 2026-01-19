// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @dev ReentrancyGuard to prevent reentrancy attacks
 */
abstract contract ReentrancyGuard {
    uint256 private constant _NOT_ENTERED = 1;
    uint256 private constant _ENTERED = 2;
    uint256 private _status;

    constructor() {
        _status = _NOT_ENTERED;
    }

    modifier nonReentrant() {
        require(_status != _ENTERED, "ReentrancyGuard: reentrant call");
        _status = _ENTERED;
        _;
        _status = _NOT_ENTERED;
    }
}

interface IERC20 {
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function transfer(address to, uint256 amount) external returns (bool);
    function decimals() external view returns (uint8);
    function balanceOf(address account) external view returns (uint256);
}

/**
 * @title CronosPaymentProcessor
 * @dev Smart contract for accepting native CRO and ERC-20 token payments on Cronos
 * @notice Features reentrancy protection and improved security
 */
contract CronosPaymentProcessor is ReentrancyGuard {
    address public owner;
    uint256 public paymentCount;
    bool public paused;

    struct Payment {
        address payer;
        address token; // address(0) for native CRO
        uint256 amount;
        uint256 timestamp;
    }

    mapping(uint256 => Payment) public payments;

    event PaymentReceived(
        uint256 indexed paymentId,
        address indexed payer,
        address token,
        uint256 amount,
        uint256 timestamp
    );
    event Withdrawn(
        address indexed to,
        address token,
        uint256 amount,
        uint256 timestamp
    );
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);
    event Paused(address indexed account);
    event Unpaused(address indexed account);

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    modifier whenNotPaused() {
        require(!paused, "Contract paused");
        _;
    }

    constructor() {
        owner = msg.sender;
        paused = false;
    }

    /**
     * @dev Transfer ownership of the contract
     */
    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "Zero address");
        address oldOwner = owner;
        owner = newOwner;
        emit OwnershipTransferred(oldOwner, newOwner);
    }

    /**
     * @dev Pause the contract to prevent payments
     */
    function pause() external onlyOwner {
        require(!paused, "Already paused");
        paused = true;
        emit Paused(msg.sender);
    }

    /**
     * @dev Unpause the contract
     */
    function unpause() external onlyOwner {
        require(paused, "Not paused");
        paused = false;
        emit Unpaused(msg.sender);
    }

    /**
     * @dev Accept native CRO payment
     * @return paymentId The ID of the payment record
     */
    function payNative() external payable nonReentrant whenNotPaused returns (uint256) {
        require(msg.value > 0, "Zero payment");
        paymentCount += 1;
        payments[paymentCount] = Payment(
            msg.sender,
            address(0),
            msg.value,
            block.timestamp
        );
        emit PaymentReceived(paymentCount, msg.sender, address(0), msg.value, block.timestamp);
        return paymentCount;
    }

    /**
     * @dev Accept ERC-20 token payment
     * @param token The ERC-20 token contract address
     * @param amount The amount to pay (in token units)
     * @return paymentId The ID of the payment record
     * @notice Buyer must approve this contract for `amount` before calling this function
     */
    function payWithERC20(address token, uint256 amount) external nonReentrant whenNotPaused returns (uint256) {
        require(token != address(0), "Token zero address");
        require(amount > 0, "Zero amount");
        
        // Check balance before transfer
        uint256 balanceBefore = IERC20(token).balanceOf(address(this));
        
        // Transfer tokens from payer to THIS contract
        bool success = IERC20(token).transferFrom(msg.sender, address(this), amount);
        require(success, "Transfer failed");
        
        // Verify the transfer was successful (handle tokens with fees)
        uint256 balanceAfter = IERC20(token).balanceOf(address(this));
        uint256 actualAmount = balanceAfter - balanceBefore;
        require(actualAmount > 0, "No tokens received");
        
        paymentCount += 1;
        payments[paymentCount] = Payment(
            msg.sender,
            token,
            actualAmount,
            block.timestamp
        );
        emit PaymentReceived(paymentCount, msg.sender, token, actualAmount, block.timestamp);
        return paymentCount;
    }

    /**
     * @dev Owner can withdraw native CRO or ERC20 tokens
     * @param to The address to withdraw to
     * @param token The token address (address(0) for native CRO)
     * @param amount The amount to withdraw (0 for full balance)
     */
    function withdraw(
        address payable to,
        address token,
        uint256 amount
    ) external onlyOwner nonReentrant {
        require(to != address(0), "Invalid recipient");
        
        if (token == address(0)) {
            // Native CRO withdrawal
            uint256 balance = address(this).balance;
            uint256 withdrawAmount = amount == 0 ? balance : amount;
            require(withdrawAmount > 0, "Zero balance");
            require(balance >= withdrawAmount, "Insufficient balance");
            
            (bool sent, ) = to.call{value: withdrawAmount}("");
            require(sent, "Transfer failed");
            emit Withdrawn(to, address(0), withdrawAmount, block.timestamp);
        } else {
            // ERC20 withdrawal
            uint256 balance = IERC20(token).balanceOf(address(this));
            uint256 withdrawAmount = amount == 0 ? balance : amount;
            require(withdrawAmount > 0, "Zero balance");
            require(balance >= withdrawAmount, "Insufficient balance");
            
            bool success = IERC20(token).transfer(to, withdrawAmount);
            require(success, "Transfer failed");
            emit Withdrawn(to, token, withdrawAmount, block.timestamp);
        }
    }

    /**
     * @dev Get ERC20 token balance of this contract
     */
    function getTokenBalance(address token) external view returns (uint256) {
        if (token == address(0)) {
            return address(this).balance;
        }
        return IERC20(token).balanceOf(address(this));
    }

    /**
     * @dev Get payment details by ID
     * @param paymentId The payment ID
     * @return Payment struct with payment details
     */
    function getPayment(uint256 paymentId) external view returns (Payment memory) {
        return payments[paymentId];
    }

    /**
     * @dev Get contract balance for native CRO
     * @return The contract's CRO balance
     */
    function getNativeBalance() external view returns (uint256) {
        return address(this).balance;
    }

    /**
     * @dev For receiving native CRO via plain transfer
     */
    receive() external payable whenNotPaused {
        require(msg.value > 0, "Zero value");
        paymentCount += 1;
        payments[paymentCount] = Payment(
            msg.sender,
            address(0),
            msg.value,
            block.timestamp
        );
        emit PaymentReceived(paymentCount, msg.sender, address(0), msg.value, block.timestamp);
    }
}
