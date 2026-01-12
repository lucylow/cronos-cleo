const { ethers } = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  console.log("🚀 Deploying HackathonNFT to Cronos...\n");

  const [deployer] = await ethers.getSigners();
  console.log("Deploying contracts with account:", deployer.address);
  console.log("Account balance:", (await ethers.provider.getBalance(deployer.address)).toString(), "\n");

  // Get network info
  const network = await ethers.provider.getNetwork();
  console.log(`Network: ${network.name} (Chain ID: ${network.chainId})\n`);

  // NFT Configuration
  const NFT_CONFIG = {
    name: process.env.NFT_NAME || "CLEO Hackathon NFT",
    symbol: process.env.NFT_SYMBOL || "CLEO",
    maxSupply: process.env.NFT_MAX_SUPPLY || 1000,
    mintPrice: process.env.NFT_MINT_PRICE || ethers.parseEther("0.1"), // 0.1 CRO
    maxPerWallet: process.env.NFT_MAX_PER_WALLET || 5,
    baseURI: process.env.NFT_BASE_URI || "ipfs://QmYourCIDHere/", // Update with your IPFS CID
  };

  console.log("📋 NFT Configuration:");
  console.log(`   Name: ${NFT_CONFIG.name}`);
  console.log(`   Symbol: ${NFT_CONFIG.symbol}`);
  console.log(`   Max Supply: ${NFT_CONFIG.maxSupply}`);
  console.log(`   Mint Price: ${ethers.formatEther(NFT_CONFIG.mintPrice)} CRO`);
  console.log(`   Max Per Wallet: ${NFT_CONFIG.maxPerWallet}`);
  console.log(`   Base URI: ${NFT_CONFIG.baseURI}\n`);

  // Deploy HackathonNFT
  console.log("📝 Deploying HackathonNFT...");
  const HackathonNFT = await ethers.getContractFactory("HackathonNFT");
  const nft = await HackathonNFT.deploy(
    NFT_CONFIG.name,
    NFT_CONFIG.symbol,
    NFT_CONFIG.maxSupply,
    NFT_CONFIG.mintPrice,
    NFT_CONFIG.maxPerWallet,
    NFT_CONFIG.baseURI
  );

  await nft.waitForDeployment();
  const nftAddress = await nft.getAddress();
  console.log("✅ HackathonNFT deployed to:", nftAddress);

  // Save deployment info
  const deploymentInfo = {
    network: network.name,
    chainId: network.chainId.toString(),
    contract: "HackathonNFT",
    address: nftAddress,
    deployer: deployer.address,
    config: {
      name: NFT_CONFIG.name,
      symbol: NFT_CONFIG.symbol,
      maxSupply: NFT_CONFIG.maxSupply.toString(),
      mintPrice: NFT_CONFIG.mintPrice.toString(),
      maxPerWallet: NFT_CONFIG.maxPerWallet.toString(),
      baseURI: NFT_CONFIG.baseURI,
    },
    deployedAt: new Date().toISOString(),
  };

  // Save to file
  const deploymentsDir = path.join(__dirname, "..", "deployments");
  if (!fs.existsSync(deploymentsDir)) {
    fs.mkdirSync(deploymentsDir, { recursive: true });
  }

  const deploymentFile = path.join(
    deploymentsDir,
    `HackathonNFT-${network.chainId}-${Date.now()}.json`
  );
  fs.writeFileSync(deploymentFile, JSON.stringify(deploymentInfo, null, 2));
  console.log("📄 Deployment info saved to:", deploymentFile);

  // Display next steps
  console.log("\n📌 Next Steps:");
  console.log("1. Enable public mint: nft.setPublicMintEnabled(true)");
  console.log("2. Update base URI if needed: nft.setBaseURI('ipfs://YourNewCID/')");
  console.log("3. Mint test NFT: nft.mint(1, { value: mintPrice })");
  console.log("4. Verify contract on Cronoscan:");
  console.log(`   npx hardhat verify --network ${network.name === "cronos_testnet" ? "cronos_testnet" : "cronos_mainnet"} ${nftAddress} "${NFT_CONFIG.name}" "${NFT_CONFIG.symbol}" ${NFT_CONFIG.maxSupply} ${NFT_CONFIG.mintPrice} ${NFT_CONFIG.maxPerWallet} "${NFT_CONFIG.baseURI}"`);
  console.log("\n✨ Deployment complete!\n");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
