# Governed Metric Registry Catalog: Layer 2 (F03)

**Branch**: `004-ontology-metrics` | **Date**: 2026-10-05 | **Spec**: [spec.md](../spec.md)

This catalog defines the canonical, governed enterprise business metrics managed by the Layer 2 Metric Registry (`eios.ontology.metrics`). All metrics execute deterministically against in-memory DuckDB hot state (`:memory:eios_hot_state`).

---

## Metric Catalog

| Metric ID | Name | Domain | Formula / Computation | Grain | Owner Role | Unit | Freshness SLA |
|---|---|---|---|---|---|---|---|
| `net_deposit_volume_usd` | Net Deposit Volume | Financial | `SUM(CASE WHEN type = 'deposit' THEN amount_usd ELSE -amount_usd END)` | `[region, currency]` | `financial_analyst` | `USD` | `PT30S` |
| `ftd_count_28d` | First-Time Deposit Count (28d) | Client | `COUNT(DISTINCT client_id) WHERE ftd_date >= NOW() - INTERVAL 28 DAY` | `[region, partner_id]` | `head_of_partnerships` | `count` | `PT15M` |
| `active_traders_24h` | Active Traders (24h) | Client | `COUNT(DISTINCT client_id) WHERE last_trade_ts >= NOW() - INTERVAL 24 HOUR` | `[region]` | `operations_lead` | `traders` | `PT5M` |
| `partner_commission_total_usd`| Total Commission Paid | Partner | `SUM(commission_amount_usd)` | `[partner_id, tier]` | `head_of_partnerships` | `USD` | `PT15M` |
| `partner_churn_rate` | Partner Churn Rate (90d) | Partner | `COUNT(disengaged_partners) / COUNT(total_tenured_partners)` | `[region, tier]` | `head_of_partnerships` | `ratio` | `PT1H` |
| `partner_value_at_risk_usd` | Partner Value at Risk | Partner | `SUM(commission_run_rate_90d * churn_hazard_score)` | `[partner_id]` | `cfo` | `USD` | `PT1H` |
| `avg_spread_pip` | Average Spread | Operational | `AVG(ask_price - bid_price) / pip_unit` | `[instrument, region]` | `broker_operations` | `pips` | `PT5M` |
| `withdrawal_reversal_ratio` | Withdrawal Reversal Ratio | Compliance | `COUNT(reversed_withdrawals) / COUNT(total_withdrawals)` | `[client_id, region]` | `mlro` | `ratio` | `PT1M` |
| `ring_collusion_score` | Ring Collusion Severity | Compliance | Deterministic graph clique symmetry & turnover ratio $[0.0, 1.0]$ | `[ring_id]` | `aml_investigator` | `score` | `PT1M` |
| `chargeback_rate_bps` | Chargeback Rate (Basis Points)| Financial | `(chargeback_volume_usd / total_deposit_volume_usd) * 10000` | `[payment_method_id]`| `risk_officer` | `bps` | `PT15M` |

---

## Metric Versioning & Immutability Rules
1. **Semantic Versioning**: Each definition begins at `1.0.0`. Additive dimension filters increment the MINOR version (`1.1.0`); any formula or calculation logic change requires a MAJOR version increment (`2.0.0`).
2. **Reproducibility Guarantee**: Queries with explicit `definition_version` will execute the exact historical SQL formula and return historical audit metadata.
3. **Audit Trail**: Every invocation of `get_metric` returns `{metric_id, value, unit, definition_version, as_of, execution_duration_ms}` to allow the Metric Auditor Gate to anchor numeric claims.
