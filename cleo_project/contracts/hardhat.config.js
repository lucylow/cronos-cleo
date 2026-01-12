require("@nomicfoundation/hardhat-toolbox");
require("@nomicfoundation/hardhat-verify");
require("dotenv").config();

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  solidity: {
    version: "0.8.20",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200,
        viaIR: true, // Required for Cronos
      },
    },
  },
  networks: {
    hardhat: {
      chainId: 1337,
    },
    cronos_testnet: {
      url: process.env.CRONOS_TESTNET_RPC || "https://evm-t3.cronos.org",
      chainId: 338,
      accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : [],
      gasPrice: 500000000000, // 500 gwei
    },
    cronos_mainnet: {
      url: process.env.CRONOS_MAINNET_RPC || "https://evm.cronos.org",
      chainId: 25,
      accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : [],
      gasPrice: 500000000000,
    },
  },
  etherscan: {
    apiKey: {
      cronos: process.env.CRONOSCAN_API_KEY || "",
      cronosTestnet: process.env.CRONOSCAN_API_KEY || "",
    },
    customChains: [
      {
        network: "cronos",
        chainId: 25,
        urls: {
          apiURL: "https://api.cronoscan.com/api",
          browserURL: "https://cronoscan.com",
        },
      },
      {
        network: "cronosTestnet",
        chainId: 338,
        urls: {
          apiURL: "https://api-testnet.cronoscan.com/api",
          browserURL: "https://testnet.cronoscan.com",
        },
      },
    ],
  },
  paths: {
    sources: "./",
    tests: "./test",
    cache: "./cache",
    artifacts: "./artifacts",
  },
};

