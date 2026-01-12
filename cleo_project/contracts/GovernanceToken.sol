// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title Minimal ERC20 Governance Token
 * @notice Simple fungible token whose balances represent voting power in the DAO.
 * @dev For production, consider snapshotting or ERC20Votes-style delegation.
 */
contract GovernanceToken {
    string public name;
    string public symbol;
    uint8  public immutable decimals = 18;

    uint256 public totalSupply;
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    event Transfer(address indexed from, address indexed to, uint256 amount);
    event Approval(address indexed owner, address indexed spender, uint256 amount);

    address public dao; // DAO contract that can mint

    modifier onlyDAO() {
        require(msg.sender == dao, "Only DAO");
        _;
    }

    constructor(string memory _name, string memory _symbol, address _dao) {
        require(_dao != address(0), "DAO zero");
        name = _name;
        symbol = _symbol;
        dao = _dao;
    }

    function _transfer(address from, address to, uint256 amount) internal {
        require(to != address(0), "Zero to");
        uint256 bal = balanceOf[from];
        require(bal >= amount, "Insufficient");
        unchecked {
            balanceOf[from] = bal - amount;
            balanceOf[to] += amount;
        }
        emit Transfer(from, to, amount);
    }

    function transfer(address to, uint256 amount) external returns (bool) {
        _transfer(msg.sender, to, amount);
        return true;
    }

    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }

    function transferFrom(address from, address to, uint256 amount)
        external
        returns (bool)
    {
        uint256 allowed = allowance[from][msg.sender];
        require(allowed >= amount, "Not allowed");
        if (allowed != type(uint256).max) {
            allowance[from][msg.sender] = allowed - amount;
        }
        _transfer(from, to, amount);
        return true;
    }

    function mint(address to, uint256 amount) external onlyDAO {
        require(to != address(0), "Zero to");
        totalSupply += amount;
        balanceOf[to] += amount;
        emit Transfer(address(0), to, amount);
    }
}
