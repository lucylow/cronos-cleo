# Human-In-The-Loop (HITL) Payment Review System

A comprehensive payment review system that integrates human operators into the payment verification workflow. This system flags high-risk payments for manual review while auto-approving low-risk transactions.

## Features

- **Risk Scoring**: Automatic risk assessment based on amount, frequency, and other heuristics
- **Queue Management**: Redis-based queue for background evidence gathering
- **Real-time Notifications**: WebSocket support for operator notifications
- **Audit Trail**: Complete audit logging for compliance
- **Operator Dashboard**: React-based UI for reviewing and approving payments

## Architecture

```
[Payment Detection] → [Risk Scoring] → [Auto-approve OR Flag for Review]
                                              ↓
                                    [Background Worker]
                                              ↓
                                    [Evidence Gathering]
                                              ↓
                                    [Operator Dashboard]
                                              ↓
                                    [Approve/Reject]
```

## Database Schema

The system uses the following tables:

- `operators`: Human reviewers/operators
- `hitl_payments`: Payment records
- `hitl_reviews`: Review records (one per operator action)
- `hitl_audit_logs`: Audit trail (append-only)

## Setup

### 1. Install Dependencies

```bash
cd cleo_project/backend
pip install -r requirements.txt
```

### 2. Configure Environment

Add to your `.env` file:

```env
DATABASE_URL=postgres://user:pass@localhost:5432/cronos_hack
# or for SQLite:
# DATABASE_URL=sqlite:///./cleo_data.db

REDIS_URL=redis://localhost:6379
CRONOS_RPC=https://evm-t3.cronos.org
```

### 3. Run Database Migrations

```bash
cd cleo_project/backend
python -m hitl.migrations
```

This will create all HITL tables in your database.

### 4. Start the Backend

The HITL system is automatically initialized when the main FastAPI app starts:

```bash
python main.py
# or
uvicorn main:app --reload
```

The HITL API endpoints will be available at `/api/hitl/*`.

## API Endpoints

### Payment Observation

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

Response:
```json
{
  "ok": true,
  "status": "flagged" | "approved",
  "paymentId": "..."
}
```

### Admin Endpoints

- `GET /api/hitl/admin/pending` - Get pending reviews
- `GET /api/hitl/admin/payment/{payment_id}` - Get payment details
- `POST /api/hitl/admin/payment/{payment_id}/action` - Approve/reject payment
- `GET /api/hitl/admin/audit/export` - Export audit logs

### WebSocket

Connect to `/api/hitl/ws` for real-time notifications.

## Frontend Integration

The React admin dashboard is available at `/payment-review` route.

### Using in Your Code

After a payment transaction is confirmed, call the observe endpoint:

```typescript
const txHash = receipt.transactionHash;
const response = await fetch(`${API_BASE}/api/hitl/payments/observe`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    txHash,
    chainId: 338,
    payer: userAddress,
    amountWei: amountWei.toString(),
    tokenAddress: tokenAddress || null
  })
});

const data = await response.json();
if (data.status === 'flagged') {
  // Show "Under review" message to user
}
```

## Risk Scoring

The default risk scoring algorithm considers:

1. **Amount**: 
   - High amount (≥100 CRO): +70 points
   - Medium amount (≥10 CRO): +30 points

2. **Frequency**:
   - 5+ payments in last hour: +30 points
   - 2+ payments in last hour: +10 points

Payments with risk score ≥50 are flagged for review.

You can customize the risk scoring by modifying `HITLService.simple_risk_score()`.

## Background Workers

For production, set up Redis Queue (RQ) workers:

```bash
# Install RQ
pip install rq

# Start worker
rq worker hitl-payments --url redis://localhost:6379
```

Then modify `hitl/api.py` to enqueue jobs:

```python
from rq import Queue
from hitl.worker import enrich_payment_job

review_queue = Queue('hitl-payments', connection=redis_conn)
job = review_queue.enqueue(
    enrich_payment_job,
    payment.id,
    rpc_url=CRONOS_RPC,
    database_url=DATABASE_URL
)
```

## Security Considerations

1. **Operator Authentication**: Add JWT-based authentication for operators
2. **Rate Limiting**: Add rate limits to `/payments/observe` endpoint
3. **Access Control**: Implement role-based access control (RBAC)
4. **Audit Logs**: Keep audit logs immutable and backed up
5. **Private Keys**: Never log or expose private keys

## Testing

### Manual Testing

1. Create a test payment observation:
```bash
curl -X POST http://localhost:8000/api/hitl/payments/observe \
  -H "Content-Type: application/json" \
  -d '{
    "txHash": "0x123...",
    "chainId": 338,
    "payer": "0xabc...",
    "amountWei": "200000000000000000000",
    "tokenAddress": null
  }'
```

2. Check pending reviews:
```bash
curl http://localhost:8000/api/hitl/admin/pending
```

3. Approve a payment:
```bash
curl -X POST http://localhost:8000/api/hitl/admin/payment/{payment_id}/action \
  -H "Content-Type: application/json" \
  -d '{
    "operatorId": "operator_123",
    "action": "approve",
    "comment": "Looks good"
  }'
```

## Future Enhancements

- [ ] ML-based anomaly detection
- [ ] Integration with Chainalysis/CipherTrace for address reputation
- [ ] KYC integration (Jumio)
- [ ] Multi-approval workflows for high-value transactions
- [ ] Email/SMS notifications
- [ ] Evidence storage in S3/object storage
- [ ] Advanced rules engine (JSON-driven)

## License

Part of the C.L.E.O. project.
