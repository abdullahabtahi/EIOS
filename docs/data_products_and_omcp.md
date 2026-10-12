# Data Products, Ontology & OMCP Contracts

Companion to `initial_plan.md` §4. Contract shape follows `.agents/skills/mckinsey-rewired-2nd/references/data-product-spec.yaml`; ontology nodes/edges follow `financial-ontology-schema.gql` in the same folder. Freshness/SLA values are `[ASSUMPTION]` until confirmed in P0. Agents and the cockpit consume these products **only through the Ontology API / OMCP tools** — never raw tables.

---

## 1. Data-product catalog

Owner = persona role (simulated). Grain = row identity. Marking: **P** = pseudonymised before LLM, **S** = sensitive (restricted marking).

| Product | Domain | Grain | Key fields (illustrative) | Freshness SLA | Marking | Consumers |
|---|---|---|---|---|---|---|
| `client_360` | Client | client_id | kyc_status, kyc_approved_at, segment, region, lifetime_value, partner_id | 5 min | P | A, B, Synthesis |
| `client_funnel` | Client | client_id × stage | stage, entered_at, source | 15 min | P | Synthesis, B |
| `transactions_aml` | Compliance | txn_id | client_id, type (deposit/withdrawal), amount, method_id, ts | 30 s | P,S | A |
| `trading_activity` | Client | trade_id | client_id, instrument, side, size, open_ts, close_ts, pnl | 30 s | P | A, B |
| `device_network_graph` | Client | edge (entity, entity) | device_id, ip_id, payment_method_id, first/last_seen, degree | 1 min | P,S | A, B |
| `partner_360` | Partner | partner_id | tier, region, tenure, value_at_risk, manager_id | 15 min | – | B, C, Synthesis |
| `partner_referral_tree` | Partner | (parent, child) | layer, attributed_master_id, since | 15 min | – | B |
| `commission_ledger` | Financial | entry_id | partner_id, client_id, basis, amount, paid_at | 15 min | – | B, C, Synthesis |
| `partner_engagement_signals` | Partner | partner_id × day | logins, referrals, ftd_count, conversion, clicks | 1 h | – | C |
| `partner_comms` | Partner | message_id | partner_id, channel, sentiment, text (untrusted) | 15 min | S | C |
| `financial_pnl` | Financial | day × product × region | revenue, cost, margin, ltv_cohort | 1 h | – | Synthesis |
| `competitor_benchmarks` | Competitive | competitor × day × region | payout_rate, spread, promo_event | 1 d | – | C, Synthesis |
| `platform_operations` | Operational | day × service | latency_p95, incidents, escrow_disputes | 5 min | – | Synthesis |
| `compliance_cases` | Compliance | case_id | client_id, status, typology, analyst, decision | 1 min | S | A |
| `decision_ledger` | Governance | seq | action_intent_id, decision, approver, prev_hash, hash | real-time | S | All (read-only) |

### Contract template (per product; YAML, versioned)
```yaml
product: partner_engagement_signals
version: 1.0.0
owner_role: head_of_partnerships
grain: [partner_id, date]
schema:            # Pydantic-generated JSON Schema is the source of truth
  partner_id: {type: string, required: true, entity: Partner}
  date:       {type: date,   required: true}
  logins:     {type: integer, min: 0}
freshness_sla: {max_lag: PT1H, on_breach: degrade_with_banner}
quality:
  null_rate_max: {partner_id: 0.0}
  volume_anomaly: {z_max: 4.0}
semantic_metrics: [login_decay_28d, referral_velocity_28d]
security: {markings: [], pii_fields: []}
interfaces: {rest: /v1/products/partner_engagement_signals, omcp: get_partner_signals}
```

Breach policy: schema/null/volume violation → record to DLQ + alert + mark product `DEGRADED` (freshness banner in UI); never silently drop.

---

## 2. Ontology

### Object types
`ClientAccount, Device, IPAddress, PaymentMethod, Partner, SubAffiliate, Competitor, Product, Region, Case, Alert, Decision, MacroEvent`

### Link types (representative)
| Link | From → To | Notes |
|---|---|---|
| `USES_DEVICE` | ClientAccount → Device | weighted by sessions |
| `CONNECTS_FROM` | ClientAccount → IPAddress | hub-suppression attribute `is_shared_context` |
| `FUNDS_VIA` | ClientAccount → PaymentMethod | |
| `REFERRED_BY` | ClientAccount → Partner | attribution layer 1..3 |
| `SUB_OF` | SubAffiliate → Partner | tree depth |
| `COMPETES_IN` | Competitor → Region/Product | |
| `AFFECTS` | MacroEvent / competitor event → Partner/Region | causal DAG edge candidate |
| `RAISED` | Alert → Case | |
| `DECIDED` | Decision → Case/Alert | writes to ledger |

