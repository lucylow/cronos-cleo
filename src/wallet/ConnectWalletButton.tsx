import { useWallet } from "./WalletProvider";
import { Button } from "@/components/ui/button";
import { Wallet, LogOut } from "lucide-react";
import { toast } from "sonner";

export default function ConnectWalletButton() {
  const { account, balance, connecting, connect, disconnect, shorten } = useWallet();

  const handleConnect = async () => {
    try {
      await connect();
      toast.success("Wallet connected!");
    } catch (e: any) {
      toast.error(e?.message || "Connection failed");
    }
  };

  if (account) {
    return (
      <div className="flex items-center gap-3" role="status" aria-live="polite">
        <div className="hidden sm:flex flex-col items-end text-sm" aria-label={`Connected wallet: ${account}, Balance: ${balance ? `${parseFloat(balance).toFixed(2)} CRO` : 'Loading...'}`}>
          <span className="font-semibold text-foreground">{shorten(account)}</span>
          <span className="text-xs text-muted-foreground">
            {balance ? `${parseFloat(balance).toFixed(2)} CRO` : ""}
          </span>
        </div>
        <Button 
          variant="outline" 
          size="sm" 
          onClick={disconnect} 
          className="gap-2"
          aria-label="Disconnect wallet"
        >
          <LogOut className="h-4 w-4" aria-hidden="true" />
          <span className="hidden sm:inline">Disconnect</span>
        </Button>
      </div>
    );
  }

  return (
    <Button 
      onClick={handleConnect} 
      disabled={connecting} 
      className="gap-2"
      aria-label={connecting ? "Connecting wallet" : "Connect wallet"}
      aria-busy={connecting}
    >
      <Wallet className="h-4 w-4" aria-hidden="true" />
      {connecting ? "Connecting..." : "Connect Wallet"}
    </Button>
  );
}
