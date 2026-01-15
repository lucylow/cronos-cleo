**Cronos-Pay — Agentic Payments, Batching & HITL**
==================================================

**Production-grade Hardhat + Relayer + Agent + HITL scaffold**_Comprehensive README with architecture, contracts, deploy scripts, server, frontend, tests, monitoring, security and operational runbook._



**Project summary & goals**
===========================

**Cronos-Pay** is an opinionated, production-grade scaffold for:

*   EVM-native payments on Cronos (native CRO + ERC-20)
    
*   Atomic multi-leg batching (single logical finality from multiple execution paths)
    
*   Agentic execution: an AI agent that observes on-chain & off-chain data, simulates outcomes and emits deterministic execution _intents_ (signed, auditable)
    
*   Server relayer that assembles batches, optionally signs & submits, or broadcasts signed client payloads
    
*   Human-in-the-Loop (HITL) workflow for flagged transactions: queueing, operator review, audit trail
    
*   Developer-friendly SDKs, Hardhat integration & test harness
    

Primary goals:

*   Reliability and auditability
    
*   Practical economics (batching reduces gas; relayer headroom)
    
*   Security & production readiness
    
*   Easy developer onboarding (examples + tests)
    

**High-level architecture**
===========================

Mermaid block diagram (paste into a Mermaid renderer in README previewers that support Mermaid):

flowchart LR

  subgraph AgentLayer

    A1\[Market & Oracles\]

    A2\[Perception / Feature Extractor\]

    A3\[Reasoning & Simulator\]

    A4\[Intent Generator\]

  end

  subgraph OffchainRelayer

    R1\[Batch Builder & Atomicizer\]

    R2\[Dry-run Sandbox\]

    R3\[Signer (server wallet / client signed tx)\]

    R4\[Tx Broadcaster\]

  end

  subgraph OnChain

    C1\[MultiSend / Atomic Contract\]

    C2\[DEXes / AMMs / Liquidity\]

    C3\[Finality Lock\]

  end

  subgraph HITL

    H1\[Queue / BullMQ\]

    H2\[Operator UI\]

    H3\[Audit DB\]

  end

  A1 --> A2 --> A3 --> A4 --> R1

  R1 --> R2 --> R3 --> R4 --> C1

  C1 --> C2 --> C3 --> H3

  H1 --> H2

  R1 --flagged--> H1

  C1 --events--> AgentLayer

  R4 --receipt--> H3

Short explanation:

*   The **agent** takes signals (on-chain state, mempool, oracles) → encodes → simulates → outputs **structured intents** (deterministic plan: routes, amounts, time windows, conditions).
    
*   The **relayer** builds atomic batches, dry-runs them in a sandbox (mirror state), optionally signs them (server) or asks client to sign, broadcasts, and monitors.
    
*   The **on-chain** contract(s) implement atomic multi-call / multi-send and finality semantics.
    
*   **HITL**: transactions flagged by scoring rules are queued for human review; operator actions are recorded in audit logs.
    

**Repository layout (recommended)**
===================================

/ (repo root)

├─ contracts/

│  ├─ MultiSend.sol

│  ├─ BatchAtomic.sol

│  └─ interfaces/

├─ scripts/

│  ├─ deploy.ts

│  └─ verify.ts

├─ frontend/

│  ├─ src/

│  │  ├─ wallet/

│  │  ├─ components/

│  │  └─ pages/

│  └─ package.json

├─ server/

│  ├─ src/

│  │  ├─ index.ts

│  │  ├─ auth.ts

│  │  ├─ gas.ts

│  │  ├─ batch.ts

│  │  ├─ monitor.ts

│  │  └─ hitl/

│  ├─ package.json

│  └─ Dockerfile

├─ test/

│  ├─ contracts/

│  └─ integration/

├─ docker-compose.yml

├─ hardhat.config.ts

└─ README.md

**Prerequisites**
=================

*   Node.js >= 18
    
*   npm or yarn
    
*   Hardhat 2.x
    
*   PostgreSQL (for audit / HITL)
    
*   Redis (for BullMQ)
    
*   Cronos testnet/mainnet RPC: provider or QuickNode/Chainstack
    
