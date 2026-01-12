import React, { useState, useEffect } from "react";
import { ethers, Contract } from "ethers";
import { useWallet } from "../wallet/WalletProvider";
import { verifyPayment } from "../lib/api";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import { Alert, AlertDescription } from "./ui/alert";
import { Loader2, CheckCircle2, XCircle } from "lucide-react";

// Payment contract ABI (minimal - only what we need)
const PAYMENT_ABI = [
  "function payNative() external payable returns (uint256)",
  "function payWithERC20(address token, uint256 amount) external returns (uint256)",
  "function payments(uint256) view returns (address payer, address token, uint256 amount, uint256 timestamp)",
  "event PaymentReceived(uint256 indexed paymentId, address indexed payer, address token, uint256 amount)",
];

// Standard ERC20 ABI
const ERC20_ABI = [
  "function approve(address spender, uint256 amount) external returns (bool)",
  "function allowance(address owner, address spender) external view returns (uint256)",
  "function decimals() external view returns (uint8)",
  "function balanceOf(address account) external view returns (uint256)",
  "function symbol() external view returns (string)",
];

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

export default function PaymentProcessor() {
  const { provider, signer, account, chainId, connect } = useWallet();
  const [paymentContractAddress, setPaymentContractAddress] = useState(getPaymentContractAddress());
  const [amount, setAmount] = useState("");
  const [tokenAddress, setTokenAddress] = useState("");
  const [tokenDecimals, setTokenDecimals] = useState<number>(18);
  const [tokenSymbol, setTokenSymbol] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<{ type: "success" | "error" | "info"; message: string } | null>(null);
  const [txHash, setTxHash] = useState<string | null>(null);
  const [paymentId, setPaymentId] = useState<number | null>(null);

  useEffect(() => {
    // Auto-fetch token info when token address is entered
    if (tokenAddress && signer && tokenAddress.startsWith("0x") && tokenAddress.length === 42) {
      fetchTokenInfo(tokenAddress);
    }
  }, [tokenAddress, signer]);

  const fetchTokenInfo = async (address: string) => {
    if (!signer) return;
    try {
      const tokenContract = new Contract(address, ERC20_ABI, signer);
      const [decimals, symbol] = await Promise.all([
        tokenContract.decimals(),
        tokenContract.symbol(),
      ]);
      setTokenDecimals(Number(decimals));
      setTokenSymbol(symbol);
    } catch (error) {
      console.error("Error fetching token info:", error);
      setTokenSymbol("");
      setTokenDecimals(18);
    }
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
      return;
    }

    if (!amount || parseFloat(amount) <= 0) {
      setStatus({ type: "error", message: "Enter a valid amount" });
      return;
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

        // Verify payment on backend
        try {
          const verifyResult = await verifyPayment({
            tx_hash: tx.hash,
            expected_recipient: paymentContractAddress,
            min_amount_wei: amountWei.toString(),
          });
          if (verifyResult.ok) {
            console.log("Payment verified:", verifyResult.result);
          }
        } catch (error) {
          console.error("Backend verification failed:", error);
        }
      }
    } catch (error: any) {
      console.error("Payment error:", error);
      setStatus({
        type: "error",
        message: error.message || "Payment failed",
      });
    } finally {
      setLoading(false);
    }
  };

  const payERC20 = async () => {
    if (!signer || !paymentContractAddress) {
      setStatus({ type: "error", message: "Connect wallet and set contract address" });
      return;
    }

    if (!tokenAddress || !tokenAddress.startsWith("0x")) {
      setStatus({ type: "error", message: "Enter a valid ERC-20 token address" });
      return;
    }

    if (!amount || parseFloat(amount) <= 0) {
      setStatus({ type: "error", message: "Enter a valid amount" });
      return;
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
        const approveTx = await tokenContract.approve(paymentContractAddress, amountWei);
        await approveTx.wait();
      }

      // Make payment
      setStatus({ type: "info", message: "Processing payment..." });
      const tx = await paymentContract.payWithERC20(tokenAddress, amountWei, {
        gasLimit: 200_000,
      });

      setStatus({ type: "info", message: `Transaction sent: ${tx.hash}` });
      setTxHash(tx.hash);

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
          }
        } catch (error) {
          console.error("Backend verification failed:", error);
        }
      }
    } catch (error: any) {
      console.error("Payment error:", error);
      setStatus({
        type: "error",
        message: error.message || "Payment failed",
      });
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

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle>Cronos Payment Processor</CardTitle>
        <CardDescription>
          Accept payments in native CRO or ERC-20 tokens on Cronos
        </CardDescription>
      </CardHeader>
      <CardContent>
        {!account ? (
          <div className="text-center py-8">
            <p className="text-muted-foreground mb-4">Connect your wallet to make payments</p>
            <Button onClick={connect}>Connect Wallet</Button>
          </div>
        ) : (
          <>
            <div className="mb-4">
              <label className="text-sm font-medium mb-2 block">Contract Address</label>
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
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="native">Native CRO</TabsTrigger>
                <TabsTrigger value="erc20">ERC-20 Token</TabsTrigger>
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
                <div>
                  <label className="text-sm font-medium mb-2 block">Token Address</label>
                  <Input
                    value={tokenAddress}
                    onChange={(e) => setTokenAddress(e.target.value)}
                    placeholder="0x..."
                    className="font-mono text-sm"
                  />
                  {tokenSymbol && (
                    <p className="text-xs text-muted-foreground mt-1">
                      Token: {tokenSymbol} (decimals: {tokenDecimals})
                    </p>
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
                  <div className="mt-2">
                    <a
                      href={explorerUrl()!}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-blue-600 hover:underline"
                    >
                      View on Cronoscan →
                    </a>
                  </div>
                )}
              </Alert>
            )}

            {account && (
              <div className="mt-4 pt-4 border-t text-sm text-muted-foreground">
                Connected: {account.slice(0, 6)}...{account.slice(-4)}
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
