// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title IntelligentSettlement
 * @notice Generic intelligent settlement / escrow contract for Web3
 * @dev Designed for use with off-chain AI agents / facilitators (e.g. Cronos x402)
 *      - Holds buyer funds in ERC20 or native token
 *      - Supports milestone-based settlement
 *      - Uses signed instructions from an authorized "agent" to settle/release funds
 *      - Can auto-refund on timeout if no settlement occurred
 */

interface IERC20 {
    function totalSupply() external view returns (uint256);
    function balanceOf(address account) external view returns (uint256);
    function transfer(address to, uint256 value)
        external
        returns (bool);

    function allowance(address owner, address spender)
        external
        view
        returns (uint256);

    function approve(address spender, uint256 value)
        external
        returns (bool);

    function transferFrom(
        address from,
        address to,
        uint256 value
    ) external returns (bool);

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(
        address indexed owner,
        address indexed spender,
        uint256 value
    );
}

library SafeERC20 {
    function safeTransfer(
        IERC20 token,
        address to,
        uint256 value
    ) internal {
        require(token.transfer(to, value), "SafeERC20: transfer failed");
    }

    function safeTransferFrom(
        IERC20 token,
        address from,
        address to,
        uint256 value
    ) internal {
        require(token.transferFrom(from, to, value), "SafeERC20: transferFrom failed");
    }
}

abstract contract ReentrancyGuard {
    uint256 private constant _NOT_ENTERED = 1;
    uint256 private constant _ENTERED     = 2;

    uint256 private _status;

    constructor () {
        _status = _NOT_ENTERED;
    }

    modifier nonReentrant() {
        require(_status != _ENTERED, "ReentrancyGuard: reentrant");
        _status = _ENTERED;
        _;
        _status = _NOT_ENTERED;
    }
}