*   Optional: GPU/CPU for agent inference (if model is heavy). Agent may also use hosted inference.
    

**Smart Contracts**
===================

This section gives contract outlines, key invariants, and example code.

**Design goals**
----------------

*   Atomicity: multiple legs (calls/transfers) in a single transaction should either all succeed or the tx reverts. This prevents partial settlement.
    
*   Gas efficiency: minimize SSTORE, favor events & efficient loops.
    
*   Clear interface for relayer & client flows (meta-transactions / multi-sig as needed).
    
*   Minimal on-chain logic; complex decisioning off-chain.
    

**MultiSend / MultiNativeSend (simple example)**
------------------------------------------------

contracts/MultiSend.sol

// SPDX-License-Identifier: MIT

pragma solidity ^0.8.20;

/// @title Simple multi-send for native CRO transfers

contract MultiSend {

    function multiNativeSend(address\[\] calldata recipients, uint256\[\] calldata amounts) external payable {

        uint256 n = recipients.length;

        require(n == amounts.length, "len mismatch");

        uint256 total = 0;

        for (uint i = 0; i < n; ++i) {

            total += amounts\[i\];

        }

        require(msg.value == total, "wrong total");

        for (uint i = 0; i < n; ++i) {

            (bool ok,) = recipients\[i\].call{value: amounts\[i\]}("");

            require(ok, "transfer failed");

        }

    }

}

**Notes**

*   This basic contract is atomic: if any send fails, the whole tx reverts.
    
*   For ERC-20 batching, use transferFrom with pre-approved allowances or a token-transfer wrapper.
    

**BatchAtomic (higher-level; supports arbitrary calls)**
--------------------------------------------------------

contracts/BatchAtomic.sol

// SPDX-License-Identifier: MIT

pragma solidity ^0.8.20;

contract BatchAtomic {

    // Execute a series of low-level calls, reverting on any failure.

    function batchExecute(address\[\] calldata targets, bytes\[\] calldata data, uint256\[\] calldata value) external payable returns (bytes\[\] memory results) {

        require(targets.length == data.length && data.length == value.length, "len mismatch");

        uint256 n = targets.length;

        results = new bytes\[\](n);

        for (uint i = 0; i < n; ++i) {

            (bool success, bytes memory res) = targets\[i\].call{value: value\[i\]}(data\[i\]);

            require(success, "call failed");

            results\[i\] = res;

        }

    }

}

**Security**

*   Be careful with reentrancy; prefer patterns where the contract is only used as a delegatecall or controlled by whitelisted relayers.
    
*   Consider checks-effects-interactions, and use ReentrancyGuard if stateful.
    

**ABI snippets**
================

Keep ABI files in artifacts/ or export minimal JSON for server consumption.

\[

  {

    "inputs": \[

      {"internalType":"address\[\]","name":"targets","type":"address\[\]"},

      {"internalType":"bytes\[\]","name":"data","type":"bytes\[\]"},

      {"internalType":"uint256\[\]","name":"value","type":"uint256\[\]"}

    \],

    "name":"batchExecute",

    "outputs":\[{"internalType":"bytes\[\]","name":"results","type":"bytes\[\]"}\],

    "stateMutability":"payable",

    "type":"function"

  }

\]

**Hardhat setup & deployment**
==============================

Example hardhat.config.ts (ethers v6 plugin):

import { HardhatUserConfig } from "hardhat/config";

import "@nomicfoundation/hardhat-toolbox";

import dotenv from "dotenv";

dotenv.config();

const config: HardhatUserConfig = {

  solidity: "0.8.20",

  networks: {

    cronoTest: {

      url: process.env.CRONOS\_RPC\_TESTNET,

      chainId: 338,

      accounts: process.env.DEPLOY\_PRIVATE\_KEY ? \[process.env.DEPLOY\_PRIVATE\_KEY\] : \[\]

    },

    cronoMain: {

      url: process.env.CRONOS\_RPC\_MAINNET,

      chainId: 25,

      accounts: process.env.DEPLOY\_PRIVATE\_KEY ? \[process.env.DEPLOY\_PRIVATE\_KEY\] : \[\]

    }

  }

};

export default config;

### **Deploy script scripts/deploy.ts**

