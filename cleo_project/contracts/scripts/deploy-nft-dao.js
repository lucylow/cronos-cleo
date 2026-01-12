const { ethers } = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  console.log("🚀 Deploying HackathonNFTDAO to Cronos...\n");

  const [deployer] = await ethers.getSigners();
  console.log("Deploying contracts with account:", deployer.address);
  console.log("Account balance:", (await ethers.provider.getBalance(deployer.address)).toString(), "\n");

  // Get network info
  const network = await ethers.provider.getNetwork();
  console.log(`Network: ${network.name} (Chain ID: ${network.chainId})\n`);

  // Get DAO address from environment or prompt
  const daoAddress = process.env.DAO_ADDRESS;
  if (!daoAddress) {
    throw new Error("DAO_ADDRESS environment variable is required. Set it to your SimpleDAO contract address.");
  }

  // NFT Configuration
  const NFT_CONFIG = {
    name: process.env.NFT_NAME || "CLEO DAO NFT",
    symbol: process.env.NFT_SYMBOL || "CLEODAO",
    maxSupply: process.env.NFT_MAX_SUPPLY || 1000,
    daoAddress: daoAddress,
    baseURI: process.env.NFT_BASE_URI || "ipfs://QmYourCIDHere/", // Update with your IPFS CID
  };

  console.log("📋 NFT Configuration:");
  console.log(`   Name: ${NFT_CONFIG.name}`);
  console.log(`   Symbol: ${NFT_CONFIG.symbol}`);
  console.log(`   Max Supply: ${NFT_CONFIG.maxSupply}`);
  console.log(`   DAO Address: ${NFT_CONFIG.daoAddress}`);
  console.log(`   Base URI: ${NFT_CONFIG.baseURI}\n`);

  // Deploy HackathonNFTDAO
  console.log("📝 Deploying HackathonNFTDAO...");
  const HackathonNFTDAO = await ethers.getContractFactory("HackathonNFTDAO");
  const nft = await HackathonNFTDAO.deploy(
    NFT_CONFIG.name,
    NFT_CONFIG.symbol,
    NFT_CONFIG.maxSupply,
    NFT_CONFIG.daoAddress,
    NFT_CONFIG.baseURI
  );

  await nft.waitForDeployment();
  const nftAddress = await nft.getAddress();
  console.log("✅ HackathonNFTDAO deployed to:", nftAddress);

  // Save deployment info
  const deploymentInfo = {
    network: network.name,
    chainId: network.chainId.toString(),
    contract: "HackathonNFTDAO",
    address: nftAddress,
    daoAddress: NFT_CONFIG.daoAddress,
    deployer: deployer.address,
    config: {
      name: NFT_CONFIG.name,
      symbol: NFT_CONFIG.symbol,
      maxSupply: NFT_CONFIG.maxSupply.toString(),
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
    `HackathonNFTDAO-${network.chainId}-${Date.now()}.json`
  );
  fs.writeFileSync(deploymentFile, JSON.stringify(deploymentInfo, null, 2));
  console.log("📄 Deployment info saved to:", deploymentFile);

  // Display next steps
  console.log("\n📌 Next Steps:");
  console.log("1. Create a DAO proposal to mint NFTs:");
  console.log(`   dao.proposeArbitraryCall(${nftAddress}, 0, calldata, "Mint NFT to user")`);
  console.log("2. The calldata should encode: nft.daoMint(userAddress, quantity)");
  console.log("3. After proposal passes, execute it to mint the NFT");
  console.log("4. Verify contract on Cronoscan:");
  console.log(`   npx hardhat verify --network ${network.name === "cronos_testnet" ? "cronos_testnet" : "cronos_mainnet"} ${nftAddress} "${NFT_CONFIG.name}" "${NFT_CONFIG.symbol}" ${NFT_CONFIG.maxSupply} ${NFT_CONFIG.daoAddress} "${NFT_CONFIG.baseURI}"`);
  console.log("\n✨ Deployment complete!\n");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
