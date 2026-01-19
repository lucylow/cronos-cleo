import React, { useState, useEffect } from "react";
import { ethers, Contract } from "ethers";
import { useWallet } from "../wallet/WalletProvider";
import { verifyPayment } from "../lib/api";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import { Alert, AlertDescription } from "./ui/alert";
import { Badge } from "./ui/badge";
import { Loader2, CheckCircle2, XCircle, Wallet, History, Zap, Copy, ExternalLink, Plus, X, Layers } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { toast } from "sonner";

// Payment contract ABI (enhanced)
const PAYMENT_ABI = [
  "function payNative() external payable returns (uint256)",
  "function payWithERC20(address token, uint256 amount) external returns (uint256)",
  "function payments(uint256) view returns (address payer, address token, uint256 amount, uint256 timestamp)",
  "function getNativeBalance() external view returns (uint256)",
  "function getTokenBalance(address token) external view returns (uint256)",
  "function paused() external view returns (bool)",
  "event PaymentReceived(uint256 indexed paymentId, address indexed payer, address token, uint256 amount, uint256 timestamp)",
] as const;

// x402 Facilitator ABI for atomic batch payments
const X402_FACILITATOR_ABI = [
  "function executeConditionalBatch(tuple(address target, uint256 value, bytes data)[] operations, bytes condition, uint256 deadline) external payable",
  "event BatchExecuted(bytes32 indexed batchId, uint256 operationsCount)",
] as const;

// MultiSend ABI for batch transfers
const MULTI_SEND_ABI = [
  "function batchTransfer(tuple(address token, address recipient, uint256 amount)[] transfers, uint256 deadline) external payable",
] as const;

// Standard ERC20 ABI
const ERC20_ABI = [
  "function approve(address spender, uint256 amount) external returns (bool)",
  "function allowance(address owner, address spender) external view returns (uint256)",
  "function decimals() external view returns (uint8)",
  "function balanceOf(address account) external view returns (uint256)",
  "function symbol() external view returns (string)",
  "function name() external view returns (string)",
] as const;

// Popular Cronos tokens (mainnet and testnet)
const POPULAR_TOKENS = {
  mainnet: {
    "USDC": "0xc21223249CA28397B4B6541dfFaEcC539BfF0c59",
    "USDT": "0x66e428c3f67a68878562e79A0234c1F83c208770",
    "ETH": "0xe44Fd7fC8652Dc6F2eE8C3C09B3eD65b3e7D33c4",
    "WBTC": "0x062E66477Faf219F25D27dCED647BF57C3107d52",
  },
  testnet: {
    "USDC": "0x0Ab9dF7118c41b3fB5f3B80633DA9b0a09Cb2Ae0",
    "USDT": "0x0Ab9dF7118c41b3fB5f3B80633DA9b0a09Cb2Ae0",
  }
};

// Get contract address from environment
const getPaymentContractAddress = (): string => {
  const envAddr = import.meta.env.VITE_PAYMENT_CONTRACT_ADDRESS;
  if (envAddr) return envAddr;
  
  // Fallback for development
  console.warn("VITE_PAYMENT_CONTRACT_ADDRESS not set in .env");
  return ""; // User will need to set this
};

const CRONOS_TESTNET = {
  chainId: 338,
  chainIdHex: "0x152",
  chainName: "Cronos Testnet",
  rpcUrls: ["https://evm-t3.cronos.org"],
  nativeCurrency: { name: "CRO", symbol: "TCRO", decimals: 18 },
  blockExplorerUrls: ["https://testnet.cronoscan.com/"],
};

const CRONOS_MAINNET = {
  chainId: 25,
  chainIdHex: "0x19",
  chainName: "Cronos Mainnet",
  rpcUrls: ["https://evm.cronos.org"],
  nativeCurrency: { name: "CRO", symbol: "CRO", decimals: 18 },
  blockExplorerUrls: ["https://cronoscan.com/"],
};

interface PaymentHistory {
  id: number;
  txHash: string;
  amount: string;
  token: string;
  timestamp: number;
  status: "success" | "failed";
}

interface PaymentTemplate {
  name: string;
  amount: string;
  recipient: string;
  tokenAddress?: string;
}

interface BatchPaymentItem {
  id: string;
  recipient: string;
  amount: string;
  tokenAddress?: string;
  tokenType: "native" | "erc20";
}

// Get x402 facilitator address from environment
const getX402FacilitatorAddress = (): string => {
  const envAddr = import.meta.env.VITE_X402_FACILITATOR_ADDRESS;
  if (envAddr) return envAddr;
  return ""; // Will need to be set by user
};