import { ethers } from "hardhat";

async function main() {

  const MultiSend = await ethers.getContractFactory("MultiSend");

  const ms = await MultiSend.deploy();

  await ms.waitForDeployment();

  console.log("MultiSend deployed to", await ms.getAddress());

}

main().catch((err)=>{ console.error(err); process.exit(1); });

### **Commands**

\# install deps

npm install

\# compile

npx hardhat compile

\# deploy to testnet

npx hardhat run scripts/deploy.ts --network cronoTest

**Backend / Relayer / API Server**
==================================

This is the operational heart: gas oracle, batch assembly, verification, broadcast, monitoring, HITL enqueue.

We recommend building server in **TypeScript**. Key packages:

*   express / fastify
    
*   ethers v6
    
*   pg (Postgres)
    
*   bullmq (Redis)
    
*   axios
    
*   jsonwebtoken
    
*   winston or pino for structured logs
    

**Server responsibilities**
---------------------------

1.  **Authentication**: Sign-in with Ethereum (challenge/response), issue JWT for UI/admin.
    
2.  **Gas recommendation endpoint**: GET /gas/recommendation — uses provider.getFeeData().
    
3.  **Estimate**: POST /gas/estimate — provider.estimateGas.
    
4.  **Batch assembly**: receive "intent" (structured) from agent, compose on-chain payload, call estimateGas, create signed packet / server-signed tx or return packet to client for signature.
    
5.  **Dry-run sandbox**: use a mirrored node or a local fork to call static eth\_call with stateOverride to simulate.
    
6.  **Broadcast**: POST /tx/send (signed tx hex) or POST /tx/send (server mode).
    
7.  **Monitor**: POST /tx/monitor with txHash; poll for confirmations, push events to audit DB & sockets.
    
8.  **Payments observe**: insert payment row & run risk scoring; auto-approve or enqueue for HITL.
    
9.  **Admin**: endpoints for operator UI (list pending, review action).
    

**Example minimal server sketch (TypeScript, Express)**
-------------------------------------------------------

server/src/index.ts — skeleton

import express from "express";

import { JsonRpcProvider, Wallet, parseUnits } from "ethers";

import bodyParser from "body-parser";

import { getGasRecommendation } from "./gasUtils"; // implement as described earlier

import { enqueueForReview, simpleRiskScore } from "./hitl"; // implemented in hitl.ts

import { pool } from "./db"; // Postgres pool

const app = express();

app.use(bodyParser.json());

const provider = new JsonRpcProvider(process.env.CRONOS\_RPC);

const PORT = process.env.PORT || 3001;

app.get("/gas/recommendation", async (req, res) => {

  const rec = await getGasRecommendation();

  res.json(rec);

});

app.post("/payments/observe", async (req, res) => {

  const { txHash, chainId, payer, amountWei, tokenAddress } = req.body;

  // insert into payments table then risk-score / enqueue

  const id = await insertPayment(txHash, chainId, payer, amountWei, tokenAddress);

  const risk = await simpleRiskScore({ txHash, payer, amountWei, tokenAddress });

  if (risk.flagged) {

    await enqueueForReview({ id, txHash, payer, amount: amountWei, chainId, tokenAddress });

    return res.json({ ok: true, status: "flagged" });

  } else {

    await markPaymentApproved(id);

    return res.json({ ok: true, status: "approved" });

  }

});

app.post("/tx/send", async (req, res) => {

  const { signedTx } = req.body;

  const tx = await provider.sendTransaction(signedTx);

  res.json({ ok: true, txHash: tx.hash });

});

app.listen(PORT, ()=> console.log("server listening", PORT));

**Note**: Above code is a sketch. See later sections for full typed modules.

**Auth: Sign-in with Ethereum**
===============================

Flow:

1.  POST /auth/challenge with { address } → server returns challenge message with nonce
    
2.  Client signs message → POST /auth/verify with { address, signature } → server verifies ethers.verifyMessage → issues JWT
    

Server stores challenges (Redis or DB) and expires them after 5 minutes.

Security:

*   Use httpOnly cookies for JWT in production (reduce XSS risk).
    
*   Rate limit challenge endpoints.
    

**Gas & send utilities**
========================

