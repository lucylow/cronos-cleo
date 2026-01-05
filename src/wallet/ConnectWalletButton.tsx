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
      <div className="flex items-center gap-3">
        <div className="hidden sm:flex flex-col items-end text-sm">
          <span className="font-semibold text-foreground">{shorten(account)}</span>
          <span className="text-xs text-muted-foreground">
            {balance ? `${parseFloat(balance).toFixed(2)} CRO` : ""}
          </span>
        </div>
        <Button variant="outline" size="sm" onClick={disconnect} className="gap-2">
          <LogOut className="h-4 w-4" />
          <span className="hidden sm:inline">Disconnect</span>
        </Button>
      </div>
    );
  }

  return (
    <Button onClick={handleConnect} disabled={connecting} className="gap-2">
      <Wallet className="h-4 w-4" />
      {connecting ? "Connecting..." : "Connect Wallet"}
    </Button>
  );
}
