// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// OpenZeppelin imports
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721Enumerable.sol";
import "@openzeppelin/contracts/utils/Strings.sol";

/**
 * @title HackathonNFTDAO
 * @notice ERC-721 collection gated by DAO control.
 *         - Fixed max supply
 *         - Only DAO can mint (via daoMint)
 *         - Base URI for metadata (IPFS / Arweave / HTTP)
 *         - Useful for DAO-controlled rewards, achievements, or credentials
 */
contract HackathonNFTDAO is ERC721Enumerable {
    using Strings for uint256;

    // ===== Configuration =====

    uint256 public immutable maxSupply;       // hard cap
    address public immutable dao;             // DAO contract address
    string  private baseTokenURI;

    // ===== Events =====

    event BaseURIUpdated(string newBaseURI);
    event DAOMint(address indexed to, uint256 quantity);

    // ===== Modifiers =====

    modifier onlyDAO() {
        require(msg.sender == dao, "Only DAO");
        _;
    }

    // ===== Constructor =====

    constructor(
        string memory _name,
        string memory _symbol,
        uint256 _maxSupply,
        address _dao,
        string memory _initialBaseURI
    ) ERC721(_name, _symbol) {
        require(_maxSupply > 0, "Max supply = 0");
        require(_dao != address(0), "DAO zero");
        maxSupply = _maxSupply;
        dao = _dao;
        baseTokenURI = _initialBaseURI;
    }

    // ===== DAO mint =====

    /**
     * @notice DAO can mint tokens to arbitrary address (for rewards, achievements, etc.).
     * @dev Only callable by the DAO contract (e.g., via proposal execution).
     */
    function daoMint(address to, uint256 quantity) external onlyDAO {
        require(quantity > 0, "Quantity = 0");
        require(to != address(0), "Zero address");

        uint256 supply = totalSupply();
        require(supply + quantity <= maxSupply, "Exceeds max supply");

        for (uint256 i = 0; i < quantity; i++) {
            uint256 tokenId = supply + i + 1; // token IDs start at 1
            _safeMint(to, tokenId);
        }

        emit DAOMint(to, quantity);
    }

    // ===== Metadata =====

    /**
     * @notice Returns metadata URI for `tokenId`.
     * @dev Typical pattern: baseURI + tokenId + ".json".
     */
    function tokenURI(uint256 tokenId)
        public
        view
        override
        returns (string memory)
    {
        require(_exists(tokenId), "Nonexistent token");

        string memory baseURI = _baseURI();
        if (bytes(baseURI).length == 0) {
            return "";
        }

        // Example: ipfs://CID/1.json
        return string(abi.encodePacked(baseURI, tokenId.toString(), ".json"));
    }

    function _baseURI() internal view override returns (string memory) {
        return baseTokenURI;
    }

    // ===== Admin configuration (DAO-controlled) =====

    /**
     * @notice Update base URI (callable by DAO via proposal).
     * @dev In production, you might want to gate this via DAO proposal execution.
     *      For now, we allow direct DAO calls. You can restrict further if needed.
     */
    function setBaseURI(string calldata _baseURI_) external onlyDAO {
        baseTokenURI = _baseURI_;
        emit BaseURIUpdated(_baseURI_);
    }
}
