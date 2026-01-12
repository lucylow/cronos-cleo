# C.L.E.O. NFT Contracts

Production-grade ERC-721 NFT implementation for the Cronos hackathon, with support for public minting, DAO-gated minting, and metadata management.

## Contracts

### 1. HackathonNFT.sol
Standard ERC-721 contract with public minting capabilities.

**Features:**
- ✅ Fixed max supply (immutable)
- ✅ Payable public mint with configurable price
- ✅ Per-wallet mint limits
- ✅ Owner-only reserved minting (for airdrops, rewards)
- ✅ Base URI for metadata (IPFS/Arweave/HTTP)
- ✅ Withdraw function for collected funds
- ✅ OpenZeppelin security standards

**Use Cases:**
- Public NFT sales
- Community collections
- Hackathon rewards/achievements

### 2. HackathonNFTDAO.sol
DAO-gated ERC-721 contract for governance-controlled NFT issuance.

**Features:**
- ✅ Fixed max supply (immutable)
- ✅ Only DAO can mint (via `daoMint`)
- ✅ Base URI for metadata
- ✅ Integrates with SimpleDAO contract

**Use Cases:**
- DAO-controlled rewards
- Governance credentials
- Achievement badges issued via proposals

## Quick Start

### Prerequisites

1. Install dependencies:
```bash
cd cleo_project/contracts
npm install
```

2. Set up environment variables in `.env`:
```env
# Network RPC URLs
CRONOS_TESTNET_RPC=https://evm-t3.cronos.org
CRONOS_MAINNET_RPC=https://evm.cronos.org

# Deployer Private Key
PRIVATE_KEY=your_private_key_here

# NFT Configuration (optional, defaults provided)
NFT_NAME="CLEO Hackathon NFT"
NFT_SYMBOL="CLEO"
NFT_MAX_SUPPLY=1000
NFT_MINT_PRICE=100000000000000000  # 0.1 CRO in wei
NFT_MAX_PER_WALLET=5
NFT_BASE_URI="ipfs://QmYourCIDHere/"

# For DAO-gated NFT
DAO_ADDRESS=0xYourDAOAddress
```

### Deploy Standard NFT

**Testnet:**
```bash
npm run deploy:nft:testnet
```

**Mainnet:**
```bash
npm run deploy:nft:mainnet
```

### Deploy DAO-Gated NFT

**Testnet:**
```bash
# Make sure DAO_ADDRESS is set in .env
npm run deploy:nft-dao:testnet
```

**Mainnet:**
```bash
npm run deploy:nft-dao:mainnet
```

## Usage

### Standard NFT (HackathonNFT)

#### Enable Public Mint
```javascript
const nft = await ethers.getContractAt("HackathonNFT", nftAddress);
await nft.setPublicMintEnabled(true);
```

#### Mint NFT
```javascript
const mintPrice = await nft.mintPrice();
await nft.mint(1, { value: mintPrice }); // Mint 1 NFT
```

#### Owner Mint (Reserve/Airdrop)
```javascript
await nft.ownerMint(userAddress, 5); // Mint 5 NFTs to user
```

#### Update Configuration
```javascript
// Update mint price
await nft.setMintPrice(ethers.parseEther("0.2"));

// Update max per wallet
await nft.setMaxPerWallet(10);

// Update base URI
await nft.setBaseURI("ipfs://QmNewCID/");
```

#### Withdraw Funds
```javascript
await nft.withdraw(ownerAddress);
```

### DAO-Gated NFT (HackathonNFTDAO)

#### Mint via DAO Proposal

1. Create a proposal to mint NFTs:
```javascript
const dao = await ethers.getContractAt("SimpleDAO", daoAddress);
const nft = await ethers.getContractAt("HackathonNFTDAO", nftAddress);

// Encode the mint call
const calldata = nft.interface.encodeFunctionData("daoMint", [
  recipientAddress,
  1 // quantity
]);

// Create proposal
await dao.proposeArbitraryCall(
  nftAddress,
  0,
  calldata,
  "Mint NFT to user for achievement"
);
```

2. Vote on the proposal (if you have governance tokens)

3. Execute the proposal after it passes:
```javascript
await dao.execute(proposalId);
```

## Metadata

The NFT contracts use a base URI pattern for metadata:

- Base URI: `ipfs://QmYourCIDHere/`
- Token URI: `ipfs://QmYourCIDHere/1.json`

### Metadata JSON Format

Each token should have a JSON file following the ERC-721 metadata standard:

```json
{
  "name": "CLEO NFT #1",
  "description": "C.L.E.O. Hackathon Achievement NFT",
  "image": "ipfs://QmImageCID/1.png",
  "attributes": [
    {
      "trait_type": "Achievement",
      "value": "Early Adopter"
    }
  ]
}
```

### Hosting Metadata

**Option 1: IPFS**
1. Upload your images and JSON files to IPFS (using Pinata, NFT.Storage, etc.)
2. Set base URI: `ipfs://QmYourCIDHere/`

**Option 2: Arweave**
1. Upload to Arweave
2. Set base URI: `https://arweave.net/YourTxID/`

**Option 3: HTTP Server**
1. Host JSON files on your server
2. Set base URI: `https://yourdomain.com/metadata/`

## Testing

Run the test suite:
```bash
npm test
```

Or run specific test file:
```bash
npx hardhat test test/HackathonNFT.test.js
```

## Contract Verification

After deployment, verify on Cronoscan:

```bash
# Standard NFT
npx hardhat verify --network cronos_testnet \
  <NFT_ADDRESS> \
  "CLEO Hackathon NFT" \
  "CLEO" \
  1000 \
  100000000000000000 \
  5 \
  "ipfs://QmYourCIDHere/"

# DAO-gated NFT
npx hardhat verify --network cronos_testnet \
  <NFT_ADDRESS> \
  "CLEO DAO NFT" \
  "CLEO" \
  1000 \
  <DAO_ADDRESS> \
  "ipfs://QmYourCIDHere/"
```

## Integration with C.L.E.O. DAO

If you want to integrate NFTs with your existing SimpleDAO:

1. Deploy `HackathonNFTDAO` with your DAO address
2. Create proposals to mint NFTs as rewards for:
   - Successful trades
   - Liquidity provision milestones
   - Governance participation
   - Achievement unlocks

Example integration in your backend:
```python
# In your backend/dao_executor.py or similar
async def mint_achievement_nft(user_address: str, achievement_type: str):
    # Create DAO proposal to mint NFT
    calldata = nft_contract.encode_function_data(
        "daoMint",
        [user_address, 1]
    )
    
    proposal_id = await dao_contract.functions.proposeArbitraryCall(
        nft_address,
        0,
        calldata,
        f"Mint {achievement_type} NFT to {user_address}"
    ).transact()
    
    return proposal_id
```

## Security Considerations

- ✅ Uses OpenZeppelin's battle-tested contracts
- ✅ Max supply is immutable (set at deployment)
- ✅ Owner functions are protected
- ✅ Reentrancy protection via OpenZeppelin
- ✅ Safe minting with `_safeMint`

## Gas Optimization

- Uses `ERC721Enumerable` for easy enumeration (slightly higher gas)
- If you don't need enumeration, consider using base `ERC721` for lower gas costs
- Token IDs start at 1 (not 0) for better compatibility

## License

MIT

## References

- [OpenZeppelin ERC-721 Documentation](https://docs.openzeppelin.com/contracts/4.x/erc721)
- [ERC-721 Standard](https://eips.ethereum.org/EIPS/eip-721)
- [Cronos Documentation](https://docs.cronos.org/)
