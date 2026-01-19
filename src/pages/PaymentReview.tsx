/**
 * Payment Review Dashboard - Operator UI for reviewing flagged payments
 */
import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, CheckCircle2, XCircle, AlertCircle, Clock, Filter, Download, BarChart3, Search } from 'lucide-react';
import { toast } from 'sonner';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

interface Payment {
  id: string;
  tx_hash: string;
  chain_id: number;
  payer: string;
  token_address?: string | null;
  amount: string;
  status: string;
  risk_score?: number | null;
  flagged_reason?: string | null;
  created_at: string;
  updated_at: string;
}

interface ReviewAction {
  operatorId?: string;
  action: 'approve' | 'reject' | 'request_info';
  comment?: string;
}

export default function PaymentReview() {
  const [pending, setPending] = useState<Payment[]>([]);
  const [selected, setSelected] = useState<Payment | null>(null);
  const [loading, setLoading] = useState(false);
  const [comment, setComment] = useState('');
  const [operatorId, setOperatorId] = useState<string>('');
  
  // Enhanced features
  const [filteredPending, setFilteredPending] = useState<Payment[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [riskFilter, setRiskFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<string>('newest');
  const [selectedPayments, setSelectedPayments] = useState<Set<string>>(new Set());
  const [showAnalytics, setShowAnalytics] = useState(false);

  useEffect(() => {
    // Initialize operator ID (in production, get from auth)
    const opId = localStorage.getItem('operatorId') || 'operator_' + Date.now();
    setOperatorId(opId);
    localStorage.setItem('operatorId', opId);

    // Connect to WebSocket (FastAPI WebSocket endpoint)
    // FastAPI uses native WebSocket, not socket.io
    const wsUrl = API_BASE.replace('http://', 'ws://').replace('https://', 'wss://');
    let websocket: WebSocket | null = null;
    
    function connectWebSocket() {
      try {
        websocket = new WebSocket(`${wsUrl}/api/hitl/ws`);
        
        websocket.onopen = () => {
          console.log('WebSocket connected');
          websocket?.send(JSON.stringify({ type: 'identify', operatorId: opId }));
        };
        
        websocket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === 'review:enqueue') {
              toast.info('New payment flagged for review');
              fetchPending();
            } else if (data.type === 'review:action') {
              if (data.paymentId === selected?.id) {
                setSelected(null);
              }
              fetchPending();
            } else if (data.type === 'identified') {
              console.log('Operator identified:', data.operatorId);
            } else if (data.type === 'payment:finalized') {
              console.log('Payment finalized:', data);
            }
          } catch (e) {
            console.error('Error parsing WebSocket message:', e);
          }
        };
        
        websocket.onerror = (error) => {
          console.error('WebSocket error:', error);
        };
        
        websocket.onclose = () => {
          console.log('WebSocket disconnected, reconnecting in 5s...');
          // Reconnect after 5 seconds
          setTimeout(connectWebSocket, 5000);
        };
      } catch (error) {
        console.error('Failed to create WebSocket:', error);
        // Fallback: poll for updates every 10 seconds
        const pollInterval = setInterval(fetchPending, 10000);
        return () => clearInterval(pollInterval);
      }
    }
    
    connectWebSocket();

    // Fetch initial pending reviews
    fetchPending();

    return () => {
      if (websocket) {
        websocket.close();
      }
    };
  }, []);

  async function fetchPending() {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/api/hitl/admin/pending`);
      const data = await response.json();
      if (data.ok) {
        setPending(data.pending || []);
      }
    } catch (error) {
      console.error('Error fetching pending:', error);
      toast.error('Failed to fetch pending reviews');
    } finally {
      setLoading(false);
    }
  }

  // Filter and sort payments
  useEffect(() => {
    let filtered = [...pending];

    // Status filter
    if (statusFilter !== 'all') {
      filtered = filtered.filter(p => p.status === statusFilter);
    }

    // Risk filter
    if (riskFilter !== 'all') {
      if (riskFilter === 'high') {
        filtered = filtered.filter(p => p.risk_score !== null && p.risk_score >= 7);
      } else if (riskFilter === 'medium') {
        filtered = filtered.filter(p => p.risk_score !== null && p.risk_score >= 4 && p.risk_score < 7);
      } else if (riskFilter === 'low') {
        filtered = filtered.filter(p => p.risk_score !== null && p.risk_score < 4);
      }
    }

    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(p => 
        p.tx_hash.toLowerCase().includes(query) ||
        p.payer.toLowerCase().includes(query) ||
        p.id.toLowerCase().includes(query)
      );
    }

    // Sort
    filtered.sort((a, b) => {
      if (sortBy === 'newest') {
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      } else if (sortBy === 'oldest') {
        return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
      } else if (sortBy === 'amount_high') {
        return BigInt(b.amount) - BigInt(a.amount);
      } else if (sortBy === 'amount_low') {
        return BigInt(a.amount) - BigInt(b.amount);
      } else if (sortBy === 'risk_high') {
        return (b.risk_score || 0) - (a.risk_score || 0);
      } else if (sortBy === 'risk_low') {
        return (a.risk_score || 0) - (b.risk_score || 0);
      }
      return 0;
    });

    setFilteredPending(filtered);
  }, [pending, statusFilter, riskFilter, searchQuery, sortBy]);

  async function viewPayment(payment: Payment) {
    try {
      const response = await fetch(`${API_BASE}/api/hitl/admin/payment/${payment.id}`);
      const data = await response.json();
      if (data.ok) {
        setSelected(data.payment);
      }
    } catch (error) {
      console.error('Error fetching payment:', error);
      toast.error('Failed to fetch payment details');
    }
  }

  async function takeAction(action: 'approve' | 'reject' | 'request_info') {
    if (!selected) return;

    const reviewAction: ReviewAction = {
      operatorId,
      action,
      comment: comment || undefined,
    };

    try {
      setLoading(true);
      const response = await fetch(
        `${API_BASE}/api/hitl/admin/payment/${selected.id}/action`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(reviewAction),
        }
      );

      const data = await response.json();
      if (data.ok) {
        toast.success(`Payment ${action}d successfully`);
        setSelected(null);
        setComment('');
        await fetchPending();
      } else {
        toast.error(data.error || 'Action failed');
      }
    } catch (error) {
      console.error('Error taking action:', error);
      toast.error('Failed to process action');
    } finally {
      setLoading(false);
    }
  }

  function formatAmount(amount: string): string {
    const wei = BigInt(amount);
    const cro = Number(wei) / 1e18;
    return cro.toFixed(4) + ' CRO';
  }

  function getStatusBadge(status: string) {
    const variants: Record<string, { variant: 'default' | 'secondary' | 'destructive' | 'outline'; icon: any }> = {
      flagged: { variant: 'destructive', icon: AlertCircle },
      pending_manual: { variant: 'secondary', icon: Clock },
      approved: { variant: 'default', icon: CheckCircle2 },
      rejected: { variant: 'destructive', icon: XCircle },
    };

    const config = variants[status] || { variant: 'outline', icon: null };
    const Icon = config.icon;

    return (
      <Badge variant={config.variant}>
        {Icon && <Icon className="w-3 h-3 mr-1" />}
        {status}
      </Badge>
    );
  }

  // Analytics calculations
  const analytics = {
    total: pending.length,
    flagged: pending.filter(p => p.status === 'flagged').length,
    approved: pending.filter(p => p.status === 'approved').length,
    rejected: pending.filter(p => p.status === 'rejected').length,
    highRisk: pending.filter(p => p.risk_score !== null && p.risk_score >= 7).length,
    totalAmount: pending.reduce((sum, p) => sum + BigInt(p.amount), 0n),
    averageRisk: pending.filter(p => p.risk_score !== null).length > 0
      ? pending.filter(p => p.risk_score !== null).reduce((sum, p) => sum + (p.risk_score || 0), 0) /
        pending.filter(p => p.risk_score !== null).length
      : 0,
  };

  // Bulk actions
  const handleBulkAction = async (action: 'approve' | 'reject') => {
    if (selectedPayments.size === 0) {
      toast.error('No payments selected');
      return;
    }

    try {
      setLoading(true);
      const promises = Array.from(selectedPayments).map(paymentId => {
        const payment = pending.find(p => p.id === paymentId);
        if (!payment) return Promise.resolve();

        const reviewAction: ReviewAction = {
          operatorId,
          action,
          comment: `Bulk ${action}`,
        };

        return fetch(`${API_BASE}/api/hitl/admin/payment/${paymentId}/action`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(reviewAction),
        });
      });

      await Promise.all(promises);
      toast.success(`Bulk ${action} completed for ${selectedPayments.size} payment(s)`);
      setSelectedPayments(new Set());
      await fetchPending();
    } catch (error) {
      console.error('Error in bulk action:', error);
      toast.error('Bulk action failed');
    } finally {
      setLoading(false);
    }
  };

  const togglePaymentSelection = (paymentId: string) => {
    const newSelected = new Set(selectedPayments);
    if (newSelected.has(paymentId)) {
      newSelected.delete(paymentId);
    } else {
      newSelected.add(paymentId);
    }
    setSelectedPayments(newSelected);
  };

  const selectAll = () => {
    if (selectedPayments.size === filteredPending.length) {
      setSelectedPayments(new Set());
    } else {
      setSelectedPayments(new Set(filteredPending.map(p => p.id)));
    }
  };

  // Export functionality
  const exportData = () => {
    const csv = [
      ['ID', 'TX Hash', 'Payer', 'Amount', 'Status', 'Risk Score', 'Flagged Reason', 'Created At'].join(','),
      ...filteredPending.map(p => [
        p.id,
        p.tx_hash,
        p.payer,
        formatAmount(p.amount),
        p.status,
        p.risk_score?.toFixed(2) || 'N/A',
        p.flagged_reason || '',
        new Date(p.created_at).toISOString(),
      ].join(','))
    ].join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `payment-review-${new Date().toISOString()}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
    toast.success('Data exported successfully');
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Payment Review Dashboard</h1>
          <p className="text-muted-foreground mt-2">
            Review and approve/reject flagged payments
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => setShowAnalytics(!showAnalytics)}
          >
            <BarChart3 className="w-4 h-4 mr-2" />
            Analytics
          </Button>
          <Button variant="outline" onClick={exportData} disabled={filteredPending.length === 0}>
            <Download className="w-4 h-4 mr-2" />
            Export
          </Button>
          <Button onClick={fetchPending} disabled={loading}>
            {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
            Refresh
          </Button>
        </div>
      </div>

      {/* Analytics Dashboard */}
      {showAnalytics && (
        <Card>
          <CardHeader>
            <CardTitle>Payment Analytics</CardTitle>
            <CardDescription>Overview of payment review statistics</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="p-4 border rounded-lg">
                <p className="text-sm text-muted-foreground">Total Payments</p>
                <p className="text-2xl font-bold">{analytics.total}</p>
              </div>
              <div className="p-4 border rounded-lg">
                <p className="text-sm text-muted-foreground">Flagged</p>
                <p className="text-2xl font-bold text-red-500">{analytics.flagged}</p>
              </div>
              <div className="p-4 border rounded-lg">
                <p className="text-sm text-muted-foreground">High Risk</p>
                <p className="text-2xl font-bold text-orange-500">{analytics.highRisk}</p>
              </div>
              <div className="p-4 border rounded-lg">
                <p className="text-sm text-muted-foreground">Total Amount</p>
                <p className="text-2xl font-bold">{formatAmount(analytics.totalAmount.toString())}</p>
              </div>
              <div className="p-4 border rounded-lg">
                <p className="text-sm text-muted-foreground">Approved</p>
                <p className="text-2xl font-bold text-green-500">{analytics.approved}</p>
              </div>
              <div className="p-4 border rounded-lg">
                <p className="text-sm text-muted-foreground">Rejected</p>
                <p className="text-2xl font-bold text-red-500">{analytics.rejected}</p>
              </div>
              <div className="p-4 border rounded-lg">
                <p className="text-sm text-muted-foreground">Avg Risk Score</p>
                <p className="text-2xl font-bold">{analytics.averageRisk.toFixed(2)}</p>
              </div>
              <div className="p-4 border rounded-lg">
                <p className="text-sm text-muted-foreground">Selected</p>
                <p className="text-2xl font-bold">{selectedPayments.size}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Filters and Search */}
      <Card>
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="relative">
              <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search by TX hash, payer..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger>
                <SelectValue placeholder="Filter by status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="flagged">Flagged</SelectItem>
                <SelectItem value="pending_manual">Pending Manual</SelectItem>
                <SelectItem value="approved">Approved</SelectItem>
                <SelectItem value="rejected">Rejected</SelectItem>
              </SelectContent>
            </Select>
            <Select value={riskFilter} onValueChange={setRiskFilter}>
              <SelectTrigger>
                <SelectValue placeholder="Filter by risk" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Risk Levels</SelectItem>
                <SelectItem value="high">High Risk (≥7)</SelectItem>
                <SelectItem value="medium">Medium Risk (4-6)</SelectItem>
                <SelectItem value="low">Low Risk (&lt;4)</SelectItem>
              </SelectContent>
            </Select>
            <Select value={sortBy} onValueChange={setSortBy}>
              <SelectTrigger>
                <SelectValue placeholder="Sort by" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="newest">Newest First</SelectItem>
                <SelectItem value="oldest">Oldest First</SelectItem>
                <SelectItem value="amount_high">Amount: High to Low</SelectItem>
                <SelectItem value="amount_low">Amount: Low to High</SelectItem>
                <SelectItem value="risk_high">Risk: High to Low</SelectItem>
                <SelectItem value="risk_low">Risk: Low to High</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Pending List */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Pending Reviews</CardTitle>
                <CardDescription>{filteredPending.length} of {pending.length} payments</CardDescription>
              </div>
              {filteredPending.length > 0 && (
                <Button variant="ghost" size="sm" onClick={selectAll}>
                  {selectedPayments.size === filteredPending.length ? 'Deselect All' : 'Select All'}
                </Button>
              )}
            </div>
            {selectedPayments.size > 0 && (
              <div className="flex gap-2 mt-2">
                <Button
                  size="sm"
                  variant="default"
                  onClick={() => handleBulkAction('approve')}
                  disabled={loading}
                >
                  <CheckCircle2 className="w-3 h-3 mr-1" />
                  Approve {selectedPayments.size}
                </Button>
                <Button
                  size="sm"
                  variant="destructive"
                  onClick={() => handleBulkAction('reject')}
                  disabled={loading}
                >
                  <XCircle className="w-3 h-3 mr-1" />
                  Reject {selectedPayments.size}
                </Button>
              </div>
            )}
          </CardHeader>
          <CardContent>
            <div className="space-y-2 max-h-[600px] overflow-y-auto">
              {filteredPending.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-8">
                  {pending.length === 0 ? 'No pending reviews' : 'No payments match filters'}
                </p>
              ) : (
                filteredPending.map((payment) => (
                  <div
                    key={payment.id}
                    className={`p-3 border rounded-lg transition-colors ${
                      selected?.id === payment.id
                        ? 'border-primary bg-primary/5'
                        : 'hover:bg-accent'
                    }`}
                  >
                    <div className="flex items-start gap-2 mb-2">
                      <Checkbox
                        checked={selectedPayments.has(payment.id)}
                        onCheckedChange={() => togglePaymentSelection(payment.id)}
                        onClick={(e) => e.stopPropagation()}
                      />
                      <div
                        className="flex-1 cursor-pointer"
                        onClick={() => viewPayment(payment)}
                      >
                        <div className="flex items-start justify-between mb-2">
                          <div className="font-mono text-xs text-muted-foreground truncate flex-1">
                            {payment.tx_hash.slice(0, 16)}...
                          </div>
                          {getStatusBadge(payment.status)}
                        </div>
                        <div className="text-sm">
                          <div>Payer: {payment.payer.slice(0, 10)}...</div>
                          <div className="font-semibold">{formatAmount(payment.amount)}</div>
                          {payment.risk_score !== null && (
                            <div className="text-xs text-muted-foreground">
                              Risk: {payment.risk_score.toFixed(1)}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>

        {/* Review Panel */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>
              {selected ? `Review Payment: ${selected.tx_hash.slice(0, 20)}...` : 'Select a Payment'}
            </CardTitle>
            <CardDescription>
              {selected
                ? 'Review payment details and take action'
                : 'Select a payment from the list to review'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {selected ? (
              <div className="space-y-6">
                <Tabs defaultValue="details">
                  <TabsList>
                    <TabsTrigger value="details">Details</TabsTrigger>
                    <TabsTrigger value="evidence">Evidence</TabsTrigger>
                  </TabsList>

                  <TabsContent value="details" className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="text-sm font-medium text-muted-foreground">
                          Transaction Hash
                        </label>
                        <p className="font-mono text-sm break-all">{selected.tx_hash}</p>
                      </div>
                      <div>
                        <label className="text-sm font-medium text-muted-foreground">Status</label>
                        <div className="mt-1">{getStatusBadge(selected.status)}</div>
                      </div>
                      <div>
                        <label className="text-sm font-medium text-muted-foreground">Payer</label>
                        <p className="font-mono text-sm">{selected.payer}</p>
                      </div>
                      <div>
                        <label className="text-sm font-medium text-muted-foreground">Amount</label>
                        <p className="font-semibold">{formatAmount(selected.amount)}</p>
                      </div>
                      <div>
                        <label className="text-sm font-medium text-muted-foreground">
                          Risk Score
                        </label>
                        <p className="text-sm">
                          {selected.risk_score !== null
                            ? selected.risk_score.toFixed(2)
                            : 'N/A'}
                        </p>
                      </div>
                      <div>
                        <label className="text-sm font-medium text-muted-foreground">
                          Chain ID
                        </label>
                        <p className="text-sm">{selected.chain_id}</p>
                      </div>
                    </div>

                    {selected.flagged_reason && (
                      <Alert>
                        <AlertCircle className="h-4 w-4" />
                        <AlertDescription>
                          <strong>Flagged Reason:</strong> {selected.flagged_reason}
                        </AlertDescription>
                      </Alert>
                    )}

                    <div>
                      <label className="text-sm font-medium mb-2 block">Review Comment</label>
                      <Textarea
                        placeholder="Add a comment for this review..."
                        value={comment}
                        onChange={(e) => setComment(e.target.value)}
                        rows={4}
                      />
                    </div>

                    <div className="flex gap-3 pt-4">
                      <Button
                        onClick={() => takeAction('approve')}
                        disabled={loading}
                        className="flex-1"
                        variant="default"
                      >
                        <CheckCircle2 className="w-4 h-4 mr-2" />
                        Approve
                      </Button>
                      <Button
                        onClick={() => takeAction('reject')}
                        disabled={loading}
                        className="flex-1"
                        variant="destructive"
                      >
                        <XCircle className="w-4 h-4 mr-2" />
                        Reject
                      </Button>
                      <Button
                        onClick={() => takeAction('request_info')}
                        disabled={loading}
                        variant="outline"
                      >
                        <AlertCircle className="w-4 h-4 mr-2" />
                        Request Info
                      </Button>
                    </div>
                  </TabsContent>

                  <TabsContent value="evidence">
                    <Alert>
                      <AlertDescription>
                        Evidence gathering is handled by background workers. Transaction details
                        are fetched on-chain when the payment is enqueued for review.
                      </AlertDescription>
                    </Alert>
                    <div className="mt-4">
                      <p className="text-sm text-muted-foreground">
                        View transaction on block explorer:
                      </p>
                      <a
                        href={`https://cronoscan.com/tx/${selected.tx_hash}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary hover:underline text-sm"
                      >
                        {selected.tx_hash}
                      </a>
                    </div>
                  </TabsContent>
                </Tabs>
              </div>
            ) : (
              <div className="text-center py-12 text-muted-foreground">
                <AlertCircle className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>Select a payment from the list to review</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