getGasRecommendation():

*   call provider.getFeeData()
    
*   if EIP-1559 fields present, return maxFeePerGas & maxPriorityFeePerGas
    
*   else fallback to provider.getGasPrice()
    
*   optionally query third-party oracles
    

sendTxWithOptimalGas(signer, txRequest):

*   estimate gas limit: provider.estimateGas(txRequest)
    
*   multiply by buffer (1.2x)
    
*   attach either EIP-1559 fields or gasPrice
    
*   signer.sendTransaction(tx)
    

**Batch assembler & atomicizer (server side)**
==============================================

Responsibilities:

*   Accept intents (structured JSON)
    
*   Map intents to contract calls (targets/data/value)
    
*   Encode calldata using contract ABI (ethers.Interface.encodeFunctionData)
    
*   Estimate gas & cost
    
*   Build batch payload (array of targets + data + value)
    
*   Optionally dry-run in sandbox
    
*   Lock & sign or return to client for signing
    

Example pseudocode:

async function assembleBatch(intent: Intent): Promise {

  // intent: { routes: \[{dex, path, amount}\], constraints: {minOut, slippage}, meta }

  const calls = \[\];

  for (const route of intent.routes) {

    const data = dexRouter.interface.encodeFunctionData('swapExactAmount', \[route.path, route.amount, ...\]);

    calls.push({ to: route.routerAddress, data, value: 0n });

  }

  // pack into batchExecute call

  const batchContract = new Contract(BATCH\_ADDR, BATCH\_ABI, provider);

  const calldata = batchContract.interface.encodeFunctionData('batchExecute', \[calls.map(c=>c.to), calls.map(c=>c.data), calls.map(c=>c.value)\]);

  return { to: BATCH\_ADDR, data: calldata, value: calls.reduce(...) };

}

**Dry-run sandbox**
===================

Approaches:

*   Use eth\_call against a local fork (Hardhat) with state override to simulate.
    
*   Or call simulation RPC if your provider supports debug\_traceTransaction / eth\_call with stateOverride.
    
*   Purpose: Validate that the batch will execute without reverts and measure gas estimation.
    

**Monitor & verify**
====================

Implement a monitorTx(txHash, options) that polls provider.getTransactionReceipt(txHash) until receipt && receipt.blockNumber and confirmations >= required. On success, parse logs and persist proof in DB.

Push events to WebSocket (socket.io) for UI updates and to audit logs.

**Agent (AI) — Simulation & Intent Generator**
==============================================

This section describes the agent architecture (not the model weights). The agent should be **deterministic** in its decisioning: same input → same intent. Determinism implies using deterministic pseudorandom seeds or avoiding randomness.

**Agent responsibilities**
--------------------------

*   Ingests:
    
    *   On-chain state (balances, pool depths)
        
    *   Mempool / pending orders
        
    *   Price oracles
        
    *   Historical execution data
        
*   Encodes state into features (quantized tensors)
    
*   Runs several candidate policies (greedy, slippage-sensitive, latency-aware)
    
*   Forward simulates candidate execution against a local state mirror
    
*   Scores candidate outcomes (expected cost, risk, MEV exposure)
    
*   Produces one or more **structured intents** with constraints (maxPrice, minOut, expiry block, preconditions)
    
*   Signs intent with agent key (or HMAC) for authenticity
    

**Intent schema (example)**
---------------------------

{

  "intentId":"uuid",

  "createdAt":"2026-01-08T12:34Z",

  "agent":"agent-v1.2",

  "payer":"0xabc...",

  "actions":\[

    {"type":"swap","router":"0x...", "path":\["0xA","0xB"\], "amountIn":"1000000000000000000", "minOut":"990000000000000000"},

    {"type":"transfer","to":"0xmerchant","amount":"990000000000000000"}

  \],

  "constraints":{"maxFeeGwei":10,"deadline":1730000000},

  "signature":"0x..."

}

**Simulation approach**
-----------------------

*   Run forward sim on a state snapshot (block N).
    
*   For each candidate, compute:
    
    *   execution cost (gas + priority fees)
        
    *   slippage / realized price
        
    *   expected residuals
        
    *   risk score (addresses, chain reorg probability)
        
