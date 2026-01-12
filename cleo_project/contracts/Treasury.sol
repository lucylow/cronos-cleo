// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title Simple Treasury
 * @notice Holds ETH and ERC20 tokens controlled by the DAO.
 */
interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
}

contract Treasury {
    address public dao;

    event ETHSent(address indexed to, uint256 amount);
    event ERC20Sent(address indexed token, address indexed to, uint256 amount);

    modifier onlyDAO() {
        require(msg.sender == dao, "Only DAO");
        _;
    }

    constructor(address _dao) {
        require(_dao != address(0), "DAO zero");
        dao = _dao;
    }

    receive() external payable {}

    function sendETH(address payable to, uint256 amount) external onlyDAO {
        require(address(this).balance >= amount, "Insufficient ETH");
        (bool ok,) = to.call{value: amount}("");
        require(ok, "ETH transfer failed");
        emit ETHSent(to, amount);
    }

    function sendERC20(address token, address to, uint256 amount) external onlyDAO {
        require(IERC20(token).transfer(to, amount), "ERC20 transfer failed");
        emit ERC20Sent(token, to, amount);
    }
}
