const { expect } = require("chai");
const { ethers } = require("hardhat");
const { time } = require("@nomicfoundation/hardhat-network-helpers");

describe("CLECORouter", function () {
  let router;
  let owner;
  let user;
  let feeRecipient;
  let mockFacilitator;
  let mockVVS;
  let mockCrona;
  let tokenIn;
  let tokenOut;

  // Mock ERC20 token for testing
  const MockERC20 = {
    deploy: async (name, symbol) => {
      const MockToken = await ethers.getContractFactory("MockERC20");
      return await MockToken.deploy(name, symbol);
    }
  };

  beforeEach(async function () {
    [owner, user, feeRecipient] = await ethers.getSigners();

    // Deploy mock facilitator (simplified - in production use actual x402 facilitator)
    const MockFacilitator = await ethers.getContractFactory("MockFacilitator");
    mockFacilitator = await MockFacilitator.deploy();

    // Deploy mock DEX routers
    const MockDEX = await ethers.getContractFactory("MockUniswapV2Router");
    mockVVS = await MockDEX.deploy();
    mockCrona = await MockDEX.deploy();

    // Deploy mock tokens
    tokenIn = await MockERC20.deploy("Test Input", "TIN");
    tokenOut = await MockERC20.deploy("Test Output", "TOUT");

    // Mint tokens to user
    await tokenIn.mint(user.address, ethers.parseEther("1000000"));
    await tokenOut.mint(mockVVS.address, ethers.parseEther("1000000"));
    await tokenOut.mint(mockCrona.address, ethers.parseEther("1000000"));

    // Deploy CLECORouter
    const CLECORouter = await ethers.getContractFactory("CLECORouter");
    router = await CLECORouter.deploy(
      await mockFacilitator.getAddress(),
      feeRecipient.address
    );
  });

  describe("Deployment", function () {
    it("Should set the right facilitator and fee recipient", async function () {
      expect(await router.facilitator()).to.equal(await mockFacilitator.getAddress());
      expect(await router.feeRecipient()).to.equal(feeRecipient.address);
    });

    it("Should set default fee to 20 bps (0.2%)", async function () {
      expect(await router.feeBps()).to.equal(20);
    });
  });

  describe("Optimized Swap Execution", function () {
    it("Should create and execute split swap across multiple DEXs", async function () {
      const amountIn = ethers.parseEther("1000");
      const minTotalOut = ethers.parseEther("980");

      // Approve router
      await tokenIn.connect(user).approve(await router.getAddress(), amountIn);

      // Define routes
      const routes = [
        {
          dexRouter: await mockVVS.getAddress(),
          path: [await tokenIn.getAddress(), await tokenOut.getAddress()],
          amountIn: ethers.parseEther("600"),
          minAmountOut: ethers.parseEther("590"),
        },
        {
          dexRouter: await mockCrona.getAddress(),
          path: [await tokenIn.getAddress(), await tokenOut.getAddress()],
          amountIn: ethers.parseEther("400"),
          minAmountOut: ethers.parseEther("390"),
        },
      ];

      // Execute swap
      const tx = await router.connect(user).createAndExecutePlan(
        routes,
        await tokenIn.getAddress(),
        await tokenOut.getAddress(),
        minTotalOut
      );

      const receipt = await tx.wait();

      // Check events
      const planCreatedEvent = receipt.logs.find(
        (log) => log.topics[0] === ethers.id("ExecutionPlanCreated(bytes32,address,uint256)")
      );
      expect(planCreatedEvent).to.not.be.undefined;

      // Check that plan was executed
      const planId = "0x" + planCreatedEvent.topics[1].slice(-64);
      const plan = await router.getPlan(planId);
      expect(plan.executed).to.be.true;
    });

    it("Should revert if deadline exceeded", async function () {
      const amountIn = ethers.parseEther("1000");

      await tokenIn.connect(user).approve(await router.getAddress(), amountIn);

      const routes = [
        {
          dexRouter: await mockVVS.getAddress(),
          path: [await tokenIn.getAddress(), await tokenOut.getAddress()],
          amountIn: ethers.parseEther("1000"),
          minAmountOut: ethers.parseEther("980"),
        },
      ];

      // Fast forward time past deadline
      await time.increase(2000); // 2000 seconds > 1800 deadline

      await expect(
        router.connect(user).createAndExecutePlan(
          routes,
          await tokenIn.getAddress(),
          await tokenOut.getAddress(),
          ethers.parseEther("980")
        )
      ).to.be.revertedWith("Plan expired");
    });

    it("Should revert if minimum output not met", async function () {
      const amountIn = ethers.parseEther("1000");
      const minTotalOut = ethers.parseEther("10000"); // Unrealistically high

      await tokenIn.connect(user).approve(await router.getAddress(), amountIn);

      const routes = [
        {
          dexRouter: await mockVVS.getAddress(),
          path: [await tokenIn.getAddress(), await tokenOut.getAddress()],
          amountIn: ethers.parseEther("1000"),
          minAmountOut: ethers.parseEther("500"),
        },
      ];

      // Mock facilitator will fail if condition not met
      await mockFacilitator.setShouldFail(true);

      await expect(
        router.connect(user).createAndExecutePlan(
          routes,
          await tokenIn.getAddress(),
          await tokenOut.getAddress(),
          minTotalOut
        )
      ).to.be.reverted;
    });
  });

  describe("Risk Management", function () {
    it("Should allow owner to toggle emergency pause", async function () {
      await router.connect(owner).toggleEmergencyPause();
      expect(await router.emergencyPause()).to.be.true;

      await router.connect(owner).toggleEmergencyPause();
      expect(await router.emergencyPause()).to.be.false;
    });

    it("Should prevent swaps when emergency paused", async function () {
      await router.connect(owner).toggleEmergencyPause();

      const amountIn = ethers.parseEther("1000");
      await tokenIn.connect(user).approve(await router.getAddress(), amountIn);

      const routes = [
        {
          dexRouter: await mockVVS.getAddress(),
          path: [await tokenIn.getAddress(), await tokenOut.getAddress()],
          amountIn: ethers.parseEther("1000"),
          minAmountOut: ethers.parseEther("980"),
        },
      ];

      await expect(
        router.connect(user).createAndExecutePlan(
          routes,
          await tokenIn.getAddress(),
          await tokenOut.getAddress(),
          ethers.parseEther("980")
        )
      ).to.be.revertedWith("Emergency pause active");
    });

    it("Should allow owner to update risk parameters", async function () {
      await router.connect(owner).setVolatilityPauseThreshold(10);
      expect(await router.volatilityPauseThreshold()).to.equal(10);

      await router.connect(owner).setMaxPoolImpact(15);
      expect(await router.maxPoolImpact()).to.equal(15);

      await router.connect(owner).setFeeBps(30);
      expect(await router.feeBps()).to.equal(30);
    });
  });

  describe("Fee Collection", function () {
    it("Should collect fees on successful swaps", async function () {
      const amountIn = ethers.parseEther("1000");
      await tokenIn.connect(user).approve(await router.getAddress(), amountIn);

      const routes = [
        {
          dexRouter: await mockVVS.getAddress(),
          path: [await tokenIn.getAddress(), await tokenOut.getAddress()],
          amountIn: ethers.parseEther("1000"),
          minAmountOut: ethers.parseEther("980"),
        },
      ];

      const balanceBefore = await tokenOut.balanceOf(feeRecipient.address);

      await router.connect(user).createAndExecutePlan(
        routes,
        await tokenIn.getAddress(),
        await tokenOut.getAddress(),
        ethers.parseEther("980")
      );

      const balanceAfter = await tokenOut.balanceOf(feeRecipient.address);
      expect(balanceAfter).to.be.gt(balanceBefore);
    });
  });
});

// Mock contracts for testing
contract("MockFacilitator", function () {
  // This would be a separate contract file in production
});

contract("MockUniswapV2Router", function () {
  // This would be a separate contract file in production
});

contract("MockERC20", function () {
  // This would be a separate contract file in production
});