### Functions (logic)
Deterministic, unit-tested Python functions registered in the Ontology: `partner_value_at_risk`, `ring_membership`, `client_quality_score`, `churn_priority`, `scenario_propagate`. LLMs call them via OMCP; they never re-implement them.

### Action types (governed; see `initial_plan.md` §6)
| Action | Parameters | Severity | Approval |
|---|---|---|---|
| `FreezeAccount` | client_id, reason_code, evidence_refs | High | Four-eyes |
| `HoldWithdrawal` | txn_id, reason, expires_at | High | Single approver, fast path |
| `ClawbackCommission` | partner_id, period, amount, evidence_refs | High | Four-eyes |
| `SuspendPartner` | partner_id, scope, evidence_refs | High | Four-eyes |
| `LaunchRetentionPlaybook` | partner_ids, playbook_id, budget | Medium | Single approver |
| `EscalateToMLRO` | case_id, summary_ref | Medium | Single approver |
| `FileSARDraft` | case_id, template_id | Medium | MLRO approval; draft only — no real filing |

### Security markings & Token Vault
- `PII` (pseudonymised for LLMs): Enforced at ingestion spine via Layer 1 Token Vault. Direct identifiers are replaced with tokens (`tok_usr_<uuid>`).
- **Identity Cluster Key (`tok_id_cluster_<hex16>`)**: Entity Resolution links related devices, payment instruments, and KYC attributes across registrations into an identity cluster, stamping a deterministic pseudonymized cluster token. This enables agents to detect client recycling and multi-affiliate fraud syndicates without exposing personal data to LLM context.
- `SENSITIVE_COMPLIANCE` (MLRO/analyst roles), `PARTNER_COMMERCIAL` (partnerships/finance), enforced server-side in the Ontology API by role → marking mapping. Markings propagate along lineage.

---

## 3. OMCP tool contracts

OMCP = the MCP-style tool surface through which agents reach the Ontology. Rules: typed inputs/outputs (JSON Schema); every response includes `as_of`, `source_product`, `entity_ids`, `metric_version`; errors are typed; **read tools and propose tools only — there is no execute tool.**

| Tool | Input | Output (abridged) | Used by |
|---|---|---|---|
| `get_metric` | metric_id, grain, filters, period | value, unit, definition_version, as_of | All |
| `list_metrics` | domain? | ids + definitions | Router |
| `get_entity` | type, id | properties, markings-filtered | All |
| `traverse_graph` | seed_ids, hops, edge_types, suppress_hubs | nodes, edges, communities, hub_flags | A, B |
| `get_partner_signals` | partner_id, window | signal series + change-points | C |
| `get_ring_evidence` | ring_id | members, shared attrs, timing stats | A, B |
| `get_causal_chain` | outcome_metric, window | edges w/ effect, CI, refutation status, gate verdict, model_version | Synthesis |
| `run_scenario` | shock spec | propagated deltas + intervals, assumptions | Scenario |
| `get_forecast` | metric_id, horizon | point, interval, driver attribution (sums to 100%) | Synthesis |
| `get_briefing` | date | briefing object | Briefing/UI |
| `search_comms` | partner_id, query | passages (marked untrusted) | C |
| `propose_action` | action_type, params, evidence_refs, propensity_score?, causal_context? | Action Intent (unsigned draft → signing service → PENDING with $e(X)$ logged for AIPW) | Domain agents |
| `get_intent_status` | intent_id | status, approver, ledger_seq | UI/agents |
| `get_dq_status` | product? | freshness, breaches, ER conflicts | Data platform, all |

Auditor Gate contract: `audit(response, tool_outputs) → {ok, untraceable_numbers[], uncited_claims[], causal_overreach[]}`; runtime blocks on `ok=false` and returns a repaired or refusal message. Statutory, regulatory, and legal citations (e.g. `Section 314(b)`, `31 CFR 1010`, `Form 111`) are normalized and exempted from business metric audits.

Versioning: additive changes only within a major; breaking changes require a new tool name + deprecation window; contract tests run in CI against both agents and UI clients.
