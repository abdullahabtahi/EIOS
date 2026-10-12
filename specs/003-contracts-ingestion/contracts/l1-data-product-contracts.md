# Layer 1 Data Product Contracts Catalog

**Feature**: `003-contracts-ingestion` | **Date**: 2026-10-04  
**Source of Truth**: `docs/data_products_and_omcp.md` §1 & Constitution Principle IV  

This catalog defines the contracts for all 14 Layer 1 data products enforced by the Ingestion Gateway. Any incoming event violating these specifications is routed to `eios.l1.dlq.v1` and sets the product state to `DEGRADED`.

---

## 1. Summary Catalog

| # | Data Product | Domain | Grain | Freshness SLA | Marking | Pydantic Schema Model | Null Ceiling |
|---|---|---|---|---|---|---|---|
| **1** | `client_360` | Client | `client_id` | $\le 5\text{ min}$ | **P** | `Client360Event` | `client_id: 0.0%`, `region: 0.0%` |
| **2** | `client_funnel` | Client | `client_id` $\times$ `stage` | $\le 15\text{ min}$ | **P** | `ClientFunnelEvent` | `client_id: 0.0%`, `stage: 0.0%` |
| **3** | `transactions_aml` | Compliance | `txn_id` | $\le 30\text{ sec}$ | **P, S** | `TransactionAMLEvent` | `txn_id: 0.0%`, `amount: 0.0%` |
| **4** | `trading_activity` | Client | `trade_id` | $\le 30\text{ sec}$ | **P** | `TradingActivityEvent` | `trade_id: 0.0%`, `side: 0.0%` |
| **5** | `device_network_graph` | Client | `edge_id` | $\le 1\text{ min}$ | **P, S** | `DeviceGraphEdgeEvent` | `source_id: 0.0%`, `target_id: 0.0%` |
| **6** | `partner_360` | Partner | `partner_id` | $\le 15\text{ min}$ | – | `Partner360Event` | `partner_id: 0.0%`, `tier: 0.0%` |
| **7** | `partner_referral_tree` | Partner | `(parent, child)` | $\le 15\text{ min}$ | – | `ReferralTreeEdgeEvent` | `parent_id: 0.0%`, `child_id: 0.0%` |
| **8** | `commission_ledger` | Financial | `entry_id` | $\le 15\text{ min}$ | – | `CommissionLedgerEvent` | `entry_id: 0.0%`, `amount: 0.0%` |
| **9** | `partner_engagement_signals`| Partner | `partner_id` $\times$ `date` | $\le 1\text{ hr}$ | – | `PartnerSignalsEvent` | `partner_id: 0.0%`, `date: 0.0%` |
| **10**| `partner_comms` | Partner | `message_id` | $\le 15\text{ min}$ | **S** | `PartnerCommsEvent` | `message_id: 0.0%`, `text: 0.0%` |
| **11**| `financial_pnl` | Financial | `day` $\times$ `prod` $\times$ `reg` | $\le 1\text{ hr}$ | – | `FinancialPnLEvent` | `date: 0.0%`, `revenue: 0.0%` |
| **12**| `competitor_benchmarks` | Competitive | `competitor` $\times$ `day` | $\le 24\text{ hr}$ | – | `CompetitorBenchmarkEvent`| `competitor: 0.0%`, `spread: 0.0%` |
| **13**| `platform_operations` | Operational | `day` $\times$ `service` | $\le 5\text{ min}$ | – | `PlatformOperationsEvent` | `service: 0.0%`, `latency_p95: 0.0%` |
| **14**| `compliance_cases` | Compliance | `case_id` | $\le 1\text{ min}$ | **S** | `ComplianceCaseEvent` | `case_id: 0.0%`, `status: 0.0%` |

*Security Marking Key*:
- **P**: Pseudonymized before in-memory storage or reasoning LLM exposure (HMAC-SHA256 surrogate tokens).
- **S**: Sensitive restricted compliance marking (accessible only via authorized roles).

---

## 2. Pydantic Core Contract Definitions (Extract)

### 2.1 `TransactionAMLEvent` (`transactions_aml`)
```python
class TransactionAMLEvent(BaseModel):
  txn_id: str = Field(..., min_length=8)
  client_id: str = Field(..., min_length=6)
  txn_type: Literal['DEPOSIT', 'WITHDRAWAL', 'TRANSFER', 'ESCROW_RELEASE']
  amount: float = Field(..., gt=0.0)
  currency: str = Field(..., min_length=3, max_length=5)
  payment_method_id: str
  payment_agent_id: str | None = None
  timestamp: datetime
  is_first_deposit: bool = False
```

### 2.2 `TradingActivityEvent` (`trading_activity`)
```python
class TradingActivityEvent(BaseModel):
  trade_id: str = Field(..., min_length=8)
  client_id: str = Field(..., min_length=6)
  symbol: str = Field(..., min_length=2)  # e.g. "VOL_75", "BOOM_1000", "EURUSD"
  side: Literal['BUY', 'SELL']
  volume: float = Field(..., gt=0.0)
  open_price: float = Field(..., gt=0.0)
  close_price: float | None = None
  open_ts: datetime
  close_ts: datetime | None = None
  profit_loss: float | None = None
```

### 2.3 `Client360Event` (`client_360`)
```python
class Client360Event(BaseModel):
  client_id: str = Field(..., min_length=6)
  tax_id: str = Field(..., min_length=4)  # Marking P: Tokenized on entry
  full_name: str = Field(..., min_length=2)  # Marking P: Tokenized on entry
  email: str = Field(..., min_length=5)  # Marking P: Tokenized on entry
  phone: str = Field(..., min_length=6)  # Marking P: Tokenized on entry
  dob: date
  country: str = Field(..., min_length=2, max_length=3)
  kyc_status: Literal['PENDING', 'APPROVED', 'REJECTED', 'EDD_REQUIRED']
  kyc_approved_at: datetime | None = None
  partner_id: str | None = None
  declared_monthly_income: float | None = Field(default=None, ge=0.0)
```