export default function PaymentProcessor() {
  const { provider, signer, account, chainId, balance, connect } = useWallet();
  const [paymentContractAddress, setPaymentContractAddress] = useState(getPaymentContractAddress());
  const [amount, setAmount] = useState("");
  const [tokenAddress, setTokenAddress] = useState("");
  const [tokenDecimals, setTokenDecimals] = useState<number>(18);
  const [tokenSymbol, setTokenSymbol] = useState<string>("");
  const [tokenName, setTokenName] = useState<string>("");
  const [tokenBalance, setTokenBalance] = useState<string>("");
  const [croBalance, setCroBalance] = useState<string>("");
  const [contractBalance, setContractBalance] = useState<string>("");
  const [isContractPaused, setIsContractPaused] = useState<boolean>(false);
  const [loading, setLoading] = useState(false);
  const [loadingBalance, setLoadingBalance] = useState(false);
  const [status, setStatus] = useState<{ type: "success" | "error" | "info"; message: string } | null>(null);
  const [txHash, setTxHash] = useState<string | null>(null);
  const [paymentId, setPaymentId] = useState<number | null>(null);
  
  // Enhanced features
  const [gasEstimate, setGasEstimate] = useState<string | null>(null);
  const [paymentHistory, setPaymentHistory] = useState<PaymentHistory[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [templates, setTemplates] = useState<PaymentTemplate[]>([]);
  
  // Batch payment features
  const [x402FacilitatorAddress, setX402FacilitatorAddress] = useState(getX402FacilitatorAddress());
  const [batchPayments, setBatchPayments] = useState<BatchPaymentItem[]>([]);
  const [batchLoading, setBatchLoading] = useState(false);

  useEffect(() => {
    // Auto-fetch token info when token address is entered
    if (tokenAddress && signer && tokenAddress.startsWith("0x") && tokenAddress.length === 42) {
      fetchTokenInfo(tokenAddress);
    } else {
      setTokenSymbol("");
      setTokenName("");
      setTokenDecimals(18);
      setTokenBalance("");
    }
  }, [tokenAddress, signer]);

  useEffect(() => {
    // Fetch balances when account or chain changes
    if (account && signer) {
      fetchBalances();
    }
  }, [account, signer, chainId, tokenAddress]);

  // Check contract status periodically
  useEffect(() => {
    if (paymentContractAddress && signer) {
      checkContractStatus();
      const interval = setInterval(checkContractStatus, 30000); // Check every 30s
      return () => clearInterval(interval);
    }
  }, [paymentContractAddress, signer]);

  useEffect(() => {
    // Load payment history from localStorage
    const stored = localStorage.getItem("paymentHistory");
    if (stored) {
      try {
        setPaymentHistory(JSON.parse(stored));
      } catch (e) {
        console.error("Failed to load payment history:", e);
      }
    }

    // Load templates from localStorage
    const storedTemplates = localStorage.getItem("paymentTemplates");
    if (storedTemplates) {
      try {
        setTemplates(JSON.parse(storedTemplates));
      } catch (e) {
        console.error("Failed to load templates:", e);
      }
    }
  }, []);

  useEffect(() => {
    // Fetch balances when account or signer changes
    if (account && signer && provider) {
      fetchBalances();
    }
  }, [account, signer, provider, tokenAddress]);

  useEffect(() => {
    // Estimate gas when amount or contract changes
    if (amount && paymentContractAddress && signer && account) {
      estimateGas();
    } else {
      setGasEstimate(null);
    }
  }, [amount, paymentContractAddress, signer, account, tokenAddress]);

  const fetchTokenInfo = async (address: string) => {
    if (!signer) return;
    try {
      const tokenContract = new Contract(address, ERC20_ABI, signer);
      const [decimals, symbol, name] = await Promise.all([
        tokenContract.decimals().catch(() => 18),
        tokenContract.symbol().catch(() => ""),
        tokenContract.name().catch(() => ""),
      ]);
      setTokenDecimals(Number(decimals));
      setTokenSymbol(symbol || "");
      setTokenName(name || "");
    } catch (error) {
      console.error("Error fetching token info:", error);
      setTokenSymbol("");
      setTokenName("");
      setTokenDecimals(18);
    }
  };

  const fetchBalances = async () => {
    if (!signer || !account) return;
    setLoadingBalance(true);
    try {
      // Fetch native CRO balance
      const croBal = await provider?.getBalance(account);
      if (croBal) {
        setCroBalance(ethers.formatEther(croBal));
      }

      // Fetch token balance if token is selected
      if (tokenAddress && tokenAddress.startsWith("0x") && tokenAddress.length === 42) {
        try {
          const tokenContract = new Contract(tokenAddress, ERC20_ABI, signer);
          const bal = await tokenContract.balanceOf(account);
          setTokenBalance(ethers.formatUnits(bal, tokenDecimals));
        } catch (error) {
          console.error("Error fetching token balance:", error);
          setTokenBalance("");
        }
      } else {
        setTokenBalance("");
      }

      // Fetch contract balance if contract address is set
      if (paymentContractAddress && paymentContractAddress.startsWith("0x")) {
        try {
          const paymentContract = new Contract(paymentContractAddress, PAYMENT_ABI, signer);
          const contractBal = await paymentContract.getNativeBalance();
          setContractBalance(ethers.formatEther(contractBal));
        } catch (error) {
          console.error("Error fetching contract balance:", error);
        }
      }
    } catch (error) {
      console.error("Error fetching balances:", error);
    } finally {
      setLoadingBalance(false);
    }
  };

  const checkContractStatus = async () => {
    if (!signer || !paymentContractAddress) return;
    try {
      const paymentContract = new Contract(paymentContractAddress, PAYMENT_ABI, signer);
      const paused = await paymentContract.paused().catch(() => false);
      setIsContractPaused(paused);
    } catch (error) {
      console.error("Error checking contract status:", error);
    }
  };

  const fetchBalances = async () => {
    if (!signer || !account || !provider) return;
    try {
      // Fetch native balance
      const nativeBalance = await provider.getBalance(account);
      setBalance(ethers.formatEther(nativeBalance));

      // Fetch token balance if token address is set
      if (tokenAddress && tokenAddress.startsWith("0x") && tokenAddress.length === 42) {
        try {
          const tokenContract = new Contract(tokenAddress, ERC20_ABI, signer);
          const balance = await tokenContract.balanceOf(account);
          setTokenBalance(ethers.formatUnits(balance, tokenDecimals));
        } catch (error) {
          console.error("Error fetching token balance:", error);
          setTokenBalance(null);
        }
      } else {
        setTokenBalance(null);
      }
    } catch (error) {
      console.error("Error fetching balances:", error);
    }
  };

  const estimateGas = async () => {
    if (!signer || !account || !amount || !paymentContractAddress) return;
    try {
      const paymentContract = new Contract(paymentContractAddress, PAYMENT_ABI, signer);
      if (tokenAddress) {
        // ERC20 payment gas estimate
        const amountWei = ethers.parseUnits(amount, tokenDecimals);
        const gasEstimate = await paymentContract.payWithERC20.estimateGas(tokenAddress, amountWei);
        const gasPrice = await provider.getFeeData();
        const gasCost = gasEstimate * (gasPrice.gasPrice || 0n);
        setGasEstimate(ethers.formatEther(gasCost));
      } else {
        // Native payment gas estimate
        const amountWei = ethers.parseUnits(amount, 18);
        const gasEstimate = await paymentContract.payNative.estimateGas({ value: amountWei });
        const gasPrice = await provider.getFeeData();
        const gasCost = gasEstimate * (gasPrice.gasPrice || 0n);
        setGasEstimate(ethers.formatEther(gasCost));
      }
    } catch (error) {
      console.error("Error estimating gas:", error);
      setGasEstimate(null);
    }
  };

  const addToHistory = (payment: PaymentHistory) => {
    const newHistory = [payment, ...paymentHistory].slice(0, 50); // Keep last 50
    setPaymentHistory(newHistory);
    localStorage.setItem("paymentHistory", JSON.stringify(newHistory));
  };

  const saveTemplate = () => {
    if (!amount || !paymentContractAddress) {
      toast.error("Please enter amount and recipient address");
      return;
    }
    const template: PaymentTemplate = {
      name: `Payment ${templates.length + 1}`,
      amount,
      recipient: paymentContractAddress,
      tokenAddress: tokenAddress || undefined,
    };
    const newTemplates = [...templates, template];
    setTemplates(newTemplates);
    localStorage.setItem("paymentTemplates", JSON.stringify(newTemplates));
    toast.success("Template saved!");
  };

  const loadTemplate = (template: PaymentTemplate) => {
    setAmount(template.amount);
    setPaymentContractAddress(template.recipient);
    if (template.tokenAddress) {
      setTokenAddress(template.tokenAddress);
    }
    toast.info("Template loaded");
  };

  const ensureCronosNetwork = async () => {
    if (!(window as any).ethereum) {
      throw new Error("No wallet found");
    }

    const targetNetwork = chainId === BigInt(25) ? CRONOS_MAINNET : CRONOS_TESTNET;

    try {
      await (window as any).ethereum.request({
        method: "wallet_switchEthereumChain",
        params: [{ chainId: targetNetwork.chainIdHex }],
      });
    } catch (switchError: any) {
      if (switchError?.code === 4902) {
        // Chain doesn't exist, add it
        await (window as any).ethereum.request({
          method: "wallet_addEthereumChain",
          params: [targetNetwork],
        });
      } else {
        throw switchError;
      }
    }
  };

  const payNative = async () => {
    if (!signer || !paymentContractAddress) {
      setStatus({ type: "error", message: "Connect wallet and set contract address" });
      toast.error("Connect wallet and set contract address");
      return;
    }

    if (!amount || parseFloat(amount) <= 0) {
      setStatus({ type: "error", message: "Enter a valid amount" });
      toast.error("Enter a valid amount");
      return;
    }

    // Check balance before payment
    if (balance) {
      const amountWei = ethers.parseUnits(amount, 18);
      const balanceWei = ethers.parseEther(balance);
      const estimatedGas = gasEstimate ? ethers.parseEther(gasEstimate) : ethers.parseUnits("0.01", 18);
      
      if (balanceWei < amountWei + estimatedGas) {
        setStatus({ type: "error", message: "Insufficient balance (including gas)" });
        toast.error("Insufficient balance (including gas)");
        return;
      }
    }

    setLoading(true);
    setStatus(null);
    setTxHash(null);
    setPaymentId(null);

    try {
      await ensureCronosNetwork();

      const paymentContract = new Contract(paymentContractAddress, PAYMENT_ABI, signer);
      const amountWei = ethers.parseUnits(amount, 18); // CRO uses 18 decimals

      const tx = await paymentContract.payNative({
        value: amountWei,
        gasLimit: 200_000,
      });

      setStatus({ type: "info", message: `Transaction sent: ${tx.hash}` });
      setTxHash(tx.hash);
      toast.info(`Transaction sent: ${tx.hash.slice(0, 10)}...`);

      const receipt = await tx.wait();
      console.log("Payment receipt:", receipt);

      // Parse PaymentReceived event
      const event = receipt.logs
        .map((log: any) => {
          try {
            return paymentContract.interface.parseLog(log);
          } catch {
            return null;
          }
        })
        .find((parsed: any) => parsed?.name === "PaymentReceived");

      if (event) {
        const id = Number(event.args.paymentId);
        setPaymentId(id);
        setStatus({
          type: "success",
          message: `Payment successful! Payment ID: ${id}`,
        });
        
        toast.success(`Payment successful! Payment ID: ${id}`);

        // Add to history
        addToHistory({
          id,
          txHash: tx.hash,
          amount,
          token: "CRO",
          timestamp: Date.now(),
          status: "success",
        });

        // Refresh balances
        await fetchBalances();

        // Verify payment on backend
        try {
          const verifyResult = await verifyPayment({
            tx_hash: tx.hash,
            expected_recipient: paymentContractAddress,
            min_amount_wei: amountWei.toString(),
          });
          if (verifyResult.ok) {
            console.log("Payment verified:", verifyResult.result);
            toast.success("Payment verified on backend");
          }
        } catch (error) {
          console.error("Backend verification failed:", error);
        }
      }
    } catch (error: any) {
      console.error("Payment error:", error);
      const errorMessage = error.message || "Payment failed";
      setStatus({
        type: "error",
        message: errorMessage,
      });
      toast.error(errorMessage);
      
      // Add failed payment to history
      if (txHash) {
        addToHistory({
          id: paymentId || 0,
          txHash,
          amount,
          token: "CRO",
          timestamp: Date.now(),
          status: "failed",
        });
      }
    } finally {
      setLoading(false);
    }
  };

  const payERC20 = async () => {
    if (!signer || !paymentContractAddress) {
      setStatus({ type: "error", message: "Connect wallet and set contract address" });
      toast.error("Connect wallet and set contract address");
      return;
    }

    if (!tokenAddress || !tokenAddress.startsWith("0x")) {
      setStatus({ type: "error", message: "Enter a valid ERC-20 token address" });
      toast.error("Enter a valid ERC-20 token address");
      return;
    }

    if (!amount || parseFloat(amount) <= 0) {
      setStatus({ type: "error", message: "Enter a valid amount" });
      toast.error("Enter a valid amount");
      return;
    }

    // Check token balance before payment
    if (tokenBalance) {
      const balanceNum = parseFloat(tokenBalance);
      const amountNum = parseFloat(amount);
      if (balanceNum < amountNum) {
        setStatus({ type: "error", message: `Insufficient token balance. Available: ${tokenBalance} ${tokenSymbol}` });
        toast.error(`Insufficient token balance. Available: ${tokenBalance} ${tokenSymbol}`);
        return;
      }
    }

    // Check native balance for gas
    if (balance) {
      const balanceWei = ethers.parseEther(balance);
      const estimatedGas = gasEstimate ? ethers.parseEther(gasEstimate) : ethers.parseUnits("0.01", 18);
      if (balanceWei < estimatedGas) {
        setStatus({ type: "error", message: "Insufficient CRO for gas fees" });
        toast.error("Insufficient CRO for gas fees");
        return;
      }
    }

    setLoading(true);
    setStatus(null);
    setTxHash(null);
    setPaymentId(null);

    try {
      await ensureCronosNetwork();

      const tokenContract = new Contract(tokenAddress, ERC20_ABI, signer);
      const paymentContract = new Contract(paymentContractAddress, PAYMENT_ABI, signer);

      const amountWei = ethers.parseUnits(amount, tokenDecimals);

      // Check and approve
      const allowance = await tokenContract.allowance(account, paymentContractAddress);
      if (allowance < amountWei) {
        setStatus({ type: "info", message: "Approving token spend..." });
        toast.info("Approving token spend...");
        const approveTx = await tokenContract.approve(paymentContractAddress, amountWei);
        await approveTx.wait();
        toast.success("Token approved");
      }

      // Make payment
      setStatus({ type: "info", message: "Processing payment..." });
      toast.info("Processing payment...");
      const tx = await paymentContract.payWithERC20(tokenAddress, amountWei, {
        gasLimit: 200_000,
      });

      setStatus({ type: "info", message: `Transaction sent: ${tx.hash}` });
      setTxHash(tx.hash);
      toast.info(`Transaction sent: ${tx.hash.slice(0, 10)}...`);

      const receipt = await tx.wait();
      console.log("Payment receipt:", receipt);

      // Parse PaymentReceived event
      const event = receipt.logs
        .map((log: any) => {
          try {
            return paymentContract.interface.parseLog(log);
          } catch {
            return null;
          }
        })
        .find((parsed: any) => parsed?.name === "PaymentReceived");

      if (event) {
        const id = Number(event.args.paymentId);
        setPaymentId(id);
        setStatus({
          type: "success",
          message: `Payment successful! Payment ID: ${id}`,
        });
        
        toast.success(`Payment successful! Payment ID: ${id}`);

        // Add to history
        addToHistory({
          id,
          txHash: tx.hash,
          amount,
          token: tokenSymbol || "ERC20",
          timestamp: Date.now(),
          status: "success",
        });

        // Refresh balances
        await fetchBalances();

        // Verify payment on backend
        try {
          const verifyResult = await verifyPayment({
            tx_hash: tx.hash,
            token_address: tokenAddress,
            expected_recipient: paymentContractAddress,
            min_amount_wei: amountWei.toString(),
          });
          if (verifyResult.ok) {
            console.log("Payment verified:", verifyResult.result);
            toast.success("Payment verified on backend");
          }
        } catch (error) {
          console.error("Backend verification failed:", error);
        }
      }
    } catch (error: any) {
      console.error("Payment error:", error);
      const errorMessage = error.message || "Payment failed";
      setStatus({
        type: "error",
        message: errorMessage,
      });
      toast.error(errorMessage);
      
      // Add failed payment to history
      if (txHash) {
        addToHistory({
          id: paymentId || 0,
          txHash,
          amount,
          token: tokenSymbol || "ERC20",
          timestamp: Date.now(),
          status: "failed",
        });
      }
    } finally {
      setLoading(false);
    }
  };

  const explorerUrl = () => {
    if (!txHash) return null;
    const isMainnet = chainId === BigInt(25);
    const baseUrl = isMainnet ? "https://cronoscan.com/tx/" : "https://testnet.cronoscan.com/tx/";
    return baseUrl + txHash;
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success("Copied to clipboard");
  };

  const executeBatchPayment = async () => {
    if (!signer || !x402FacilitatorAddress || batchPayments.length === 0) {
      toast.error("Missing required information for batch payment");
      return;
    }

    // Validate all payments
    for (const payment of batchPayments) {
      if (!payment.recipient || !payment.amount) {
        toast.error(`Payment ${batchPayments.indexOf(payment) + 1} is incomplete`);
        return;
      }
      if (payment.tokenType === "erc20" && !payment.tokenAddress) {
        toast.error(`Payment ${batchPayments.indexOf(payment) + 1} missing token address`);
        return;
      }
    }

    setBatchLoading(true);
    setStatus(null);
    setTxHash(null);

    try {
      await ensureCronosNetwork();

      const facilitator = new Contract(x402FacilitatorAddress, X402_FACILITATOR_ABI, signer);

      // Build operations for x402 batch
      const operations: Array<{ target: string; value: bigint; data: string }> = [];
      let totalNativeValue = 0n;

      for (const payment of batchPayments) {
        const amountWei = payment.tokenType === "native"
          ? ethers.parseEther(payment.amount)
          : ethers.parseUnits(payment.amount, 18); // Assuming 18 decimals for ERC20

        if (payment.tokenType === "native") {
          // Native CRO transfer
          totalNativeValue += amountWei;
          operations.push({
            target: payment.recipient,
            value: amountWei,
            data: "0x",
          });
        } else if (payment.tokenAddress) {
          // ERC20 transfer
          const tokenContract = new Contract(payment.tokenAddress, ERC20_ABI, signer);
          
          // Check and approve if needed
          const allowance = await tokenContract.allowance(account, x402FacilitatorAddress);
          if (allowance < amountWei) {
            setStatus({ type: "info", message: `Approving token ${payment.tokenAddress}...` });
            toast.info("Approving tokens...");
            const approveTx = await tokenContract.approve(x402FacilitatorAddress, amountWei);
            await approveTx.wait();
          }

          // Encode transfer function call
          const transferData = tokenContract.interface.encodeFunctionData("transfer", [
            payment.recipient,
            amountWei,
          ]);

          operations.push({
            target: payment.tokenAddress,
            value: 0n,
            data: transferData,
          });
        }
      }

      if (operations.length === 0) {
        throw new Error("No valid operations to execute");
      }

      // Set deadline (30 minutes from now)
      const deadline = Math.floor(Date.now() / 1000) + 1800;
      const condition = "0x"; // No condition - all or nothing execution

      setStatus({ type: "info", message: "Executing x402 batch..." });
      toast.info(`Executing ${operations.length} payments atomically...`);

      // Execute batch via x402 facilitator
      const tx = await facilitator.executeConditionalBatch(
        operations.map((op) => ({
          target: op.target,
          value: op.value,
          data: op.data,
        })),
        condition,
        deadline,
        {
          value: totalNativeValue,
          gasLimit: 1_500_000n, // Higher gas limit for batch operations
        }
      );

      setStatus({ type: "info", message: `Transaction sent: ${tx.hash}` });
      setTxHash(tx.hash);
      toast.info(`Batch transaction sent: ${tx.hash.slice(0, 10)}...`);

      const receipt = await tx.wait();
      console.log("Batch payment receipt:", receipt);

      if (receipt.status === 1) {
        setStatus({
          type: "success",
          message: `Batch payment successful! ${operations.length} payments executed atomically.`,
        });
        toast.success(`Batch payment successful! ${operations.length} payments executed.`);

        // Add to history
        batchPayments.forEach((payment, idx) => {
          addToHistory({
            id: Date.now() + idx,
            txHash: tx.hash,
            amount: payment.amount,
            token: payment.tokenType === "native" ? "CRO" : payment.tokenAddress || "ERC20",
            timestamp: Date.now(),
            status: "success",
          });
        });

        // Clear batch payments
        setBatchPayments([]);

        // Refresh balances
        await fetchBalances();
      } else {
        throw new Error("Transaction failed");
      }
    } catch (error: any) {
      console.error("Batch payment error:", error);
      const errorMessage = error.message || "Batch payment failed";
      setStatus({
        type: "error",
        message: errorMessage,
      });
      toast.error(errorMessage);

      // Add failed batch to history
      if (txHash) {
        batchPayments.forEach((payment, idx) => {
          addToHistory({
            id: Date.now() + idx,
            txHash,
            amount: payment.amount,
            token: payment.tokenType === "native" ? "CRO" : payment.tokenAddress || "ERC20",
            timestamp: Date.now(),
            status: "failed",
          });
        });
      }
    } finally {
      setBatchLoading(false);
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Cronos Payment Processor</CardTitle>
              <CardDescription>
                Accept payments in native CRO or ERC-20 tokens on Cronos
              </CardDescription>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowHistory(!showHistory)}
              >
                <History className="h-4 w-4 mr-2" />
                History ({paymentHistory.length})
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {!account ? (
            <div className="text-center py-8">
              <p className="text-muted-foreground mb-4">Connect your wallet to make payments</p>
              <Button onClick={connect}>Connect Wallet</Button>
            </div>
          ) : (
            <>
              {/* Balance Display */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                <Card>
                  <CardContent className="pt-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Wallet className="h-4 w-4 text-muted-foreground" />
                        <span className="text-sm font-medium">Native Balance</span>
                      </div>
                      <Badge variant="outline">
                        {balance ? `${parseFloat(balance).toFixed(4)} CRO` : "Loading..."}
                      </Badge>
                    </div>
                    {gasEstimate && (
                      <div className="mt-2 text-xs text-muted-foreground flex items-center gap-1">
                        <Zap className="h-3 w-3" />
                        Est. Gas: ~{parseFloat(gasEstimate).toFixed(6)} CRO
                      </div>
                    )}
                  </CardContent>
                </Card>
                {tokenBalance && tokenAddress && (
                  <Card>
                    <CardContent className="pt-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Wallet className="h-4 w-4 text-muted-foreground" />
                          <span className="text-sm font-medium">Token Balance</span>
                        </div>
                        <Badge variant="outline">
                          {parseFloat(tokenBalance).toFixed(4)} {tokenSymbol}
                        </Badge>
                      </div>
                    </CardContent>
                  </Card>
                )}
              </div>

              {/* Payment Templates */}
              {templates.length > 0 && (
                <div className="mb-4">
                  <label className="text-sm font-medium mb-2 block">Quick Templates</label>
                  <div className="flex flex-wrap gap-2">
                    {templates.map((template, idx) => (
                      <Button
                        key={idx}
                        variant="outline"
                        size="sm"
                        onClick={() => loadTemplate(template)}
                      >
                        {template.name}
                      </Button>
                    ))}
                  </div>
                </div>
              )}

              <div className="mb-4">
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium">Contract Address</label>
                  <div className="flex gap-2">
                    {paymentContractAddress && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => copyToClipboard(paymentContractAddress)}
                      >
                        <Copy className="h-3 w-3" />
                      </Button>
                    )}
                    {templates.length > 0 && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={saveTemplate}
                        disabled={!amount || !paymentContractAddress}
                      >
                        Save Template
                      </Button>
                    )}
                  </div>
                </div>
                <Input
                  value={paymentContractAddress}
                  onChange={(e) => setPaymentContractAddress(e.target.value)}
                  placeholder="0x..."
                  className="font-mono text-sm"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Set VITE_PAYMENT_CONTRACT_ADDRESS in .env or enter manually
                </p>
              </div>

              <Tabs defaultValue="native" className="w-full">
                <TabsList className="grid w-full grid-cols-3">
                  <TabsTrigger value="native">Native CRO</TabsTrigger>
                  <TabsTrigger value="erc20">ERC-20 Token</TabsTrigger>
                  <TabsTrigger value="batch">x402 Batch</TabsTrigger>
                </TabsList>

                <TabsContent value="native" className="space-y-4 mt-4">
                  <div>
                    <label className="text-sm font-medium mb-2 block">Amount (CRO)</label>
                    <Input
                      type="number"
                      step="0.0001"
                      value={amount}
                      onChange={(e) => setAmount(e.target.value)}
                      placeholder="0.1"
                    />
                    {balance && amount && (
                      <p className="text-xs text-muted-foreground mt-1">
                        Available: {balance} CRO
                        {parseFloat(amount) > parseFloat(balance) && (
                          <span className="text-red-500 ml-2">Insufficient balance</span>
                        )}
                      </p>
                    )}
                  </div>
                  <Button
                    onClick={payNative}
                    disabled={loading || !amount || !paymentContractAddress}
                    className="w-full"
                  >
                    {loading ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Processing...
                      </>
                    ) : (
                      "Pay with CRO"
                    )}
                  </Button>
                </TabsContent>

              <TabsContent value="erc20" className="space-y-4 mt-4">
                {/* Popular tokens quick select */}
                <div>
                  <label className="text-sm font-medium mb-2 block">Quick Select (Popular Tokens)</label>
                  <div className="flex flex-wrap gap-2 mb-2">
                    {Object.entries(chainId === BigInt(25) ? POPULAR_TOKENS.mainnet : POPULAR_TOKENS.testnet).map(([symbol, address]) => (
                      <Button
                        key={symbol}
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setTokenAddress(address);
                          fetchTokenInfo(address);
                        }}
                        className="text-xs"
                      >
                        {symbol}
                      </Button>
                    ))}
                  </div>
                </div>
                
                <div>
                  <label className="text-sm font-medium mb-2 block">Token Address</label>
                  <Input
                    value={tokenAddress}
                    onChange={(e) => setTokenAddress(e.target.value)}
                    placeholder="0x..."
                    className="font-mono text-sm"
                  />
                  {tokenSymbol && (
                    <div className="mt-1 space-y-0.5">
                      <p className="text-xs text-muted-foreground">
                        Token: <span className="font-semibold">{tokenSymbol}</span>
                        {tokenName && ` (${tokenName})`}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        Decimals: {tokenDecimals}
                      </p>
                      {tokenBalance && (
                        <p className="text-xs text-muted-foreground">
                          Balance: <span className="font-semibold">{parseFloat(tokenBalance).toFixed(4)} {tokenSymbol}</span>
                        </p>
                      )}
                    </div>
                  )}
                </div>
                  <div>
                    <label className="text-sm font-medium mb-2 block">Amount</label>
                    <Input
                      type="number"
                      step="0.0001"
                      value={amount}
                      onChange={(e) => setAmount(e.target.value)}
                      placeholder="10"
                    />
                    {tokenBalance && amount && (
                      <p className="text-xs text-muted-foreground mt-1">
                        Available: {tokenBalance} {tokenSymbol}
                        {parseFloat(amount) > parseFloat(tokenBalance) && (
                          <span className="text-red-500 ml-2">Insufficient balance</span>
                        )}
                      </p>
                    )}
                  </div>
                  <Button
                    onClick={payERC20}
                    disabled={loading || !amount || !tokenAddress || !paymentContractAddress}
                    className="w-full"
                  >
                    {loading ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Processing...
                      </>
                    ) : (
                      `Pay with ${tokenSymbol || "ERC-20"}`
                    )}
                  </Button>
                </TabsContent>

                <TabsContent value="batch" className="space-y-4 mt-4">
                  <Alert className="border-primary/50 bg-primary/5">
                    <Layers className="h-4 w-4 text-primary" />
                    <AlertDescription>
                      Execute multiple payments atomically via x402 facilitator. All payments succeed or all revert.
                    </AlertDescription>
                  </Alert>

                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-sm font-medium">x402 Facilitator Address</label>
                      {x402FacilitatorAddress && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => copyToClipboard(x402FacilitatorAddress)}
                        >
                          <Copy className="h-3 w-3" />
                        </Button>
                      )}
                    </div>
                    <Input
                      value={x402FacilitatorAddress}
                      onChange={(e) => setX402FacilitatorAddress(e.target.value)}
                      placeholder="0x..."
                      className="font-mono text-sm"
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      Set VITE_X402_FACILITATOR_ADDRESS in .env or enter manually
                    </p>
                  </div>

                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <label className="text-sm font-medium">Batch Payments</label>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          const newPayment: BatchPaymentItem = {
                            id: Date.now().toString(),
                            recipient: "",
                            amount: "",
                            tokenType: "native",
                          };
                          setBatchPayments([...batchPayments, newPayment]);
                        }}
                      >
                        <Plus className="h-4 w-4 mr-2" />
                        Add Payment
                      </Button>
                    </div>

                    {batchPayments.length === 0 ? (
                      <div className="text-center py-8 border rounded-lg bg-muted/30">
                        <p className="text-sm text-muted-foreground mb-2">No batch payments added</p>
                        <p className="text-xs text-muted-foreground">Click "Add Payment" to create a batch</p>
                      </div>
                    ) : (
                      <div className="space-y-2 max-h-[300px] overflow-y-auto">
                        {batchPayments.map((payment, idx) => (
                          <Card key={payment.id} className="p-3">
                            <div className="space-y-2">
                              <div className="flex items-center justify-between">
                                <Badge variant="outline">Payment {idx + 1}</Badge>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => {
                                    setBatchPayments(batchPayments.filter((p) => p.id !== payment.id));
                                  }}
                                >
                                  <X className="h-4 w-4 text-destructive" />
                                </Button>
                              </div>

                              <div className="grid grid-cols-2 gap-2">
                                <div>
                                  <label className="text-xs text-muted-foreground mb-1 block">Type</label>
                                  <select
                                    className="w-full text-sm border rounded px-2 py-1"
                                    value={payment.tokenType}
                                    onChange={(e) => {
                                      const updated = [...batchPayments];
                                      updated[idx].tokenType = e.target.value as "native" | "erc20";
                                      if (e.target.value === "native") {
                                        updated[idx].tokenAddress = undefined;
                                      }
                                      setBatchPayments(updated);
                                    }}
                                  >
                                    <option value="native">Native CRO</option>
                                    <option value="erc20">ERC-20 Token</option>
                                  </select>
                                </div>

                                <div>
                                  <label className="text-xs text-muted-foreground mb-1 block">Amount</label>
                                  <Input
                                    type="number"
                                    step="0.0001"
                                    value={payment.amount}
                                    onChange={(e) => {
                                      const updated = [...batchPayments];
                                      updated[idx].amount = e.target.value;
                                      setBatchPayments(updated);
                                    }}
                                    placeholder="0.1"
                                    className="text-sm"
                                  />
                                </div>
                              </div>

                              {payment.tokenType === "erc20" && (
                                <div>
                                  <label className="text-xs text-muted-foreground mb-1 block">Token Address</label>
                                  <Input
                                    value={payment.tokenAddress || ""}
                                    onChange={(e) => {
                                      const updated = [...batchPayments];
                                      updated[idx].tokenAddress = e.target.value;
                                      setBatchPayments(updated);
                                    }}
                                    placeholder="0x..."
                                    className="font-mono text-xs"
                                  />
                                </div>
                              )}

                              <div>
                                <label className="text-xs text-muted-foreground mb-1 block">Recipient</label>
                                <Input
                                  value={payment.recipient}
                                  onChange={(e) => {
                                    const updated = [...batchPayments];
                                    updated[idx].recipient = e.target.value;
                                    setBatchPayments(updated);
                                  }}
                                  placeholder="0x..."
                                  className="font-mono text-xs"
                                />
                              </div>
                            </div>
                          </Card>
                        ))}
                      </div>
                    )}
                  </div>

                  <Button
                    onClick={executeBatchPayment}
                    disabled={
                      batchLoading ||
                      batchPayments.length === 0 ||
                      !x402FacilitatorAddress ||
                      !signer ||
                      batchPayments.some((p) => !p.recipient || !p.amount || (p.tokenType === "erc20" && !p.tokenAddress))
                    }
                    className="w-full"
                  >
                    {batchLoading ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Executing Batch...
                      </>
                    ) : (
                      <>
                        <Layers className="mr-2 h-4 w-4" />
                        Execute x402 Batch ({batchPayments.length} payments)
                      </>
                    )}
                  </Button>
                </TabsContent>
              </Tabs>

              {status && (
                <Alert
                  className={`mt-4 ${
                    status.type === "success"
                      ? "border-green-500"
                      : status.type === "error"
                      ? "border-red-500"
                      : "border-blue-500"
                  }`}
                >
                  <div className="flex items-start gap-2">
                    {status.type === "success" ? (
                      <CheckCircle2 className="h-4 w-4 text-green-500 mt-0.5" />
                    ) : status.type === "error" ? (
                      <XCircle className="h-4 w-4 text-red-500 mt-0.5" />
                    ) : (
                      <Loader2 className="h-4 w-4 text-blue-500 mt-0.5 animate-spin" />
                    )}
                    <AlertDescription>{status.message}</AlertDescription>
                  </div>
                  {txHash && explorerUrl() && (
                    <div className="mt-2 flex items-center gap-2">
                      <a
                        href={explorerUrl()!}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-blue-600 hover:underline flex items-center gap-1"
                      >
                        View on Cronoscan <ExternalLink className="h-3 w-3" />
                      </a>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => copyToClipboard(txHash)}
                        className="h-6 px-2"
                      >
                        <Copy className="h-3 w-3" />
                      </Button>
                    </div>
                  )}
                </Alert>
              )}

              {account && (
                <div className="mt-4 pt-4 border-t text-sm text-muted-foreground flex items-center justify-between">
                  <span>Connected: {account.slice(0, 6)}...{account.slice(-4)}</span>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => copyToClipboard(account)}
                  >
                    <Copy className="h-3 w-3" />
                  </Button>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Payment History */}
      {showHistory && paymentHistory.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Payment History</CardTitle>
            <CardDescription>Recent payment transactions</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 max-h-[400px] overflow-y-auto">
              {paymentHistory.map((payment) => {
                const explorerUrl = chainId === BigInt(25)
                  ? `https://cronoscan.com/tx/${payment.txHash}`
                  : `https://testnet.cronoscan.com/tx/${payment.txHash}`;
                return (
                  <div
                    key={`${payment.id}-${payment.txHash}`}
                    className="flex items-center justify-between p-3 border rounded-lg hover:bg-accent transition-colors"
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <Badge variant={payment.status === "success" ? "default" : "destructive"}>
                          {payment.status}
                        </Badge>
                        <span className="text-sm font-medium">
                          {payment.amount} {payment.token}
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground mt-1 font-mono">
                        {payment.txHash.slice(0, 16)}...{payment.txHash.slice(-8)}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {formatDistanceToNow(new Date(payment.timestamp), { addSuffix: true })}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => copyToClipboard(payment.txHash)}
                      >
                        <Copy className="h-3 w-3" />
                      </Button>
                      <a
                        href={explorerUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        <Button variant="ghost" size="sm">
                          <ExternalLink className="h-3 w-3" />
                        </Button>
                      </a>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
