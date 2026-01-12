const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("HackathonNFT", function () {
  let nft;
  let owner;
  let user1;
  let user2;
  const name = "Test NFT";
  const symbol = "TEST";
  const maxSupply = 100;
  const mintPrice = ethers.parseEther("0.1"); // 0.1 CRO
  const maxPerWallet = 5;
  const baseURI = "ipfs://QmTestCID/";

  beforeEach(async function () {
    [owner, user1, user2] = await ethers.getSigners();

    const HackathonNFT = await ethers.getContractFactory("HackathonNFT");
    nft = await HackathonNFT.deploy(
      name,
      symbol,
      maxSupply,
      mintPrice,
      maxPerWallet,
      baseURI
    );
    await nft.waitForDeployment();
  });

  describe("Deployment", function () {
    it("Should set the right name and symbol", async function () {
      expect(await nft.name()).to.equal(name);
      expect(await nft.symbol()).to.equal(symbol);
    });

    it("Should set the right max supply", async function () {
      expect(await nft.maxSupply()).to.equal(maxSupply);
    });

    it("Should set the right mint price", async function () {
      expect(await nft.mintPrice()).to.equal(mintPrice);
    });

    it("Should set the right max per wallet", async function () {
      expect(await nft.maxPerWallet()).to.equal(maxPerWallet);
    });

    it("Should set owner correctly", async function () {
      expect(await nft.owner()).to.equal(owner.address);
    });

    it("Should have public mint disabled initially", async function () {
      expect(await nft.publicMintEnabled()).to.be.false;
    });
  });

  describe("Public Minting", function () {
    it("Should revert if public mint is disabled", async function () {
      await expect(
        nft.connect(user1).mint(1, { value: mintPrice })
      ).to.be.revertedWith("Public mint disabled");
    });

    it("Should allow minting when enabled", async function () {
      await nft.setPublicMintEnabled(true);
      await nft.connect(user1).mint(1, { value: mintPrice });
      expect(await nft.balanceOf(user1.address)).to.equal(1);
      expect(await nft.ownerOf(1)).to.equal(user1.address);
    });

    it("Should revert if incorrect payment", async function () {
      await nft.setPublicMintEnabled(true);
      await expect(
        nft.connect(user1).mint(1, { value: ethers.parseEther("0.05") })
      ).to.be.revertedWith("Incorrect ETH value");
    });

    it("Should allow minting multiple tokens", async function () {
      await nft.setPublicMintEnabled(true);
      const quantity = 3;
      await nft.connect(user1).mint(quantity, { value: mintPrice * BigInt(quantity) });
      expect(await nft.balanceOf(user1.address)).to.equal(quantity);
    });

    it("Should enforce max per wallet limit", async function () {
      await nft.setPublicMintEnabled(true);
      await nft.connect(user1).mint(maxPerWallet, { value: mintPrice * BigInt(maxPerWallet) });
      await expect(
        nft.connect(user1).mint(1, { value: mintPrice })
      ).to.be.revertedWith("Exceeds wallet mint limit");
    });

    it("Should enforce max supply", async function () {
      await nft.setPublicMintEnabled(true);
      // Mint up to max supply
      await nft.connect(user1).mint(maxSupply, { value: mintPrice * BigInt(maxSupply) });
      await expect(
        nft.connect(user2).mint(1, { value: mintPrice })
      ).to.be.revertedWith("Exceeds max supply");
    });

    it("Should track minted count per wallet", async function () {
      await nft.setPublicMintEnabled(true);
      await nft.connect(user1).mint(2, { value: mintPrice * 2n });
      expect(await nft.mintedByWallet(user1.address)).to.equal(2);
    });
  });

  describe("Owner Minting", function () {
    it("Should allow owner to mint without payment", async function () {
      await nft.ownerMint(user1.address, 5);
      expect(await nft.balanceOf(user1.address)).to.equal(5);
    });

    it("Should revert if non-owner tries to ownerMint", async function () {
      await expect(
        nft.connect(user1).ownerMint(user1.address, 1)
      ).to.be.revertedWithCustomError(nft, "OwnableUnauthorizedAccount");
    });

    it("Should respect max supply in ownerMint", async function () {
      await nft.ownerMint(owner.address, maxSupply);
      await expect(
        nft.ownerMint(owner.address, 1)
      ).to.be.revertedWith("Exceeds max supply");
    });
  });

  describe("Metadata", function () {
    it("Should return correct token URI", async function () {
      await nft.setPublicMintEnabled(true);
      await nft.connect(user1).mint(1, { value: mintPrice });
      const tokenURI = await nft.tokenURI(1);
      expect(tokenURI).to.equal(`${baseURI}1.json`);
    });

    it("Should revert for nonexistent token", async function () {
      await expect(nft.tokenURI(999)).to.be.revertedWith("Nonexistent token");
    });
  });

  describe("Admin Functions", function () {
    it("Should allow owner to toggle public mint", async function () {
      await nft.setPublicMintEnabled(true);
      expect(await nft.publicMintEnabled()).to.be.true;
      await nft.setPublicMintEnabled(false);
      expect(await nft.publicMintEnabled()).to.be.false;
    });

    it("Should allow owner to update mint price", async function () {
      const newPrice = ethers.parseEther("0.2");
      await nft.setMintPrice(newPrice);
      expect(await nft.mintPrice()).to.equal(newPrice);
    });

    it("Should allow owner to update max per wallet", async function () {
      const newLimit = 10;
      await nft.setMaxPerWallet(newLimit);
      expect(await nft.maxPerWallet()).to.equal(newLimit);
    });

    it("Should allow owner to update base URI", async function () {
      const newURI = "ipfs://QmNewCID/";
      await nft.setBaseURI(newURI);
      await nft.setPublicMintEnabled(true);
      await nft.connect(user1).mint(1, { value: mintPrice });
      expect(await nft.tokenURI(1)).to.equal(`${newURI}1.json`);
    });

    it("Should revert if non-owner tries admin functions", async function () {
      await expect(
        nft.connect(user1).setPublicMintEnabled(true)
      ).to.be.revertedWithCustomError(nft, "OwnableUnauthorizedAccount");
    });
  });

  describe("Withdraw", function () {
    it("Should allow owner to withdraw funds", async function () {
      await nft.setPublicMintEnabled(true);
      await nft.connect(user1).mint(2, { value: mintPrice * 2n });
      
      const balanceBefore = await ethers.provider.getBalance(owner.address);
      const tx = await nft.withdraw(owner.address);
      const receipt = await tx.wait();
      const gasUsed = receipt.gasUsed * receipt.gasPrice;
      const balanceAfter = await ethers.provider.getBalance(owner.address);
      
      // Balance should increase by approximately (mintPrice * 2 - gasUsed)
      expect(balanceAfter).to.be.gt(balanceBefore);
    });

    it("Should revert if non-owner tries to withdraw", async function () {
      await expect(
        nft.connect(user1).withdraw(user1.address)
      ).to.be.revertedWithCustomError(nft, "OwnableUnauthorizedAccount");
    });

    it("Should revert if withdrawing to zero address", async function () {
      await expect(
        nft.withdraw(ethers.ZeroAddress)
      ).to.be.revertedWith("Zero address");
    });
  });

  describe("Free Mint (price = 0)", function () {
    it("Should allow free minting when price is 0", async function () {
      await nft.setMintPrice(0);
      await nft.setPublicMintEnabled(true);
      await nft.connect(user1).mint(1);
      expect(await nft.balanceOf(user1.address)).to.equal(1);
    });
  });
});
