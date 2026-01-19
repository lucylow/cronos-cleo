# C.L.E.O. - Cronos Liquidity Execution Orchestrator

<div align="center">

**Production-Grade Agentic Payment System with AI-Powered Multi-DEX Routing**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-blue.svg)](https://www.typescriptlang.org/)
[![Solidity](https://img.shields.io/badge/Solidity-0.8.20+-blue.svg)](https://soliditylang.org/)

</div>

---

## Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Technical Stack](#technical-stack)
- [Core Components](#core-components)
- [Architecture Diagrams](#architecture-diagrams)
- [Agent System](#agent-system)
- [Smart Contracts](#smart-contracts)
- [API Documentation](#api-documentation)
- [Deployment](#deployment)
- [Development](#development)
- [Security](#security)

---

## Overview

**C.L.E.O. (Cronos Liquidity Execution Orchestrator)** is an enterprise-grade, AI-powered DeFi execution system designed for the Cronos blockchain. It provides:

- 🤖 **Multi-Agent AI System**: Orchestrated agents for liquidity analysis, route optimization, risk management, and execution
- 🔄 **Atomic Multi-DEX Swaps**: Cross-DEX routing with x402 facilitator for guaranteed atomicity
- 🛡️ **Human-in-the-Loop (HITL)**: Payment review workflow with risk scoring and operator approval
- 📊 **Real-Time Analytics**: ML-based slippage prediction, liquidity monitoring, and performance metrics
- 🔐 **Production Security**: Comprehensive audit logging, risk validation, and secure key management

---

## System Architecture

### High-Level Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        A[React Frontend<br/>TypeScript + Wagmi]
        B[Mobile Apps<br/>Web3 Wallet]
    end
    
    subgraph "API Gateway Layer"
        C[FastAPI Backend<br/>REST + WebSocket]
        D[Authentication<br/>JWT + Wallet Sign]
    end
    
    subgraph "Agent Orchestration Layer"
        E[Orchestrator Agent]
        F[Liquidity Scout]
        G[Split Optimizer]
        H[Risk Validator]
        I[Execution Agent]
        J[Performance Monitor]
        K[Message Bus<br/>Event-Driven]
    end
    
    subgraph "AI/ML Layer"
        L[Route Optimizer AI]
        M[Slippage Predictor]
        N[Liquidity Monitor]
        O[ML Models<br/>PyTorch/XGBoost]
    end
    
    subgraph "Execution Layer"
        P[x402 Executor]
        Q[Multi-Leg Coordinator]
        R[Settlement Pipeline]
        S[Gas Optimizer]
    end
    
    subgraph "HITL System"
        T[Payment Observer]
        U[Risk Scorer]
        V[Review Queue<br/>BullMQ]
        W[Operator Dashboard]
        X[Audit Logger]
    end
    
    subgraph "Blockchain Layer"
        Y[Cronos EVM<br/>Testnet/Mainnet]
        Z[CrossDEXRouter<br/>Smart Contract]
        AA[x402 Facilitator]
        AB[DEX Routers<br/>VVS/CronaSwap/MMF]
    end
    
    subgraph "Data Layer"
        AC[PostgreSQL<br/>HITL + Audit]
        AD[Redis<br/>Cache + Queue]
        AE[MCP Client<br/>Market Data]
    end
    
    A --> C
    B --> C
    C --> D
    C --> E
    E --> K
    K --> F
    K --> G
    K --> H
    K --> I
    F --> L
    G --> M
    H --> N
    L --> O
    M --> O
    N --> O
    I --> P
    P --> Q
    Q --> R
    R --> S
    S --> Z
    Z --> AA
    AA --> AB
    AB --> Y
    C --> T
    T --> U
    U --> V
    V --> W
    W --> X
    X --> AC
    K --> AD
    N --> AE
    L --> AE
    
    style E fill:#4CAF50
    style K fill:#2196F3
    style Z fill:#FF9800
    style AA fill:#FF9800
    style O fill:#9C27B0
```

### Component Architecture

```mermaid
graph LR
    subgraph "Frontend Stack"
        F1[React 18<br/>TypeScript]
        F2[Vite<br/>Build Tool]
        F3[Wagmi 3<br/>Web3 Hooks]
        F4[Viem 2<br/>Ethereum Library]
        F5[shadcn/ui<br/>Components]
        F1 --> F2
        F1 --> F3
        F3 --> F4
        F1 --> F5
    end
    
    subgraph "Backend Stack"
        B1[FastAPI<br/>Python 3.10+]
        B2[Pydantic<br/>Data Validation]
        B3[SQLAlchemy<br/>ORM]
        B4[Redis<br/>Cache/Queue]
        B5[Web3.py<br/>Blockchain]
        B1 --> B2
        B1 --> B3
        B1 --> B4
        B1 --> B5
    end
    
    subgraph "AI/ML Stack"
        ML1[PyTorch<br/>Deep Learning]
        ML2[XGBoost<br/>Ensemble]
        ML3[scikit-learn<br/>Classical ML]
        ML4[NumPy/SciPy<br/>Numerical]
        ML1 --> ML4
        ML2 --> ML4
        ML3 --> ML4
    end
    
    subgraph "Smart Contracts"
        SC1[Solidity 0.8.20]
        SC2[Hardhat<br/>Dev Framework]
        SC3[OpenZeppelin<br/>Libraries]
        SC1 --> SC2
        SC1 --> SC3
    end
    
    style F1 fill:#61DAFB
    style B1 fill:#009688
    style ML1 fill:#EE4C2C
    style SC1 fill:#363636
```

---

## Technical Stack

### Frontend
- **React 18.3** with TypeScript 5.8
- **Vite 5.4** for build tooling
- **Wagmi 3.3** + **Viem 2.44** for Web3 interactions
- **Tailwind CSS 3.4** + **shadcn/ui** for UI components
- **React Query 5.83** for server state management
- **React Router 6.30** for routing

### Backend
- **FastAPI 0.104** with Python 3.10+
- **Pydantic 2.0** for data validation
- **SQLAlchemy 2.0** for database ORM
- **Redis 5.0** for caching and job queues
- **Web3.py 6.11** for blockchain interaction
- **AsyncIO** for concurrent operations

### AI/ML
- **PyTorch 2.1** for deep learning models
- **XGBoost 2.0** for gradient boosting
- **scikit-learn 1.3** for classical ML
- **NumPy 1.26** + **SciPy 1.11** for numerical computing
- **Pandas 2.1** for data processing

### Smart Contracts
- **Solidity 0.8.20**
- **Hardhat 2.x** for development
- **OpenZeppelin** contracts library
- **x402 Facilitator** for atomic execution

### Infrastructure
- **PostgreSQL 15** for persistent storage
- **Redis 7** for caching and queues
- **Docker** for containerization
- **BullMQ** for background job processing

---

## Core Components

### 1. Multi-Agent System

The agent system uses an event-driven architecture with a message bus for inter-agent communication.

#### Agent Types

| Agent | Responsibility | Technology |
|-------|---------------|------------|
| **Orchestrator** | Coordinates all agents, manages workflow | Python/AsyncIO |
| **Liquidity Scout** | Real-time liquidity discovery across DEXs | MCP Client + Subgraphs |
| **Split Optimizer** | Optimal route splitting using ML | scipy.optimize + ML Models |
| **Risk Validator** | Pre-execution risk assessment | Rule Engine + ML |
| **Execution Agent** | x402 transaction execution | Web3.py + x402 SDK |
| **Performance Monitor** | System metrics and analytics | Prometheus + Grafana |

### 2. x402 Integration

Atomic execution across multiple DEXs using Cronos x402 facilitator:

```
User Request → AI Optimization → Route Splits → x402 Executor → 
CrossDEXRouter Contract → x402 Facilitator → Multiple DEX Routers → 
Atomic Settlement
```

### 3. HITL System

Human-in-the-loop payment review workflow:

- **Payment Observer**: Monitors on-chain transactions
- **Risk Scorer**: Evaluates risk factors (amount, frequency, patterns)
- **Review Queue**: BullMQ-based job queue for flagged payments
- **Operator Dashboard**: React-based review interface
- **Audit Logger**: Immutable audit trail for compliance

---

## Architecture Diagrams

### Agent Communication Flow

```mermaid
sequenceDiagram
    participant User
    participant API
    participant Orchestrator
    participant MessageBus
    participant LiquidityScout
    participant Optimizer
    participant RiskValidator
    participant Executor
    participant Blockchain
    
    User->>API: POST /api/v2/swap
    API->>Orchestrator: SwapRequest
    
    Orchestrator->>MessageBus: Publish(LIQUIDITY_REQUEST)
    MessageBus->>LiquidityScout: RouteRequest
    LiquidityScout->>MCP: Query Pools
    MCP-->>LiquidityScout: Pool Data
    LiquidityScout->>MessageBus: Publish(LIQUIDITY_DATA)
    
    MessageBus->>Optimizer: OptimizeRequest
    Optimizer->>ML: Predict Slippage
    ML-->>Optimizer: Predictions
    Optimizer->>Optimizer: Calculate Optimal Splits
    Optimizer->>MessageBus: Publish(OPTIMIZED_ROUTE)
    
    MessageBus->>RiskValidator: ValidateRequest
    RiskValidator->>RiskValidator: Risk Assessment
    RiskValidator->>MessageBus: Publish(VALIDATION_RESULT)
    
    alt Risk Valid
        MessageBus->>Executor: ExecuteRequest
        Executor->>x402: Prepare Operations
        x402->>Blockchain: Execute Atomic Batch
        Blockchain-->>Executor: Transaction Receipt
        Executor->>MessageBus: Publish(EXECUTION_RESULT)
    else Risk Invalid
        MessageBus->>Orchestrator: REJECTED
    end
    
    MessageBus->>API: SwapResult
    API-->>User: 200 OK + Result
```

### Transaction Execution Flow

```mermaid
flowchart TD
    Start([User Initiates Swap]) --> Validate{Validate Input}
    Validate -->|Invalid| Error([Return Error])
    Validate -->|Valid| Agent[Orchestrator Agent]
    
    Agent --> Scout[Liquidity Scout Agent]
    Scout --> Pools[Query Pools<br/>MCP + Subgraphs]
    Pools --> ML[ML Slippage Predictor]
    ML --> Optimize[Split Optimizer]
    
    Optimize --> Routes{Multiple Routes?}
    Routes -->|Yes| Multi[Multi-DEX Split]
    Routes -->|No| Single[Single DEX Route]
    
    Multi --> Risk[Risk Validator]
    Single --> Risk
    
    Risk --> RiskCheck{Risk Acceptable?}
    RiskCheck -->|High Risk| HITL[HITL Queue]
    RiskCheck -->|Acceptable| Prepare[Prepare x402 Operations]
    
    HITL --> Review[Operator Review]
    Review -->|Approved| Prepare
    Review -->|Rejected| Reject([Transaction Rejected])
    
    Prepare --> Contract[CrossDEXRouter Contract]
    Contract --> x402[x402 Facilitator]
    x402 --> DEX1[VVS Finance]
    x402 --> DEX2[CronaSwap]
    x402 --> DEX3[MM Finance]
    
    DEX1 --> Settle{All Successful?}
    DEX2 --> Settle
    DEX3 --> Settle
    
    Settle -->|Yes| Success([Atomic Success])
    Settle -->|No| Revert([Atomic Revert])
    
    Success --> Monitor[Performance Monitor]
    Monitor --> Complete([Transaction Complete])
    Revert --> Complete
    
    style Agent fill:#4CAF50
    style x402 fill:#FF9800
    style HITL fill:#F44336
    style Success fill:#4CAF50
    style Revert fill:#F44336
```

### x402 Integration Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        A[Frontend<br/>React App]
        B[User Wallet<br/>MetaMask/Crypto.com]
    end
    
    subgraph "Backend Services"
        C[x402 Executor<br/>Python Service]
        D[Route Preparer<br/>Format Conversion]
        E[Gas Estimator<br/>Fee Calculation]
    end
    
    subgraph "Smart Contract Layer"
        F[CrossDEXRouter.sol<br/>Main Router Contract]
        G[MultiSend.sol<br/>Batch Transfers]
        H[IntelligentSettlement.sol<br/>Settlement Logic]
    end
    
    subgraph "x402 Facilitator"
        I[x402 Facilitator<br/>Atomic Execution Engine]
        J[Condition Evaluator<br/>Batch Validation]
        K[Operation Executor<br/>Call Dispatcher]
    end
    
    subgraph "DEX Routers"
        L[VVS Finance<br/>Router 0x...]
        M[CronaSwap<br/>Router 0x...]
        N[MM Finance<br/>Router 0x...]
    end
    
    subgraph "Blockchain"
        O[(Cronos EVM<br/>Chain ID: 25/338)]
    end
    
    A --> B
    B --> C
    C --> D
    D --> E
    E --> F
    F --> I
    I --> J
    J --> K
    K --> L
    K --> M
    K --> N
    L --> O
    M --> O
    N --> O
    F --> G
    F --> H
    H --> I
    
    style I fill:#FF9800,stroke:#F57C00,stroke-width:3px
    style F fill:#2196F3,stroke:#1976D2,stroke-width:2px
    style O fill:#627EEA,stroke:#4C6EF5,stroke-width:2px
```

### HITL Workflow Diagram

```mermaid
stateDiagram-v2
    [*] --> PaymentObserved: On-chain TX Detected
    
    PaymentObserved --> RiskScoring: Calculate Risk Score
    
    RiskScoring --> LowRisk: Score < 50
    RiskScoring --> HighRisk: Score >= 50
    
    LowRisk --> AutoApproved: Auto-Approve
    
    HighRisk --> Enqueued: Add to Review Queue
    
    Enqueued --> EvidenceGathering: Background Worker
    
    EvidenceGathering --> OperatorNotification: WebSocket Push
    
    OperatorNotification --> PendingReview: Operator Assigned
    
    PendingReview --> Approved: Operator Approves
    PendingReview --> Rejected: Operator Rejects
    PendingReview --> Escalated: High Value
    
    Approved --> Settlement: Execute Settlement
    Rejected --> Reverted: Cancel Transaction
    
    Escalated --> MultiApproval: Requires Multiple Approvers
    MultiApproval --> Approved: All Approve
    MultiApproval --> Rejected: Any Reject
    
    Settlement --> AuditLogged: Log to Audit DB
    Reverted --> AuditLogged
    AutoApproved --> AuditLogged
    
    AuditLogged --> [*]
    
    note right of RiskScoring
        Factors:
        - Amount (≥100 CRO = +70)
        - Frequency (5+ /hr = +30)
        - Pattern Analysis
        - Address Reputation
    end note
```

### Data Flow Architecture

```mermaid
graph LR
    subgraph "Data Sources"
        DS1[On-Chain Events<br/>Web3 Event Listeners]
        DS2[MCP Server<br/>Market Data]
        DS3[Subgraph APIs<br/>The Graph]
        DS4[Historical Data<br/>PostgreSQL]
    end
    
    subgraph "Data Processing"
        DP1[Event Processor<br/>Async Workers]
        DP2[Data Pipeline<br/>ETL Jobs]
        DP3[Feature Engineering<br/>ML Preprocessing]
        DP4[Cache Layer<br/>Redis]
    end
    
    subgraph "AI/ML Models"
        ML1[Slippage Predictor<br/>XGBoost]
        ML2[Liquidity Forecaster<br/>LSTM]
        ML3[Risk Classifier<br/>Random Forest]
        ML4[Route Optimizer<br/>Reinforcement Learning]
    end
    
    subgraph "Decision Layer"
        DL1[Orchestrator<br/>Decision Engine]
        DL2[Rule Engine<br/>Business Logic]
        DL3[Risk Engine<br/>Validation]
    end
    
    subgraph "Outputs"
        OUT1[Optimized Routes<br/>JSON Response]
        OUT2[Risk Scores<br/>HITL Decisions]
        OUT3[Metrics<br/>Prometheus]
        OUT4[Audit Logs<br/>PostgreSQL]
    end
    
    DS1 --> DP1
    DS2 --> DP1
    DS3 --> DP1
    DS4 --> DP2
    
    DP1 --> DP2
    DP2 --> DP3
    DP3 --> DP4
    
    DP4 --> ML1
    DP4 --> ML2
    DP4 --> ML3
    DP4 --> ML4
    
    ML1 --> DL1
    ML2 --> DL1
    ML3 --> DL3
    ML4 --> DL1
    
    DL1 --> DL2
    DL2 --> DL3
    
    DL3 --> OUT1
    DL3 --> OUT2
    DL1 --> OUT3
    DL3 --> OUT4
    
    style ML1 fill:#9C27B0
    style ML2 fill:#9C27B0
    style ML3 fill:#9C27B0
    style ML4 fill:#9C27B0
    style DP4 fill:#FF9800
```

---

## Agent System

### Message Bus Architecture

The agent system uses a publish-subscribe message bus for asynchronous communication:

```python
# Example Agent Message
{
    "message_id": "uuid",
    "sender": "liquidity_scout",
    "receiver": "broadcast",  # or specific agent_id
    "message_type": "LIQUIDITY_DATA",
    "payload": {...},
    "timestamp": "2024-01-01T12:00:00Z",
    "priority": 3  # 1-5 scale
}
```

### Agent Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Initialized: Agent Created
    
    Initialized --> Starting: start() Called
    
    Starting --> Running: Agents Registered
    
    Running --> Processing: Message Received
    
    Processing --> Evaluating: Handle Message
    
    Evaluating --> Publishing: Decision Made
    
    Publishing --> Running: Message Sent
    
    Running --> Paused: Pause Signal
    Paused --> Running: Resume Signal
    
    Running --> Stopping: Shutdown Signal
    Stopping --> Stopped: Cleanup Complete
    
    Stopped --> [*]
    
    note right of Processing
        Agents can:
        - Query external APIs
        - Run ML inference
        - Access blockchain state
        - Update internal state
    end note
```

### Agent Responsibilities

#### 1. Orchestrator Agent
- **Purpose**: Central coordinator for all agents
- **Responsibilities**:
  - Receive swap requests from API
  - Coordinate agent execution flow
  - Aggregate results from multiple agents
  - Return final execution result
- **Technology**: Python AsyncIO, Message Bus

#### 2. Liquidity Scout Agent
- **Purpose**: Discover and monitor liquidity across DEXs
- **Responsibilities**:
  - Query MCP server for real-time prices
  - Query subgraphs for pool reserves
  - Cache liquidity data
  - Detect arbitrage opportunities
- **Data Sources**: MCP Client, The Graph Subgraphs

#### 3. Split Optimizer Agent
- **Purpose**: Calculate optimal route splits
- **Responsibilities**:
  - Receive liquidity data
  - Run ML slippage predictions
  - Solve optimization problem (linear programming)
  - Generate route splits with expected outputs
- **Technology**: scipy.optimize, ML Models

#### 4. Risk Validator Agent
- **Purpose**: Pre-execution risk assessment
- **Responsibilities**:
  - Evaluate route safety
  - Check slippage tolerance
  - Validate gas estimates
  - Flag high-risk transactions
- **Technology**: Rule Engine, ML Risk Models

#### 5. Execution Agent
- **Purpose**: Execute transactions via x402
- **Responsibilities**:
  - Prepare x402 operations
  - Sign transactions (if configured)
  - Submit to blockchain
  - Monitor execution status
- **Technology**: Web3.py, x402 SDK

---

## Smart Contracts

### Contract Architecture

```mermaid
graph TB
    subgraph "Router Contracts"
        CR[CrossDEXRouter.sol<br/>Main Entry Point]
        CL[CLECORouter.sol<br/>Legacy Router]
    end
    
    subgraph "Settlement Contracts"
        MS[MultiSend.sol<br/>Batch Transfers]
        IS[IntelligentSettlement.sol<br/>Settlement Logic]
        SP[SettlementPipeline.sol<br/>Multi-Stage Settlement]
    end
    
    subgraph "Payment Contracts"
        CP[CronosPaymentProcessor.sol<br/>Payment Processing]
        TR[Treasury.sol<br/>Treasury Management]
    end
    
    subgraph "DAO Contracts"
        HD[HackathonNFTDAO.sol<br/>Governance]
        GT[GovernanceToken.sol<br/>Voting Token]
        SD[SimpleDAO.sol<br/>Simple Governance]
    end
    
    subgraph "Utility Contracts"
        HS[HackathonNFT.sol<br/>NFT Collection]
    end
    
    CR --> MS
    CR --> IS
    CR --> SP
    IS --> CP
    CP --> TR
    HD --> GT
    HD --> SD
    
    style CR fill:#2196F3
    style IS fill:#4CAF50
    style CP fill:#FF9800
```

### CrossDEXRouter Contract

**Key Functions:**

```solidity
// Main execution function
function executeOptimizedSwap(
    RouteSplit[] calldata routes,
    address tokenIn,
    address tokenOut,
    uint256 totalAmountIn,
    uint256 minTotalOut,
    uint256 deadline
) external returns (uint256 totalOut);

// Internal x402 execution
function _executeRoutes(
    RouteSplit[] calldata routes,
    uint256 minTotalOut
) internal returns (uint256 totalOut);
```

**Features:**
- Atomic multi-DEX execution via x402
- Automatic slippage protection
- Gas optimization
- Reentrancy protection

### Contract Security Features

- ✅ **ReentrancyGuard**: Protection against reentrancy attacks
- ✅ **Access Control**: Role-based permissions
- ✅ **SafeMath**: Overflow protection (Solidity 0.8+ built-in)
- ✅ **Input Validation**: Comprehensive parameter checks
- ✅ **Event Logging**: Complete audit trail

---

## API Documentation

### Core Endpoints

#### Swap Execution

```http
POST /api/v2/swap
Content-Type: application/json

{
  "token_in": "0x5C7F8A570d578ED84E63fdFA7b1eE72dEae1AE23",
  "token_out": "0xc21223249CA28397B4B6541dfFaEcC539BfF0c59",
  "amount_in": "1000.0",
  "slippage_tolerance": 0.005,
  "user_address": "0x...",
  "strategy": "ai_optimized"
}
```

**Response:**
```json
{
  "success": true,
  "tx_hash": "0x...",
  "routes": [
    {
      "dex": "VVS Finance",
      "amount_in": "400.0",
      "expected_out": "398.5",
      "slippage": 0.003
    },
    {
      "dex": "CronaSwap",
      "amount_in": "600.0",
      "expected_out": "597.8",
      "slippage": 0.004
    }
  ],
  "total_expected_out": "996.3",
  "gas_estimate": "250000"
}
```

#### Route Optimization

```http
POST /api/optimize
Content-Type: application/json

{
  "token_in": "WCRO",
  "token_out": "USDC",
  "amount_in": "1000.0",
  "max_splits": 3
}
```

#### Liquidity Query

```http
GET /api/liquidity/{token_in}/{token_out}
```

#### HITL Payment Observation

```http
POST /api/hitl/payments/observe
Content-Type: application/json

{
  "txHash": "0x...",
  "chainId": 338,
  "payer": "0x...",
  "amountWei": "1000000000000000000",
  "tokenAddress": null
}
```

### WebSocket Events

**Connection:** `ws://localhost:8000/api/hitl/ws`

**Events:**
- `payment_flagged`: New payment flagged for review
- `payment_approved`: Payment approved by operator
- `payment_rejected`: Payment rejected
- `agent_update`: Agent status update
- `execution_status`: Swap execution status

---

## Deployment

### Docker Compose Deployment

```yaml
version: '3.8'

services:
  backend:
    build: ./cleo_project/backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgres://user:pass@db:5432/cleo
      - REDIS_URL=redis://redis:6379
      - CRONOS_RPC=https://evm-t3.cronos.org
    depends_on:
      - db
      - redis

  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
    depends_on:
      - backend

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=cleo
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    command: ["redis-server", "--appendonly", "yes"]
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

### Environment Variables

```bash
# Backend
DATABASE_URL=postgresql://user:pass@localhost:5432/cleo
REDIS_URL=redis://localhost:6379
CRONOS_RPC=https://evm-t3.cronos.org
X402_FACILITATOR_URL=https://facilitator.cronos.org
PRIVATE_KEY=0x...  # Optional, for server-signed txs
MCP_SERVER_URL=https://mcp-server.example.com

# Frontend
VITE_API_URL=http://localhost:8000
VITE_CHAIN_ID=338  # Cronos Testnet
VITE_ROUTER_ADDRESS=0x...
```

### Deployment Architecture

```mermaid
graph TB
    subgraph "Load Balancer"
        LB[Nginx<br/>SSL Termination]
    end
    
    subgraph "Application Layer"
        APP1[FastAPI Instance 1]
        APP2[FastAPI Instance 2]
        APP3[FastAPI Instance 3]
    end
    
    subgraph "Worker Layer"
        W1[BullMQ Worker 1]
        W2[BullMQ Worker 2]
        W3[ML Inference Worker]
    end
    
    subgraph "Data Layer"
        PG[(PostgreSQL<br/>Primary)]
        PG_REPLICA[(PostgreSQL<br/>Replica)]
        REDIS[(Redis<br/>Cluster)]
    end
    
    subgraph "Blockchain"
        CRONOS[Cronos RPC<br/>Load Balanced]
    end
    
    LB --> APP1
    LB --> APP2
    LB --> APP3
    
    APP1 --> PG
    APP2 --> PG
    APP3 --> PG
    PG --> PG_REPLICA
    
    APP1 --> REDIS
    APP2 --> REDIS
    APP3 --> REDIS
    
    W1 --> REDIS
    W2 --> REDIS
    W3 --> PG
    
    APP1 --> CRONOS
    APP2 --> CRONOS
    APP3 --> CRONOS
    
    style LB fill:#4CAF50
    style PG fill:#336791
    style REDIS fill:#DC382D
```

---

## Development

### Prerequisites

- **Node.js** >= 18
- **Python** >= 3.10
- **PostgreSQL** >= 15
- **Redis** >= 7
- **Hardhat** >= 2.0
- **Docker** (optional)

### Setup

#### Backend

```bash
cd cleo_project/backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Setup database
python -m hitl.migrations

# Run server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend

```bash
npm install
npm run dev
```

#### Smart Contracts

```bash
cd cleo_project/contracts
npm install
npx hardhat compile
npx hardhat test
npx hardhat run scripts/deploy.ts --network cronoTest
```

### Project Structure

```
cronos-cleo-main/
├── cleo_project/
│   ├── backend/
│   │   ├── agents/           # Multi-agent system
│   │   │   ├── agent_orchestrator.py
│   │   │   ├── execution_agent.py
│   │   │   ├── liquidity_scout.py
│   │   │   ├── risk_validator.py
│   │   │   └── message_bus.py
│   │   ├── ai/               # AI/ML models
│   │   │   ├── ai_agent.py
│   │   │   ├── ai_models.py
│   │   │   └── data_pipeline.py
│   │   ├── hitl/             # Human-in-the-loop
│   │   │   ├── api.py
│   │   │   ├── service.py
│   │   │   └── models.py
│   │   ├── multi_leg/        # Multi-leg transactions
│   │   ├── workflows/        # Workflow management
│   │   ├── main.py           # FastAPI app
│   │   ├── x402_executor.py
│   │   └── requirements.txt
│   ├── contracts/
│   │   ├── CrossDEXRouter.sol
│   │   ├── MultiSend.sol
│   │   ├── IntelligentSettlement.sol
│   │   └── test/
│   └── frontend/             # React frontend (in root)
├── src/                      # Frontend source
│   ├── components/
│   ├── pages/
│   ├── lib/
│   └── hooks/
├── package.json
└── README.md
```

### Testing

#### Backend Tests

```bash
cd cleo_project/backend
pytest tests/
```

#### Contract Tests

```bash
cd cleo_project/contracts
npx hardhat test
```

#### Integration Tests

```bash
# Start test environment
docker-compose -f docker-compose.test.yml up

# Run integration tests
pytest tests/integration/
```

---

## Security

### Security Features

1. **Key Management**
   - Never store private keys in code
   - Use environment variables or KMS
   - Support for hardware wallets (HSM)

2. **Access Control**
   - JWT-based authentication
   - Wallet signature verification
   - Role-based access control (RBAC)

3. **Input Validation**
   - Pydantic models for API validation
   - Contract parameter checks
   - Sanitization of user inputs

4. **Audit Logging**
   - Immutable audit trails
   - Complete transaction history
   - Operator action logging

5. **Rate Limiting**
   - API rate limits
   - Per-IP throttling
   - DDoS protection

### Security Best Practices

- ✅ Use multi-sig for contract ownership
- ✅ Regular security audits
- ✅ Bug bounty program (recommended)
- ✅ Monitoring and alerting
- ✅ Incident response plan

---

## Performance Metrics

### Key Performance Indicators (KPIs)

- **Transaction Success Rate**: > 99%
- **Average Execution Time**: < 5 seconds
- **Slippage Reduction**: 30-50% vs single-DEX
- **Gas Savings**: 15-25% through batching
- **HITL Review Time**: < 2 minutes (target)

### Monitoring

- **Prometheus** for metrics collection
- **Grafana** for visualization
- **AlertManager** for incident alerts
- **ELK Stack** for log aggregation

---

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Workflow

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## References

- [Cronos Documentation](https://docs.cronos.org/)
- [x402 Facilitator](https://docs.cronos.org/x402/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Wagmi Documentation](https://wagmi.sh/)

---

## Support

For support, please open an issue on GitHub or contact the maintainers.

---

<div align="center">

**Built with ❤️ for the Cronos ecosystem**

[Website](https://cleo.cronos.org) • [Documentation](https://docs.cleo.cronos.org) • [Discord](https://discord.gg/cleo)

</div>