*   Pick the top candidate(s), generate intents.
    

**Tip**: Use a deterministic inference (fixed seeds) and log all inputs for auditability.

**Human-in-the-Loop (HITL) subsystem**
======================================

HITL handles flagged transactions and operator approval workflows.

**DB schema**
-------------

server/db/schema.sql — core tables:

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE operators (

  id uuid PRIMARY KEY DEFAULT uuid\_generate\_v4(),

  email text UNIQUE NOT NULL,

  name text,

  role text,

  created\_at timestamptz DEFAULT now()

);

CREATE TABLE payments (

  id uuid PRIMARY KEY DEFAULT uuid\_generate\_v4(),

  tx\_hash text UNIQUE,

  payer text,

  amount numeric(78,0),

  token\_address text,

  status text DEFAULT 'pending\_verification',

  risk\_score integer DEFAULT 0,

  flagged\_reason text,

  created\_at timestamptz DEFAULT now(),

  updated\_at timestamptz DEFAULT now()

);

CREATE TABLE reviews (

  id uuid PRIMARY KEY DEFAULT uuid\_generate\_v4(),

  payment\_id uuid REFERENCES payments(id) ON DELETE CASCADE,

  operator\_id uuid REFERENCES operators(id),

  action text,

  comment text,

  evidence jsonb,

  created\_at timestamptz DEFAULT now()

);

CREATE TABLE audit\_logs (

  id uuid PRIMARY KEY DEFAULT uuid\_generate\_v4(),

  entity\_type text,

  entity\_id uuid,

  actor text,

  action text,

  details jsonb,

  created\_at timestamptz DEFAULT now()

);

**Queueing & Worker**
---------------------

*   Use **BullMQ** for queueing
    
*   Worker flow:
    
    *   Fetch job (paymentId)
        
    *   Gather evidence: tx, receipt, block, payer balance, historical txs (via indexer)
        
    *   Update payments.status='flagged'
        
    *   Emit socket event to operator UI
        

**Operator UI**
---------------

*   Real-time via socket.io
    
*   Present: tx hash, payer, amount, routes, evidence (tx logs, proof of funds), risk score, suggested action
    
*   Actions: approve / reject / request more info — each action writes to reviews and audit\_logs
    

**Timeout & policies**
----------------------

*   Set TTL for jobs (e.g., 2 hours). If no operator responds, escalate or auto-fallback (e.g., safe revert or lower priority execution).
    

**Frontend (Wallet + UX)**
==========================

We recommend React + ethers v6.

Key pieces:

*   WalletProvider (inject + WalletConnect) — use BrowserProvider and @walletconnect/web3-provider or web3modal v2.
    
*   Connect UI: connect/disconnect, display account, ENS, balance, chainId, quick switch to Cronos testnet/mainnet via wallet\_addEthereumChain.
    
*   Sign-in flow: challenge → signature → obtain JWT for admin features
    
*   Payment flow:
    
    *   User creates payment (amount, token, merchant)
        
    *   Client calls POST /intent/create or the agent returns intent for user to approve
        
    *   Optionally, user signs final transaction locally (preferred) and sends signed tx to server for broadcast, or server broadcasts if the user granted permission
        
*   HITL admin UI integration: connect via Socket.io, show review queue, take actions
    

Example WalletProvider snippet (minimal):

import React, {createContext, useContext, useState, useEffect} from "react";

import {BrowserProvider} from "ethers";

const WalletContext = createContext(null);

export function WalletProvider({children}) {

  const \[provider, setProvider\] = useState(null);

  const \[signer, setSigner\] = useState(null);

  const \[account, setAccount\] = useState(null);

  useEffect(() => {

    if (window.ethereum) {

      const p = new BrowserProvider(window.ethereum);

      setProvider(p);

    }

  }, \[\]);

  const connect = async () => {

    await window.ethereum.request({method: "eth\_requestAccounts"});

    const p = new BrowserProvider(window.ethereum);

    setProvider(p);

    const s = await p.getSigner();

    setSigner(s);

    setAccount(await s.getAddress());

  };

  return {children};

}

**Batching patterns (on-chain & off-chain)**
============================================

**On-chain multicall**
----------------------

