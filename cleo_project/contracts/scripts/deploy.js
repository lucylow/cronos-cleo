const { ethers } = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  console.log("🚀 Deploying C.L.E.O. Cross-DEX Router to Cronos...\n");

  const [deployer] = await ethers.getSigners();
  console.log("Deploying contracts with account:", deployer.address);
  console.log("Account balance:", (await ethers.provider.getBalance(deployer.address)).toString(), "\n");

  // Get network info
  const network = await ethers.provider.getNetwork();
  console.log(`Network: ${network.name} (Chain ID: ${network.chainId})\n`);

  // x402 Facilitator addresses (update these with actual addresses)
  const FACILITATOR_ADDRESSES = {
    338: "0x0000000000000000000000000000000000000000", // Cronos Testnet - UPDATE THIS
    25: "0x0000000000000000000000000000000000000000",  // Cronos Mainnet - UPDATE THIS
  };

  const facilitatorAddress = FACILITATOR_ADDRESSES[network.chainId] || FACILITATOR_ADDRESSES[338];
  
  if (facilitatorAddress === "0x0000000000000000000000000000000000000000") {
    console.warn("⚠️  WARNING: Facilitator address not set! Please update FACILITATOR_ADDRESSES in deploy.js");
    console.warn("   Using zero address for now (contract will need to be updated later)\n");
  }

  // Fee recipient (can be deployer for now)
  const feeRecipient = process.env.FEE_RECIPIENT || deployer.address;
  console.log(`Fee Recipient: ${feeRecipient}\n`);

  // Deploy CLECORouter
  console.log("📝 Deploying CLECORouter...");
  const CLECORouter = await ethers.getContractFactory("CLECORouter");
  const router = await CLECORouter.deploy(facilitatorAddress, feeRecipient);
  
  await router.waitForDeployment();
  const routerAddress = await router.getAddress();
  console.log("✅ CLECORouter deployed to:", routerAddress);

  // Wait for a few confirmations
  console.log("\n⏳ Waiting for confirmations...");
  await router.deploymentTransaction().wait(3);
  console.log("✅ Contract confirmed\n");

  // Save deployment info
  const deploymentInfo = {
    network: network.name,
    chainId: network.chainId.toString(),
    router: {
      address: routerAddress,
      deployer: deployer.address,
      transactionHash: router.deploymentTransaction().hash,
      blockNumber: (await ethers.provider.getBlockNumber()).toString(),
    },
    facilitator: facilitatorAddress,
    feeRecipient: feeRecipient,
    timestamp: new Date().toISOString(),
  };

  const deploymentDir = path.join(__dirname, "../deployments");
  if (!fs.existsSync(deploymentDir)) {
    fs.mkdirSync(deploymentDir, { recursive: true });
  }

  const deploymentFile = path.join(deploymentDir, `${network.name}-${Date.now()}.json`);
  fs.writeFileSync(deploymentFile, JSON.stringify(deploymentInfo, null, 2));
  console.log("📄 Deployment info saved to:", deploymentFile);

  // Verify contract (optional, requires API key)
  if (network.chainId !== 1337n && process.env.CRONOSCAN_API_KEY) {
    console.log("\n🔍 Verifying contract on Cronoscan...");
    try {
      await hre.run("verify:verify", {
        address: routerAddress,
        constructorArguments: [facilitatorAddress, feeRecipient],
      });
      console.log("✅ Contract verified!");
    } catch (error) {
      console.log("⚠️  Verification failed (this is OK if contract is already verified):", error.message);
    }
  }

  console.log("\n" + "=".repeat(60));
  console.log("🎉 Deployment Complete!");
  console.log("=".repeat(60));
  console.log("\n📋 Next Steps:");
  console.log("1. Update facilitator address if using zero address");
  console.log("2. Register DEX routers using router.registerDEX()");
  console.log("3. Test the contract with a small swap");
  console.log("4. Update frontend with router address:", routerAddress);
  console.log("\n📊 View on explorer:");
  if (network.chainId === 338n) {
    console.log(`   https://testnet.cronoscan.com/address/${routerAddress}`);
  } else if (network.chainId === 25n) {
    console.log(`   https://cronoscan.com/address/${routerAddress}`);
  }
  console.log("\n");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });

