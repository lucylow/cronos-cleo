const { ethers } = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  console.log("Deploying CronosPaymentProcessor...");

  const [deployer] = await ethers.getSigners();
  console.log("Deploying contracts with account:", deployer.address);

  const balance = await ethers.provider.getBalance(deployer.address);
  console.log("Account balance:", ethers.formatEther(balance), "CRO");

  // Deploy the payment processor contract
  const CronosPaymentProcessor = await ethers.getContractFactory(
    "CronosPaymentProcessor"
  );
  const paymentProcessor = await CronosPaymentProcessor.deploy();

  await paymentProcessor.waitForDeployment();
  const address = await paymentProcessor.getAddress();

  console.log("CronosPaymentProcessor deployed to:", address);

  // Save deployment info
  const deploymentInfo = {
    network: network.name,
    contract: "CronosPaymentProcessor",
    address: address,
    deployer: deployer.address,
    timestamp: new Date().toISOString(),
    blockNumber: await ethers.provider.getBlockNumber(),
  };

  // Save to a JSON file
  const deploymentsDir = path.join(__dirname, "../deployments");
  if (!fs.existsSync(deploymentsDir)) {
    fs.mkdirSync(deploymentsDir, { recursive: true });
  }

  const deploymentFile = path.join(
    deploymentsDir,
    `payment-${network.name}.json`
  );
  fs.writeFileSync(
    deploymentFile,
    JSON.stringify(deploymentInfo, null, 2)
  );
  console.log("Deployment info saved to:", deploymentFile);

  // Get contract ABI and save it
  const artifact = await ethers.getContractFactory("CronosPaymentProcessor");
  const contractInterface = artifact.interface;
  const abiDir = path.join(__dirname, "../abi");
  if (!fs.existsSync(abiDir)) {
    fs.mkdirSync(abiDir, { recursive: true });
  }
  fs.writeFileSync(
    path.join(abiDir, "CronosPaymentProcessor.json"),
    JSON.stringify(contractInterface.format("json"), null, 2)
  );
  console.log("ABI saved to abi/CronosPaymentProcessor.json");

  console.log("\n=== Deployment Summary ===");
  console.log("Contract:", "CronosPaymentProcessor");
  console.log("Address:", address);
  console.log("Network:", network.name);
  console.log("Deployer:", deployer.address);
  console.log("\nNext steps:");
  console.log("1. Verify the contract on Cronoscan:");
  console.log(
    `   npx hardhat verify --network ${network.name} ${address}`
  );
  console.log("2. Update your frontend .env with:");
  console.log(`   VITE_PAYMENT_CONTRACT_ADDRESS=${address}`);
  console.log("3. Update your backend .env with:");
  console.log(`   PAYMENT_CONTRACT_ADDRESS=${address}`);
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