contract IntelligentSettlement is ReentrancyGuard {
    using SafeERC20 for IERC20;

    // ========== TYPES ==========

    enum DealStatus {
        PendingFunding,
        Active,
        Completed,
        Refunded,
        Cancelled
    }

    struct Milestone {
        uint256 amount;          // amount to release if milestone succeeds
        bool    completed;       // marked true once released
    }

    struct Deal {
        address buyer;
        address seller;
        address token;           // address(0) = native (CRO/ETH/etc)
        uint256 totalAmount;
        uint256 fundedAmount;
        uint256 createdAt;
        uint256 deadline;        // unix timestamp; after this buyer can refund if not completed
        uint256 currentMilestone;
        DealStatus status;
        uint256 feeBps;          // protocol fee in basis points (e.g. 25 = 0.25%)
        uint256 agentNonce;      // monotonically increasing nonce for agent instructions
        address arbitrator;      // optional arbitrator
    }

    // ========== STORAGE ==========

    address public owner;
    address public protocolTreasury;
    address public authorizedAgent; // off-chain AI/oracle/settlement agent

    uint256 public nextDealId = 1;
    uint256 public constant MAX_FEE_BPS = 500;   // 5%
    uint256 public constant BPS_DENOMINATOR = 10_000;

    // dealId => Deal
    mapping(uint256 => Deal) public deals;

    // dealId => milestones
    mapping(uint256 => Milestone[]) public milestones;

    // ========== EVENTS ==========

    event DealCreated(
        uint256 indexed dealId,
        address indexed buyer,
        address indexed seller,
        address token,
        uint256 totalAmount,
        uint256 deadline
    );

    event DealFunded(
        uint256 indexed dealId,
        uint256 amount,
        uint256 fundedAmount
    );

    event MilestoneReleased(
        uint256 indexed dealId,
        uint256 indexed milestoneIndex,
        uint256 amountToSeller,
        uint256 feeToProtocol
    );

    event DealCompleted(uint256 indexed dealId);
    event DealRefunded(uint256 indexed dealId, uint256 amount);
    event DealCancelled(uint256 indexed dealId);

    event AgentUpdated(address indexed oldAgent, address indexed newAgent);
    event TreasuryUpdated(address indexed oldTreasury, address indexed newTreasury);
    event OwnerTransferred(address indexed oldOwner, address indexed newOwner);

    // ========== MODIFIERS ==========

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }

    modifier onlyAgent() {
        require(msg.sender == authorizedAgent, "Only agent");
        _;
    }

    // ========== CONSTRUCTOR ==========

    constructor(address _treasury, address _agent) {
        require(_treasury != address(0), "Treasury zero");
        owner = msg.sender;
        protocolTreasury = _treasury;
        authorizedAgent = _agent;
    }

    // ========== ADMIN FUNCTIONS ==========

    function setAuthorizedAgent(address _agent) external onlyOwner {
        emit AgentUpdated(authorizedAgent, _agent);
        authorizedAgent = _agent;
    }

    function setProtocolTreasury(address _treasury) external onlyOwner {
        require(_treasury != address(0), "Zero address");
        emit TreasuryUpdated(protocolTreasury, _treasury);
        protocolTreasury = _treasury;
    }

    function transferOwnership(address _newOwner) external onlyOwner {
        require(_newOwner != address(0), "Zero address");
        emit OwnerTransferred(owner, _newOwner);
        owner = _newOwner;
    }

    // ========== DEAL CREATION & FUNDING ==========

    /**
     * @notice Create a new intelligent settlement deal with milestones
     * @param _seller Seller address (payment recipient)
     * @param _token Settlement token (0 for native)
     * @param _totalAmount Total amount to be escrowed (sum of milestones)
     * @param _deadline Timestamp after which buyer can refund if incomplete
     * @param _milestoneAmounts Array of milestone amounts (must sum to total)
     * @param _feeBps Protocol fee in basis points (0-500)
     * @param _arbitrator Optional arbitrator (can be zero)
     */
    function createDeal(
        address _seller,
        address _token,
        uint256 _totalAmount,
        uint256 _deadline,
        uint256[] calldata _milestoneAmounts,
        uint256 _feeBps,
        address _arbitrator
    ) external returns (uint256 dealId) {
        require(_seller != address(0), "Seller zero");
        require(_totalAmount > 0, "Total amount zero");
        require(_deadline > block.timestamp, "Deadline in past");
        require(_feeBps <= MAX_FEE_BPS, "Fee too high");
        require(_milestoneAmounts.length > 0, "No milestones");

        uint256 sum;
        for (uint256 i = 0; i < _milestoneAmounts.length; i++) {
            sum += _milestoneAmounts[i];
        }
        require(sum == _totalAmount, "Milestones != total");

        dealId = nextDealId++;
        Deal storage d = deals[dealId];

        d.buyer = msg.sender;
        d.seller = _seller;
        d.token = _token;
        d.totalAmount = _totalAmount;
        d.fundedAmount = 0;
        d.createdAt = block.timestamp;
        d.deadline = _deadline;
        d.currentMilestone = 0;
        d.status = DealStatus.PendingFunding;
        d.feeBps = _feeBps;
        d.agentNonce = 0;
        d.arbitrator = _arbitrator;

        for (uint256 i = 0; i < _milestoneAmounts.length; i++) {
            milestones[dealId].push(
                Milestone({
                    amount: _milestoneAmounts[i],
                    completed: false
                })
            );
        }

        emit DealCreated(
            dealId,
            msg.sender,
            _seller,
            _token,
            _totalAmount,
            _deadline
        );
    }

    /**
     * @notice Fund an existing deal (can be done in multiple txs until fully funded)
     * @dev token == address(0) => msg.value must be amount
     */
    function fundDeal(uint256 _dealId, uint256 _amount)
        external
        payable
        nonReentrant
    {
        Deal storage d = deals[_dealId];
        require(d.buyer != address(0), "Deal not found");
        require(msg.sender == d.buyer, "Only buyer");
        require(
            d.status == DealStatus.PendingFunding || d.status == DealStatus.Active,
            "Wrong status"
        );
        require(_amount > 0, "Amount zero");
        require(d.fundedAmount + _amount <= d.totalAmount, "Overfund");

        if (d.token == address(0)) {
            // Native token (e.g., CRO)
            require(msg.value == _amount, "Incorrect msg.value");
        } else {
            require(msg.value == 0, "No native");
            IERC20(d.token).safeTransferFrom(msg.sender, address(this), _amount);
        }

        d.fundedAmount += _amount;
        if (d.fundedAmount == d.totalAmount) {
            d.status = DealStatus.Active;
        }

        emit DealFunded(_dealId, _amount, d.fundedAmount);
    }

    // ========== AGENT-DRIVEN SETTLEMENT ==========

    /**
     * @notice Called by the authorized agent (e.g., AI/x402 facilitator)
     *         to release a specific milestone after verifying conditions off-chain.
     *
     * @param _dealId The deal to settle
     * @param _milestoneIndex Index of milestone to release
     * @param _minSellerAmount Minimum net amount to seller (slippage/error guard)
     * @param _agentNonce Monotonic nonce to prevent replay per deal
     *
     * In a production setting this function is usually invoked by:
     *  - an x402 facilitator after verifying payee/payor intents
     *  - or an AI agent that checked off-chain conditions (delivery, KYC, scoring, etc.).
     */
    function agentReleaseMilestone(
        uint256 _dealId,
        uint256 _milestoneIndex,
        uint256 _minSellerAmount,
        uint256 _agentNonce
    ) external onlyAgent nonReentrant {
        Deal storage d = deals[_dealId];
        require(d.status == DealStatus.Active, "Deal not active");
        require(_milestoneIndex < milestones[_dealId].length, "Bad index");

        // simple per-deal monotonic nonce to avoid replays from the same agent
        require(_agentNonce == d.agentNonce + 1, "Bad nonce");
        d.agentNonce = _agentNonce;

        Milestone storage m = milestones[_dealId][_milestoneIndex];
        require(!m.completed, "Milestone done");
        require(m.amount > 0, "Zero milestone");
        require(d.fundedAmount >= m.amount, "Not enough funded");

        // calculate protocol fee and seller amount
        uint256 fee = (m.amount * d.feeBps) / BPS_DENOMINATOR;
        uint256 sellerAmount = m.amount - fee;
        require(sellerAmount >= _minSellerAmount, "Seller min not met");

        // update state
        m.completed = true;
        d.fundedAmount -= m.amount;

        // send funds
        _payout(d.token, d.seller, sellerAmount);
        if (fee > 0) {
            _payout(d.token, protocolTreasury, fee);
        }

        emit MilestoneReleased(_dealId, _milestoneIndex, sellerAmount, fee);

        // if all milestones completed -> mark deal completed
        if (_allMilestonesCompleted(_dealId)) {
            d.status = DealStatus.Completed;
            emit DealCompleted(_dealId);
        }
    }

    /**
     * @notice Arbitrator emergency function:
     *         release remaining funds to seller OR refund buyer in disputes.
     * @dev Only arbitrator specified for deal can call.
     */
    function arbitratorResolve(
        uint256 _dealId,
        bool releaseToSeller
    ) external nonReentrant {
        Deal storage d = deals[_dealId];
        require(d.arbitrator != address(0), "No arbitrator");
        require(msg.sender == d.arbitrator, "Only arbitrator");
        require(
            d.status == DealStatus.Active || d.status == DealStatus.PendingFunding,
            "Wrong status"
        );

        uint256 amount = d.fundedAmount;
        d.fundedAmount = 0;

        if (releaseToSeller) {
            // take fee on remaining amount
            uint256 fee = (amount * d.feeBps) / BPS_DENOMINATOR;
            uint256 sellerAmount = amount - fee;
            _payout(d.token, d.seller, sellerAmount);
            if (fee > 0) {
                _payout(d.token, protocolTreasury, fee);
            }

            d.status = DealStatus.Completed;
            emit DealCompleted(_dealId);
        } else {
            _payout(d.token, d.buyer, amount);
            d.status = DealStatus.Refunded;
            emit DealRefunded(_dealId, amount);
        }
    }

    // ========== BUYER-INITIATED REFUND / CANCEL ==========

    /**
     * @notice Buyer can cancel an unfunded deal before any funds are locked.
     */
    function cancelUnfundedDeal(uint256 _dealId) external {
        Deal storage d = deals[_dealId];
        require(d.buyer != address(0), "Deal not found");
        require(msg.sender == d.buyer, "Only buyer");
        require(d.fundedAmount == 0, "Already funded");
        require(
            d.status == DealStatus.PendingFunding,
            "Wrong status"
        );

        d.status = DealStatus.Cancelled;
        emit DealCancelled(_dealId);
    }

    /**
     * @notice Buyer can refund remaining funds if deadline has passed and deal is not completed
     */
    function refundAfterDeadline(uint256 _dealId) external nonReentrant {
        Deal storage d = deals[_dealId];
        require(d.buyer != address(0), "Deal not found");
        require(msg.sender == d.buyer, "Only buyer");
        require(d.status == DealStatus.Active || d.status == DealStatus.PendingFunding, "Wrong status");
        require(block.timestamp >= d.deadline, "Deadline not passed");

        uint256 amount = d.fundedAmount;
        d.fundedAmount = 0;
        d.status = DealStatus.Refunded;

        _payout(d.token, d.buyer, amount);

        emit DealRefunded(_dealId, amount);
    }

    // ========== VIEW HELPERS ==========

    function getMilestones(uint256 _dealId)
        external
        view
        returns (Milestone[] memory)
    {
        return milestones[_dealId];
    }

    function milestonesCount(uint256 _dealId)
        external
        view
        returns (uint256)
    {
        return milestones[_dealId].length;
    }

    function getDeal(uint256 _dealId)
        external
        view
        returns (Deal memory)
    {
        return deals[_dealId];
    }

    // ========== INTERNALS ==========

    function _allMilestonesCompleted(uint256 _dealId)
        internal
        view
        returns (bool)
    {
        Milestone[] storage arr = milestones[_dealId];
        for (uint256 i = 0; i < arr.length; i++) {
            if (!arr[i].completed) {
                return false;
            }
        }
        return true;
    }

    function _payout(
        address _token,
        address _to,
        uint256 _amount
    ) internal {
        if (_amount == 0) return;
        if (_token == address(0)) {
            (bool ok, ) = _to.call{value: _amount}("");
            require(ok, "Native transfer failed");
        } else {
            IERC20(_token).safeTransfer(_to, _amount);
        }
    }

    // accept native token deposits
    receive() external payable {}
}
