const { ethers } = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  console.log("🚀 Deploying C.L.E.O. DAO to Cronos...\n");

  const [deployer] = await ethers.getSigners();
  console.log("Deploying contracts with account:", deployer.address);
  console.log("Account balance:", (await ethers.provider.getBalance(deployer.address)).toString(), "\n");

  // Get network info
  const network = await ethers.provider.getNetwork();
  console.log(`Network: ${network.name} (Chain ID: ${network.chainId})\n`);

  // DAO Configuration
  const DAO_CONFIG = {
    tokenName: process.env.DAO_TOKEN_NAME || "CLEO Governance Token",
    tokenSymbol: process.env.DAO_TOKEN_SYMBOL || "CLEO",
    quorumPercentage: process.env.DAO_QUORUM || 10, // 10% of total supply must vote
    proposalThreshold: process.env.DAO_PROPOSAL_THRESHOLD || ethers.parseEther("1000"), // Min tokens to propose
    votingPeriod: process.env.DAO_VOTING_PERIOD || 7 * 24 * 60 * 60, // 7 days in seconds
  };

  console.log("📋 DAO Configuration:");
  console.log(`   Token Name: ${DAO_CONFIG.tokenName}`);
  console.log(`   Token Symbol: ${DAO_CONFIG.tokenSymbol}`);
  console.log(`   Quorum: ${DAO_CONFIG.quorumPercentage}%`);
  console.log(`   Proposal Threshold: ${ethers.formatEther(DAO_CONFIG.proposalThreshold)} ${DAO_CONFIG.tokenSymbol}`);
  console.log(`   Voting Period: ${DAO_CONFIG.votingPeriod / (24 * 60 * 60)} days\n`);

  // Deploy SimpleDAO (this will also deploy GovernanceToken and Treasury)
  console.log("📝 Deploying SimpleDAO...");
  const SimpleDAO = await ethers.getContractFactory("SimpleDAO");
  const dao = await SimpleDAO.deploy(
    DAO_CONFIG.tokenName,
    DAO_CONFIG.tokenSymbol,
    DAO_CONFIG.quorumPercentage,
    DAO_CONFIG.proposalThreshold,
    DAO_CONFIG.votingPeriod
  );

  await dao.waitForDeployment();
  const daoAddress = await dao.getAddress();
  console.log("✅ SimpleDAO deployed to:", daoAddress);

  // Get deployed token and treasury addresses
  const governanceTokenAddress = await dao.governanceToken();
  const treasuryAddress = await dao.treasury();
  console.log("✅ GovernanceToken deployed to:", governanceTokenAddress);
  console.log("✅ Treasury deployed to:", treasuryAddress);

  // Wait for confirmations
  console.log("\n⏳ Waiting for confirmations...");
  await dao.deploymentTransaction().wait(3);
  console.log("✅ Contracts confirmed\n");

  // Optional: Mint initial tokens to deployer (for testing)
  if (process.env.DAO_INITIAL_MINT) {
    const initialMint = ethers.parseEther(process.env.DAO_INITIAL_MINT);
    console.log(`📝 Minting ${ethers.formatEther(initialMint)} tokens to deployer...`);
    const tx = await dao.mintGovToken(deployer.address, initialMint);
    await tx.wait();
    console.log("✅ Initial tokens minted\n");
  }

  // Save deployment info
  const deploymentInfo = {
    network: network.name,
    chainId: network.chainId.toString(),
    dao: {
      address: daoAddress,
      deployer: deployer.address,
      transactionHash: dao.deploymentTransaction().hash,
      blockNumber: (await ethers.provider.getBlockNumber()).toString(),
    },
    governanceToken: {
      address: governanceTokenAddress,
      name: DAO_CONFIG.tokenName,
      symbol: DAO_CONFIG.tokenSymbol,
    },
    treasury: {
      address: treasuryAddress,
    },
    config: {
      quorumPercentage: DAO_CONFIG.quorumPercentage,
      proposalThreshold: DAO_CONFIG.proposalThreshold.toString(),
      votingPeriod: DAO_CONFIG.votingPeriod,
    },
    timestamp: new Date().toISOString(),
  };

  const deploymentDir = path.join(__dirname, "../deployments");
  if (!fs.existsSync(deploymentDir)) {
    fs.mkdirSync(deploymentDir, { recursive: true });
  }

  const deploymentFile = path.join(deploymentDir, `dao-${network.name}-${Date.now()}.json`);
  fs.writeFileSync(deploymentFile, JSON.stringify(deploymentInfo, null, 2));
  console.log("📄 Deployment info saved to:", deploymentFile);

  // Verify contracts (optional, requires API key)
  if (network.chainId !== 1337n && process.env.CRONOSCAN_API_KEY) {
    console.log("\n🔍 Verifying contracts on Cronoscan...");
    try {
      await hre.run("verify:verify", {
        address: daoAddress,
        constructorArguments: [
          DAO_CONFIG.tokenName,
          DAO_CONFIG.tokenSymbol,
          DAO_CONFIG.quorumPercentage,
          DAO_CONFIG.proposalThreshold,
          DAO_CONFIG.votingPeriod,
        ],
      });
      console.log("✅ SimpleDAO verified!");
    } catch (error) {
      console.log("⚠️  Verification failed (this is OK if contract is already verified):", error.message);
    }
  }

  console.log("\n" + "=".repeat(60));
  console.log("🎉 DAO Deployment Complete!");
  console.log("=".repeat(60));
  console.log("\n📋 Next Steps:");
  console.log("1. Distribute governance tokens using dao.mintGovToken()");
  console.log("2. Fund the treasury by sending native tokens or ERC20s to:", treasuryAddress);
  console.log("3. Create proposals using dao.proposeTreasuryETHTransfer() or proposeTreasuryERC20Transfer()");
  console.log("4. Vote on proposals using dao.vote(proposalId, support)");
  console.log("5. Execute successful proposals using dao.execute(proposalId)");
  console.log("\n📊 View on explorer:");
  if (network.chainId === 338n) {
    console.log(`   DAO: https://testnet.cronoscan.com/address/${daoAddress}`);
    console.log(`   Token: https://testnet.cronoscan.com/address/${governanceTokenAddress}`);
    console.log(`   Treasury: https://testnet.cronoscan.com/address/${treasuryAddress}`);
  } else if (network.chainId === 25n) {
    console.log(`   DAO: https://cronoscan.com/address/${daoAddress}`);
    console.log(`   Token: https://cronoscan.com/address/${governanceTokenAddress}`);
    console.log(`   Treasury: https://cronoscan.com/address/${treasuryAddress}`);
  }
  console.log("\n");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
