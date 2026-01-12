// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IERC20 {
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function transfer(address to, uint256 amount) external returns (bool);
    function decimals() external view returns (uint8);
}

/**
 * @title CronosPaymentProcessor
 * @dev Smart contract for accepting native CRO and ERC-20 token payments on Cronos
 */
contract CronosPaymentProcessor {
    address public owner;
    uint256 public paymentCount;

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
        uint256 amount
    );
    event Withdrawn(
        address indexed to,
        address token,
        uint256 amount
    );

    modifier onlyOwner() {
        require(msg.sender == owner, "owner only");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    /**
     * @dev Accept native CRO payment
     * @return paymentId The ID of the payment record
     */
    function payNative() external payable returns (uint256) {
        require(msg.value > 0, "zero payment");
        paymentCount += 1;
        payments[paymentCount] = Payment(
            msg.sender,
            address(0),
            msg.value,
            block.timestamp
        );
        emit PaymentReceived(paymentCount, msg.sender, address(0), msg.value);
        return paymentCount;
    }

    /**
     * @dev Accept ERC-20 token payment
     * @param token The ERC-20 token contract address
     * @param amount The amount to pay (in token units)
     * @return paymentId The ID of the payment record
     * @notice Buyer must approve this contract for `amount` before calling this function
     */
    function payWithERC20(address token, uint256 amount) external returns (uint256) {
        require(token != address(0), "token zero");
        require(amount > 0, "zero amount");
        
        // Transfer tokens from payer to THIS contract
        bool ok = IERC20(token).transferFrom(msg.sender, address(this), amount);
        require(ok, "transfer failed");
        
        paymentCount += 1;
        payments[paymentCount] = Payment(
            msg.sender,
            token,
            amount,
            block.timestamp
        );
        emit PaymentReceived(paymentCount, msg.sender, token, amount);
        return paymentCount;
    }

    /**
     * @dev Owner can withdraw native CRO or ERC20 tokens
     * @param to The address to withdraw to
     * @param token The token address (address(0) for native CRO)
     * @param amount The amount to withdraw
     */
    function withdraw(
        address payable to,
        address token,
        uint256 amount
    ) external onlyOwner {
        require(to != address(0), "bad recipient");
        
        if (token == address(0)) {
            // Native CRO withdrawal
            require(address(this).balance >= amount, "insufficient native balance");
            (bool sent, ) = to.call{value: amount}("");
            require(sent, "native transfer failed");
            emit Withdrawn(to, address(0), amount);
        } else {
            // ERC20 withdrawal
            bool success = IERC20(token).transfer(to, amount);
            require(success, "token transfer failed");
            emit Withdrawn(to, token, amount);
        }
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
    receive() external payable {
        paymentCount += 1;
        payments[paymentCount] = Payment(
            msg.sender,
            address(0),
            msg.value,
            block.timestamp
        );
        emit PaymentReceived(paymentCount, msg.sender, address(0), msg.value);
    }
}
