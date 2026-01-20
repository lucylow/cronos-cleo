import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { WagmiProvider } from 'wagmi';
import { config } from '@/lib/wagmiConfig';
import { WalletProvider } from "@/wallet/WalletProvider";
import { AuthProvider } from "@/contexts/AuthContext";

import AppLayout from "./components/layout/AppLayout";
import Dashboard from "./pages/Dashboard";
import Settings from "./pages/Settings";
import Agent from "./pages/Agent";
import PaymentReview from "./pages/PaymentReview";
import Payments from "./pages/Payments";
import CLEOFrontend from "./components/CLEOFrontend";
import Index from "./pages/Index";
import NotFound from "./pages/NotFound";
import DaoPage from "./pages/DaoPage";
import ProposalDetailPage from "./pages/ProposalDetailPage";
import CreateProposalPage from "./pages/CreateProposalPage";
import Analytics from "./pages/Analytics";
import NFT from "./pages/NFT";
import Transactions from "./pages/Transactions";
import Portfolio from "./pages/Portfolio";
import Activity from "./pages/Activity";
import Documentation from "./pages/Documentation";
import Reports from "./pages/Reports";
import SignIn from "./pages/SignIn";
import UserAccount from "./pages/UserAccount";

const queryClient = new QueryClient();

const App = () => (
  <WagmiProvider config={config}>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <WalletProvider>
          <TooltipProvider>
            <Toaster />
            <Sonner />
            <BrowserRouter>
              <Routes>
                {/* Landing page without layout */}
                <Route path="/" element={<Index />} />
                
                {/* Authentication routes without layout */}
                <Route path="/signin" element={<SignIn />} />
                
                {/* App routes with sidebar layout */}
                <Route element={<AppLayout />}>
                  <Route path="/dashboard" element={<Dashboard />} />
                  <Route path="/execution/route" element={<Navigate to="/execution/routes" replace />} />
                  <Route path="/execution/routes" element={<CLEOFrontend />} />
                  <Route path="/execution/simulator" element={<CLEOFrontend />} />
                  <Route path="/agent" element={<Agent />} />
                  <Route path="/agent/decisions" element={<Agent />} />
                  <Route path="/agent/logs" element={<Agent />} />
                  <Route path="/settlement" element={<Dashboard />} />
                  <Route path="/payments" element={<Payments />} />
                  <Route path="/payment-review" element={<PaymentReview />} />
                  <Route path="/analytics" element={<Analytics />} />
                  <Route path="/transactions" element={<Transactions />} />
                  <Route path="/portfolio" element={<Portfolio />} />
                  <Route path="/activity" element={<Activity />} />
                  <Route path="/reports" element={<Reports />} />
                  <Route path="/documentation" element={<Documentation />} />
                  <Route path="/app" element={<CLEOFrontend />} />
                  <Route path="/settings" element={<Settings />} />
                  <Route path="/account" element={<UserAccount />} />
                  {/* DAO routes */}
                  <Route path="/dao" element={<DaoPage />} />
                  <Route path="/dao/:id" element={<ProposalDetailPage />} />
                  <Route path="/dao/create" element={<CreateProposalPage />} />
                  {/* NFT routes */}
                  <Route path="/nft" element={<NFT />} />
                </Route>
                
                <Route path="*" element={<NotFound />} />
              </Routes>
            </BrowserRouter>
          </TooltipProvider>
        </WalletProvider>
      </AuthProvider>
    </QueryClientProvider>
  </WagmiProvider>
);

export default App;
