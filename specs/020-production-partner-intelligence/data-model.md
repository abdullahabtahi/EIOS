# Data Model: Production-Grade Partner Churn & Retention Intelligence

## Core Entities & Schemas

### 1. `PartnerChurnItem` (Extended Forensic Schema)
Represents a monitored partner entity within the Churn Hazard Radar and Triage Grid.

```typescript
export interface PartnerChurnItem {
  partnerId: string;                    // Primary key (e.g., 'PTR-882')
  name: string;                         // Business / Legal name
  tier: 'TIER_1_SUPER' | 'TIER_2_MASTER' | 'TIER_3_AFFILIATE';
  pChurn: number;                       // 0.00 to 1.00 (30D cumulative hazard)
  valueAtRiskUsd: number;               // 30D projected volume / commission at risk
  daysToChurn: number;                  // Golden window countdown (e.g., 14)
  changePointDetected: boolean;         // PELT statistical inflection flag
  mirrorTradeCorrelation: number;       // Collusion score against client orders
  extractedCommissionUsd: number;       // Total commission generated
  region: string;                       // e.g., 'LatAm (Colombia)'
  cohort: string;                       // e.g., 'LatAm P2P Cashier'
  
  // Historical Drift Vectors
  historicalDrift?: {
    tMinus30d: { pChurn: number; valueAtRiskUsd: number };
    tMinus14d: { pChurn: number; valueAtRiskUsd: number };
    driftVelocityPct: number;           // WoW acceleration of decay
  };

  // Multi-Signal Root Cause Decomposition
  loginDecayPct?: number;               // e.g., -68%
  referralDropWoWPct?: number;          // e.g., -44%
  cashierLatencyHours?: number;         // e.g., 4.8h
  supportTicketCount?: number;          // e.g., 3 open tickets
  competitorPoaching?: string;          // e.g., 'Exness Gold Promo'
  primaryDriver: 'OPERATIONAL_CASHIER' | 'COMPETITIVE_POACHING' | 'COMMERCIAL_REBATE' | 'CYCLICAL';

  // Causal Retention Playbook
  projectedLiftPct?: number;            // e.g., 74%
  netMarginRecoveryUsd?: number;        // e.g., $38,200 USD
  empiricalPlaybookWinRate?: number;    // e.g., 0.785 (11/14 historical retention)
}
```

### 2. `WhatIfCausalResponse` (Backend Contract)
Response payload from `POST /api/v1/churn/partner/{partner_id}/what-if`.

```json
{
  "partner_id": "PTR-882",
  "evaluator_model": "gemini-3.8-flash",
  "evaluated_at": "2026-10-12T04:00:00Z",
  "query_prompt": "Simulate VIP Spread Rebate (+1.20/lot)",
  "projected_retention_lift_pct": 74.0,
  "confidence_interval_95": [66.0, 82.0],
  "estimated_deal_cost_usd": 18000.0,
  "projected_net_margin_usd": 92000.0,
  "verdict": "OPTIMAL_FRONTIER_APPROVED",
  "governed_decision_rationale": "Gemini 3.8 Flash Causal Evaluation: Proposed spread rebate tier (+1.20/lot) lies on the optimal Pareto frontier. Delivers 74% retention lift with 5.1x net margin recovery ratio.",
  "causal_refuter_p_value": 0.44
}
```
