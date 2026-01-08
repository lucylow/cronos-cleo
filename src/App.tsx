import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { WalletProvider } from "@/wallet/WalletProvider";

import AppLayout from "./components/layout/AppLayout";
import Dashboard from "./pages/Dashboard";
import Settings from "./pages/Settings";
import Agent from "./pages/Agent";
import CLEOFrontend from "./components/CLEOFrontend";
import Index from "./pages/Index";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <WalletProvider>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <BrowserRouter>
          <Routes>
            {/* Landing page without layout */}
            <Route path="/" element={<Index />} />
            
            {/* App routes with sidebar layout */}
            <Route element={<AppLayout />}>
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/execution/routes" element={<CLEOFrontend />} />
              <Route path="/execution/simulator" element={<CLEOFrontend />} />
              <Route path="/agent" element={<Agent />} />
              <Route path="/agent/decisions" element={<Agent />} />
              <Route path="/agent/logs" element={<Agent />} />
              <Route path="/settlement" element={<Dashboard />} />
              <Route path="/app" element={<CLEOFrontend />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/account" element={<Dashboard />} />
            </Route>
            
            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </TooltipProvider>
    </WalletProvider>
  </QueryClientProvider>
);

export default App;
