// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// OpenZeppelin imports (install via npm: @openzeppelin/contracts)
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721Enumerable.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Strings.sol";

/**
 * @title HackathonNFT
 * @notice ERC-721 collection for your Cronos hack.
 *         - Fixed max supply
 *         - Optional public mint with price
 *         - Owner-only reserved mint
 *         - Base URI for metadata (IPFS / Arweave / HTTP)
 */
contract HackathonNFT is ERC721Enumerable, Ownable {
    using Strings for uint256;

    // ===== Configuration =====

    uint256 public immutable maxSupply;       // hard cap
    uint256 public mintPrice;                 // in native token (CRO)
    uint256 public maxPerWallet;              // public mint limit per address
    bool    public publicMintEnabled;
    string  private baseTokenURI;

    // address => minted count (public sale)
    mapping(address => uint256) public mintedByWallet;

    // ===== Events =====

    event PublicMintToggled(bool enabled);
    event MintPriceUpdated(uint256 newPrice);
    event MaxPerWalletUpdated(uint256 newLimit);
    event BaseURIUpdated(string newBaseURI);

    // ===== Constructor =====

    constructor(
        string memory _name,
        string memory _symbol,
        uint256 _maxSupply,
        uint256 _mintPrice,
        uint256 _maxPerWallet,
        string memory _initialBaseURI
    ) ERC721(_name, _symbol) Ownable(msg.sender) {
        require(_maxSupply > 0, "Max supply = 0");
        maxSupply = _maxSupply;
        mintPrice = _mintPrice;
        maxPerWallet = _maxPerWallet;
        baseTokenURI = _initialBaseURI;
    }

    // ===== Public mint =====

    /**
     * @notice Mint `quantity` NFTs during public sale.
     * @dev Requires publicMintEnabled, respects maxSupply and per-wallet cap.
     */
    function mint(uint256 quantity) external payable {
        require(publicMintEnabled, "Public mint disabled");
        require(quantity > 0, "Quantity = 0");

        uint256 supply = totalSupply();
        require(supply + quantity <= maxSupply, "Exceeds max supply");

        if (mintPrice > 0) {
            require(msg.value == mintPrice * quantity, "Incorrect ETH value");
        }

        if (maxPerWallet > 0) {
            require(
                mintedByWallet[msg.sender] + quantity <= maxPerWallet,
                "Exceeds wallet mint limit"
            );
        }

        mintedByWallet[msg.sender] += quantity;

        for (uint256 i = 0; i < quantity; i++) {
            uint256 tokenId = supply + i + 1; // token IDs start at 1
            _safeMint(msg.sender, tokenId);
        }
    }

    // ===== Owner mint (reserve / airdrops) =====

    /**
     * @notice Owner can mint tokens to arbitrary address (no payment / wallet cap).
     */
    function ownerMint(address to, uint256 quantity) external onlyOwner {
        require(quantity > 0, "Quantity = 0");

        uint256 supply = totalSupply();
        require(supply + quantity <= maxSupply, "Exceeds max supply");

        for (uint256 i = 0; i < quantity; i++) {
            uint256 tokenId = supply + i + 1;
            _safeMint(to, tokenId);
        }
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

    // ===== Admin configuration =====

    function setPublicMintEnabled(bool enabled) external onlyOwner {
        publicMintEnabled = enabled;
        emit PublicMintToggled(enabled);
    }

    function setMintPrice(uint256 _mintPrice) external onlyOwner {
        mintPrice = _mintPrice;
        emit MintPriceUpdated(_mintPrice);
    }

    function setMaxPerWallet(uint256 _limit) external onlyOwner {
        maxPerWallet = _limit;
        emit MaxPerWalletUpdated(_limit);
    }

    function setBaseURI(string calldata _baseURI_) external onlyOwner {
        baseTokenURI = _baseURI_;
        emit BaseURIUpdated(_baseURI_);
    }

    // ===== Withdraw funds =====

    function withdraw(address payable to) external onlyOwner {
        require(to != address(0), "Zero address");
        (bool ok, ) = to.call{value: address(this).balance}("");
        require(ok, "Withdraw failed");
    }
}