*   Use BatchAtomic contract to include arbitrary calls.
    
*   Pros: atomic guarantees; single receipt.
    
*   Cons: all contracts must be accessible; gas cost may be high for some ops.
    

**Off-chain aggregation + on-chain settlement**
-----------------------------------------------

*   Relayer collects many mini-payments into a single on-chain settlement using MultiSend. Each user signs an off-chain proof of payment; relayer includes proofs in batch.
    
*   Pros: saves gas; flexible.
    
*   Cons: requires trust model (relayer integrity) or cryptographic proofs.
    

**Meta-transactions & account abstraction**
-------------------------------------------

*   Use EIP-712 signed intents so relayer can submit on behalf of users.
    
*   Provide signed envelope containing intent + nonce + expiry + signature.
    

**Gas & fee handling (Cronos specifics)**
=========================================

Cronos uses EIP-1559-style or hybrid fee market. Use provider.getFeeData().

Sample gasUtils.js logic:

export async function getGasRecommendation(provider) {

  const feeData = await provider.getFeeData();

  if (feeData.maxFeePerGas && feeData.maxPriorityFeePerGas) {

    return { supports1559:true, maxFeePerGas: feeData.maxFeePerGas, maxPriorityFeePerGas: feeData.maxPriorityFeePerGas };

  } else {

    return { supports1559:false, gasPrice: feeData.gasPrice || parseUnits("1", "gwei") };

  }

}

**Presets**: create slow / normal / fast multipliers of priority fee & maxFee.

**Gas estimation**:

*   Always run estimateGas() for the final payload.
    
*   Add buffer (20–30%) then cap at reasonable upper bound.
    

**Testing & QA**
================

**Unit tests**
--------------

*   Test contracts: multi-send success/fail paths, revert scenarios, reentrancy attempts.
    
*   Use Hardhat Mocha + Chai.
    

Example test:

describe("MultiSend", () => {

  it("sends to multiple accounts", async () => {

    const \[owner, a,b\] = await ethers.getSigners();

    const MultiSend = await ethers.getContractFactory("MultiSend");

    const ms = await MultiSend.deploy();

    await owner.sendTransaction({to: ms.address, value: parseEther("1.0")});

    await expect(ms.multiNativeSend(\[a.address,b.address\],\[parseEther("0.4"),parseEther("0.6")\],{value:parseEther("1.0")})).to.not.be.reverted;

  });

});

**Integration tests**
---------------------

*   Spin up local fork (Hardhat) and run end-to-end: agent intent → batch assemble → dry-run → submit → receipts.
    

**Fuzzing & property testing**
------------------------------

*   Use foundry or echidna for property testing (e.g., invariants: total value in equals total out).
    
*   For server: property tests for IDempotence keys & duplicates.
    

**Monitoring, Observability & SLOs**
====================================

Metrics to export:

*   txs/day, txs/sec
    
*   avg gas / batch
    
*   % of auto approvals vs HITL
    
*   queue length & avg review time
    
*   API latency / error rate
    

Tools:

*   Prometheus for metrics, Grafana dashboards
    
*   Loki / Elastic for logs
    
*   Tracing: OpenTelemetry, Jaeger
    
*   Alerting: PagerDuty / Opsgenie for critical alerts (e.g., relayer down, high reverts)
    

SLO examples:

*   99.9% uptime for relayer API
    
*   <30s avg time to broadcast after user signs
    
*   <5% of batches revert in production
    

**Security & hardening**
========================

*   **Key management**: do NOT store DEPLOY\_PRIVATE\_KEY in repo. Use KMS (AWS KMS, GCP KMS) or HSM. Use ephemeral signing services for production.
    
*   **Least privilege**: relayer wallet should have limited funds with clear refill policy.
    
*   **Audits & formal verification**: budget audits for contracts and critical server logic.
    
*   **Rate limits & WAF**: protect challenge endpoints and /tx/send endpoints.
    
*   **Input validation & sanitization** on all APIs.
    
*   **Immutable audit logs** stored in DB and optionally pushed to object storage (S3 + Glacier) for retention.
    

**CI / CD (GitHub Actions example)**
====================================

.github/workflows/ci.yml (illustrative):

name: CI

