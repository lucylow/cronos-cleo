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
import { Loader2, CheckCircle2, XCircle, AlertCircle, Clock } from 'lucide-react';
import { toast } from 'sonner';

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

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Payment Review Dashboard</h1>
          <p className="text-muted-foreground mt-2">
            Review and approve/reject flagged payments
          </p>
        </div>
        <Button onClick={fetchPending} disabled={loading}>
          {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
          Refresh
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Pending List */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>Pending Reviews</CardTitle>
            <CardDescription>{pending.length} payments awaiting review</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 max-h-[600px] overflow-y-auto">
              {pending.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-8">
                  No pending reviews
                </p>
              ) : (
                pending.map((payment) => (
                  <div
                    key={payment.id}
                    className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                      selected?.id === payment.id
                        ? 'border-primary bg-primary/5'
                        : 'hover:bg-accent'
                    }`}
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
