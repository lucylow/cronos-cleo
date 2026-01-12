# DAO Voting Frontend Setup Guide

This guide explains how to set up and use the Cronos DAO voting frontend that has been integrated into the C.L.E.O. project.

## Prerequisites

1. **Install Dependencies**
   ```bash
   npm install wagmi viem
   ```

2. **Deploy DAO Contract**
   - Deploy the `SimpleDAO` contract to Cronos (mainnet or testnet)
   - Note the deployed contract address
   - The contract is located at: `cleo_project/contracts/SimpleDAO.sol`

## Configuration

### Environment Variables

Create a `.env` file in the project root (or update existing `.env`) with your deployed DAO contract addresses:

```env
VITE_DAO_ADDRESS_TESTNET=0xYourDaoAddressOnTestnet
VITE_DAO_ADDRESS_MAINNET=0xYourDaoAddressOnMainnet
```

If these are not set, the app will default to `0x0000000000000000000000000000000000000000` and you'll need to update the constants file directly.

### Update Contract Addresses

Alternatively, you can directly edit `src/lib/daoConstants.ts`:

```typescript
export const DAO_ADDRESS_TESTNET = '0xYourDaoAddressOnTestnet';
export const DAO_ADDRESS_MAINNET = '0xYourDaoAddressOnMainnet';
```

## Features

### 1. Proposal List (`/dao`)
- View all proposals
- See proposal status (Active, Succeeded, Defeated, Executed)
- View vote counts (For, Against, Abstain)
- Click on any proposal to view details

### 2. Proposal Detail (`/dao/:id`)
- View full proposal information
- Vote on active proposals (For, Against, Abstain)
- Execute succeeded proposals
- Finalize proposals after voting period ends
- See if you've already voted

### 3. Create Proposal (`/dao/create`)
- Create new treasury ETH transfer proposals
- Specify recipient address and amount
- Add description for the proposal

## Navigation

The DAO governance section is accessible via:
- **Sidebar**: "DAO Governance" link (with Vote icon)
- **Top Nav Bar**: "Governance" link (in desktop view)
- **Direct URL**: `/dao`

## Wallet Connection

The DAO frontend uses wagmi for wallet connections. It supports:
- MetaMask
- Crypto.com DeFi Wallet
- Any standard EVM wallet

The app automatically detects and connects to Cronos mainnet (chain ID 25) or testnet (chain ID 338).

## Contract ABI

The DAO ABI is defined in `src/lib/daoAbi.ts` and includes:
- `nextProposalId()` - Get the next proposal ID
- `proposals(uint256)` - Get proposal details
- `getProposal(uint256)` - Get full proposal struct
- `vote(uint256, uint8)` - Vote on a proposal (0=Against, 1=For, 2=Abstain)
- `execute(uint256)` - Execute a succeeded proposal
- `finalizeProposal(uint256)` - Finalize a proposal after voting ends
- `proposeTreasuryETHTransfer(address, uint256, string)` - Create ETH transfer proposal
- `hasVoted(uint256, address)` - Check if address has voted

## Usage Flow

1. **Connect Wallet**: Click "Connect Wallet" button
2. **View Proposals**: Navigate to `/dao` to see all proposals
3. **Vote**: Click on a proposal, then click "Vote For/Against/Abstain"
4. **Create Proposal**: Click "New Proposal" button, fill in details, and submit
5. **Execute**: After a proposal succeeds and voting period ends, click "Execute Proposal"

## Troubleshooting

### "Contract not found" errors
- Ensure the DAO contract address is correctly set in environment variables or constants
- Verify the contract is deployed on the network you're connected to

### "Insufficient voting power" errors
- You need to hold governance tokens to vote or create proposals
- Check your token balance using the governance token contract

### Transaction failures
- Ensure you have enough CRO for gas fees
- Check that the proposal is in the correct state (e.g., Active for voting, Succeeded for execution)
- Verify you haven't already voted on the proposal

## Integration with Existing CLEO UI

The DAO frontend uses the same design system as the rest of the CLEO app:
- Tailwind CSS styling
- shadcn/ui components
- Consistent color scheme and gradients
- Responsive design for mobile and desktop

## Next Steps

1. Deploy the SimpleDAO contract to Cronos
2. Set the contract addresses in environment variables
3. Mint governance tokens to bootstrap the DAO
4. Start creating and voting on proposals!