on: \[push, pull\_request\]

jobs:

  test:

    runs-on: ubuntu-latest

    steps:

      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4

        with: node-version: 18

      - run: npm ci

      - run: npx hardhat compile

      - run: npx hardhat test

  deploy:

    if: github.ref == 'refs/heads/main' && github.event\_name == 'push'

    runs-on: ubuntu-latest

    steps:

      - uses: actions/checkout@v4

      - run: npm ci

      - run: npx hardhat run scripts/deploy.ts --network cronoTest

**Notes**: For production deployments, use protected branches, manual approvals, and store secrets in GitHub Actions secrets or external vault.

**Deployment (docker-compose)**
===============================

Example docker-compose.yml snippet:

version: '3.8'

services:

  server:

    build: ./server

    ports:

      - "3001:3001"

    environment:

      - DATABASE\_URL=postgres://postgres:pass@db:5432/cronos

      - REDIS\_URL=redis://redis:6379

      - CRONOS\_RPC=https://evm-t3.cronos.org

    depends\_on:

      - db

      - redis

  db:

    image: postgres:15

    environment:

      - POSTGRES\_PASSWORD=pass

      - POSTGRES\_DB=cronos

  redis:

    image: redis:7

    command: \["redis-server", "--appendonly", "yes"\]

Start:

docker-compose up --build

**Roadmap & next steps (developer & ops)**
==========================================

Short roadmap (priority):

1.  Complete end-to-end test harness & demo (testnet)
    
2.  Run closed pilot with 1 merchant + measure gas savings
    
3.  Complete security audit for contracts + relayer
    
4.  Implement full agent sandbox + deterministic logging
    
5.  Build admin HITL dashboard & operator runbooks
    
6.  Implement billing & SaaS metering
    

**Business model summary (brief)**
==================================

*   Revenue streams: tx fees (primary), batch premium, SaaS subscriptions, routing share, analytics APIs, professional services.
    
*   Unit economics: target blended take rate ~0.10% → revenue/tx $0.30 on avg $300 tx.
    
*   Push to get SaaS & enterprise for predictable revenue.
    

**Contributing**
================

We welcome contributions.

Guidelines:

*   Open an issue first for discussion.
    
*   Follow code style and linting (prettier, eslint).
    
*   Tests required for non-trivial changes.
    
*   Sign Contributor License Agreement (if project policy).
    

**License & credits**
=====================

*   Recommended: **Apache-2.0** or **MIT** (pick one).
    
*   Include SECURITY.md with disclosure process and contact.
    

**Appendix A — Example end-to-end sequence (narrative)**
========================================================

1.  Merchant integrates SDK + requests payment from consumer.
    
2.  SDK hits agent endpoint for routing (optional) or client chooses simple route.
    
3.  Agent evaluates, simulates, returns signed intent.
    
4.  Client or server builds batch payload (3 legs: swap, fee, payout) and dry-runs.
    
5.  If passes, client signs tx and returns signedTx to server OR server signs and broadcasts (if user delegated).
    
6.  Server broadcasts to Cronos RPC.
    
7.  Receipt processed; server verifies; payment observed; risk score computed.
    
8.  If flagged → queued for HITL; operator reviews & acts.
    
9.  Audit logs appended; outcome persisted.
    

**Appendix B — Useful commands & dev tips**
===========================================

Start Hardhat node (local fork):

npx hardhat node

\# in another shell

npx hardhat run scripts/deploy.ts --network localhost

Run server locally (env in .env):

cd server

npm ci

npm run dev

Run frontend:

cd frontend

npm ci

npm start

**Appendix C — Example troubleshooting & runbook**
==================================================

*   If relayer txs are failing with out of gas: check estimateGas usage and gasLimit buffer; increase EIP-1559 maxFee margin.
    
*   If many hits queued in HITL: adjust risk threshold temporarily, scale worker processes, or add auto-fallback rules.
    
*   Node RPC timeouts under load: use QuickNode / Chainstack with rate-limit management.
    

**Final notes**
---------------

This README is intended to be the central technical narrative for your repo. You can copy-paste sections into README.md and expand contract code / server modules into the repository structure shown earlier. For production, be strict about secrets, audits, and KMS.
