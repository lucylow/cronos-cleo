// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./GovernanceToken.sol";
import "./Treasury.sol";

/**
 * @title SimpleDAO
 * @notice Basic token‑based DAO with proposal, voting and execution.
 *
 * Voting model:
 * - One token = one vote (no delegation, snapshot, or time‑weighted logic).
 * - Voting power is balance at the time vote() is called.
 *
 * Proposals:
 * - Can trigger:
 *   * Treasury ETH transfers
 *   * Treasury ERC20 transfers
 *   * Or arbitrary call to a target (advanced / experimental)
 *
 * Parameters:
 * - quorum: minimum % of total supply that must vote YES for proposal to pass
 * - proposalThreshold: minimum tokens proposer must hold
 * - votingPeriod: duration in seconds for voting
 */
contract SimpleDAO {
    enum ProposalType {
        TreasuryETHTransfer,
        TreasuryERC20Transfer,
        ArbitraryCall
    }

    enum ProposalStatus {
        Pending,
        Active,
        Defeated,
        Succeeded,
        Executed,
        Cancelled
    }

    struct Proposal {
        uint256 id;
        address proposer;
        uint256 startTime;
        uint256 endTime;
        uint256 forVotes;
        uint256 againstVotes;
        uint256 abstainVotes;
        ProposalStatus status;
        ProposalType pType;

        // execution data
        address target;
        uint256 value;          // for ETH transfer or call value
        address token;          // for ERC20 transfer
        address recipient;      // for transfers
        bytes   callData;       // for ArbitraryCall
        string  description;
    }

    GovernanceToken public governanceToken;
    Treasury        public treasury;

    uint256 public nextProposalId = 1;

    // Governance parameters
    uint256 public quorumPercentage;      // e.g. 10 = 10%
    uint256 public proposalThreshold;     // min tokens to create proposal
    uint256 public votingPeriod;          // in seconds

    // Admin (can update params, emergency cancel)
    address public admin;

    // proposalId => Proposal
    mapping(uint256 => Proposal) public proposals;
    // proposalId => voter => hasVoted
    mapping(uint256 => mapping(address => bool)) public hasVoted;

    event ProposalCreated(
        uint256 indexed id,
        address indexed proposer,
        ProposalType proposalType,
        string description
    );

    event VoteCast(
        uint256 indexed proposalId,
        address indexed voter,
        uint8 support,    // 0 = Against, 1 = For, 2 = Abstain
        uint256 weight
    );

    event ProposalStatusChanged(uint256 indexed id, ProposalStatus newStatus);
    event Executed(uint256 indexed id);
    event Cancelled(uint256 indexed id);
    event ParamsUpdated(
        uint256 quorumPercentage,
        uint256 proposalThreshold,
        uint256 votingPeriod
    );
    event AdminChanged(address indexed oldAdmin, address indexed newAdmin);

    modifier onlyAdmin() {
        require(msg.sender == admin, "Only admin");
        _;
    }

    constructor(
        string memory _tokenName,
        string memory _tokenSymbol,
        uint256 _quorumPercentage,
        uint256 _proposalThreshold,
        uint256 _votingPeriod
    ) {
        require(_quorumPercentage <= 100, "Quorum > 100");
        require(_votingPeriod > 0, "Voting period 0");

        admin = msg.sender;
        quorumPercentage = _quorumPercentage;
        proposalThreshold = _proposalThreshold;
        votingPeriod = _votingPeriod;

        // Deploy token and treasury where DAO is owner/issuer.
        governanceToken = new GovernanceToken(_tokenName, _tokenSymbol, address(this));
        treasury = new Treasury(address(this));
    }

    // ===== Governance parameter management =====

    function setParams(
        uint256 _quorumPercentage,
        uint256 _proposalThreshold,
        uint256 _votingPeriod
    ) external onlyAdmin {
        require(_quorumPercentage <= 100, "Quorum > 100");
        require(_votingPeriod > 0, "Voting period 0");
        quorumPercentage = _quorumPercentage;
        proposalThreshold = _proposalThreshold;
        votingPeriod = _votingPeriod;
        emit ParamsUpdated(_quorumPercentage, _proposalThreshold, _votingPeriod);
    }

    function setAdmin(address _admin) external onlyAdmin {
        require(_admin != address(0), "Zero admin");
        emit AdminChanged(admin, _admin);
        admin = _admin;
    }

    // ===== Token distribution (bootstrap) =====

    /**
     * @notice Mint governance tokens to bootstrap DAO members.
     * @dev Only callable by admin at first; in a mature DAO you'd replace this
     *      with on‑chain sale, airdrops, or a one‑time distribution script.
     */
    function mintGovToken(address to, uint256 amount) external onlyAdmin {
        governanceToken.mint(to, amount);
    }

    // ===== Proposal creation =====

    function _canPropose(address proposer) internal view returns (bool) {
        return governanceToken.balanceOf(proposer) >= proposalThreshold;
    }

    /**
     * @notice Create a proposal to send ETH from the treasury.
     */
    function proposeTreasuryETHTransfer(
        address payable recipient,
        uint256 amount,
        string calldata description
    ) external returns (uint256) {
        require(_canPropose(msg.sender), "Insufficient voting power");
        require(recipient != address(0), "Zero recipient");

        uint256 id = nextProposalId++;
        uint256 start = block.timestamp;
        uint256 end = start + votingPeriod;

        proposals[id] = Proposal({
            id: id,
            proposer: msg.sender,
            startTime: start,
            endTime: end,
            forVotes: 0,
            againstVotes: 0,
            abstainVotes: 0,
            status: ProposalStatus.Active,
            pType: ProposalType.TreasuryETHTransfer,
            target: address(treasury),
            value: amount,
            token: address(0),
            recipient: recipient,
            callData: "",
            description: description
        });

        emit ProposalCreated(id, msg.sender, ProposalType.TreasuryETHTransfer, description);
        emit ProposalStatusChanged(id, ProposalStatus.Active);
        return id;
    }

    /**
     * @notice Create a proposal to send an ERC20 from the treasury.
     */
    function proposeTreasuryERC20Transfer(
        address token,
        address recipient,
        uint256 amount,
        string calldata description
    ) external returns (uint256) {
        require(_canPropose(msg.sender), "Insufficient voting power");
        require(token != address(0), "Zero token");
        require(recipient != address(0), "Zero recipient");

        uint256 id = nextProposalId++;
        uint256 start = block.timestamp;
        uint256 end = start + votingPeriod;

        proposals[id] = Proposal({
            id: id,
            proposer: msg.sender,
            startTime: start,
            endTime: end,
            forVotes: 0,
            againstVotes: 0,
            abstainVotes: 0,
            status: ProposalStatus.Active,
            pType: ProposalType.TreasuryERC20Transfer,
            target: address(treasury),
            value: 0,
            token: token,
            recipient: recipient,
            callData: "",
            description: description
        });

        emit ProposalCreated(id, msg.sender, ProposalType.TreasuryERC20Transfer, description);
        emit ProposalStatusChanged(id, ProposalStatus.Active);
        return id;
    }

    /**
     * @notice Create an arbitrary call proposal (advanced).
     * @dev Dangerous; use carefully. Useful to upgrade contracts or call external dApps.
     */
    function proposeArbitraryCall(
        address target,
        uint256 value,
        bytes calldata callData,
        string calldata description
    ) external returns (uint256) {
        require(_canPropose(msg.sender), "Insufficient voting power");
        require(target != address(0), "Zero target");

        uint256 id = nextProposalId++;
        uint256 start = block.timestamp;
        uint256 end = start + votingPeriod;

        proposals[id] = Proposal({
            id: id,
            proposer: msg.sender,
            startTime: start,
            endTime: end,
            forVotes: 0,
            againstVotes: 0,
            abstainVotes: 0,
            status: ProposalStatus.Active,
            pType: ProposalType.ArbitraryCall,
            target: target,
            value: value,
            token: address(0),
            recipient: address(0),
            callData: callData,
            description: description
        });

        emit ProposalCreated(id, msg.sender, ProposalType.ArbitraryCall, description);
        emit ProposalStatusChanged(id, ProposalStatus.Active);
        return id;
    }

    // ===== Voting =====

    /**
     * @notice Cast a vote on a proposal.
     * @param proposalId ID of proposal
     * @param support 0 = Against, 1 = For, 2 = Abstain
     */
    function vote(uint256 proposalId, uint8 support) external {
        require(support <= 2, "Invalid support");
        Proposal storage p = proposals[proposalId];
        require(p.status == ProposalStatus.Active, "Not active");
        require(block.timestamp >= p.startTime, "Voting not started");
        require(block.timestamp <= p.endTime, "Voting ended");
        require(!hasVoted[proposalId][msg.sender], "Already voted");

        uint256 weight = governanceToken.balanceOf(msg.sender);
        require(weight > 0, "No voting power");

        hasVoted[proposalId][msg.sender] = true;

        if (support == 0) {
            p.againstVotes += weight;
        } else if (support == 1) {
            p.forVotes += weight;
        } else {
            p.abstainVotes += weight;
        }

        emit VoteCast(proposalId, msg.sender, support, weight);
    }

    // ===== Proposal state helpers =====

    function _quorumReached(Proposal storage p) internal view returns (bool) {
        uint256 totalVotes = p.forVotes + p.againstVotes + p.abstainVotes;
        uint256 supply = governanceToken.totalSupply();
        if (supply == 0) return false;
        uint256 votesPct = (totalVotes * 100) / supply;
        return votesPct >= quorumPercentage;
    }

    function _proposalSucceeded(Proposal storage p) internal view returns (bool) {
        return p.forVotes > p.againstVotes && _quorumReached(p);
    }

    /**
     * @notice Manually update status after voting period ends (cheap & explicit).
     */
    function finalizeProposal(uint256 proposalId) public {
        Proposal storage p = proposals[proposalId];
        require(p.status == ProposalStatus.Active, "Not active");
        require(block.timestamp > p.endTime, "Voting still open");

        if (_proposalSucceeded(p)) {
            p.status = ProposalStatus.Succeeded;
        } else {
            p.status = ProposalStatus.Defeated;
        }

        emit ProposalStatusChanged(proposalId, p.status);
    }

    // ===== Execution & cancellation =====

    function execute(uint256 proposalId) external payable {
        Proposal storage p = proposals[proposalId];
        if (p.status == ProposalStatus.Active && block.timestamp > p.endTime) {
            finalizeProposal(proposalId);
        }

        require(p.status == ProposalStatus.Succeeded, "Not succeeded");

        if (p.pType == ProposalType.TreasuryETHTransfer) {
            // call Treasury.sendETH(recipient, amount)
            bytes memory data = abi.encodeWithSignature(
                "sendETH(address,uint256)",
                p.recipient,
                p.value
            );
            (bool ok,) = p.target.call{value: 0}(data);
            require(ok, "ETH transfer failed");
        } else if (p.pType == ProposalType.TreasuryERC20Transfer) {
            // call Treasury.sendERC20(token, recipient, amount)
            bytes memory data = abi.encodeWithSignature(
                "sendERC20(address,address,uint256)",
                p.token,
                p.recipient,
                p.value
            );
            (bool ok,) = p.target.call{value: 0}(data);
            require(ok, "ERC20 transfer failed");
        } else if (p.pType == ProposalType.ArbitraryCall) {
            (bool ok,) = p.target.call{value: p.value}(p.callData);
            require(ok, "Call failed");
        }

        p.status = ProposalStatus.Executed;
        emit Executed(proposalId);
        emit ProposalStatusChanged(proposalId, ProposalStatus.Executed);
    }

    /**
     * @notice Emergency cancel (e.g. admin finds a critical bug).
     * @dev Centralized; consider gating via another on‑chain process in production.
     */
    function cancel(uint256 proposalId) external onlyAdmin {
        Proposal storage p = proposals[proposalId];
        require(
            p.status == ProposalStatus.Active ||
            p.status == ProposalStatus.Succeeded,
            "Not cancellable"
        );
        p.status = ProposalStatus.Cancelled;
        emit Cancelled(proposalId);
        emit ProposalStatusChanged(proposalId, ProposalStatus.Cancelled);
    }

    // ===== View helpers =====

    function getProposal(uint256 proposalId)
        external
        view
        returns (Proposal memory)
    {
        return proposals[proposalId];
    }

    function state(uint256 proposalId)
        external
        view
        returns (ProposalStatus)
    {
        return proposals[proposalId].status;
    }
}
