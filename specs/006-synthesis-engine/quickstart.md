# Quickstart: Executive Synthesis Engine (F05)

**Feature**: `006-synthesis-engine` | **Date**: 2026-10-06  
**Status**: Completed  
**References**: `specs/006-synthesis-engine/spec.md`, `specs/006-synthesis-engine/research.md`.

---

## 1. Fit & Cache the Structural Causal Model (SCM)

Run the offline nightly refutation engine to fit structural equations over historical domain metrics, execute placebo refutations, and generate the certified `SCMCache`:

```bash
uv run python -m eios.synthesis.scm_runner --fit-cache --output evals/reports/synthesis_scm_cache.json
```

**Output**:
```text
[SCM] Fitting 4-domain causal DAG across historical metrics...
[SCM] Testing edge: competitor_payout_rate -> partner_churn_rate (weight: +0.45, 95% CI: [0.38, 0.52])
      Refutation: Placebo p-val = 0.842 (>0.05 PASS) | Random Common Cause delta = +3.2% (PASS) | Gate = PASS
[SCM] Testing edge: partner_churn_rate -> ftd_count_28d (weight: -340.0, 95% CI: [-410.0, -270.0])
      Refutation: Placebo p-val = 0.719 (>0.05 PASS) | Random Common Cause delta = -1.8% (PASS) | Gate = PASS
[SCM] Testing edge: ftd_count_28d -> net_deposit_volume_usd (weight: +45.0, 95% CI: [38.5, 51.5])
      Refutation: Placebo p-val = 0.912 (>0.05 PASS) | Random Common Cause delta = +2.4% (PASS) | Gate = PASS
[SCM] Testing planted placebo: avg_spread_pip -> partner_churn_rate (true effect = 0.0)
      Refutation: Placebo p-val = 0.012 (<= 0.05 REJECTED) | Gate = FAIL (Excluded from propagation)
[SCM] Cached 3 certified edges to evals/reports/synthesis_scm_cache.json in 1.42s
```

---

## 2. Inspect the Causal Chain via OMCP

Retrieve the certified causal DAG and gate verification status:

```python
from eios.ontology.omcp.server import OMCPServer
from eios.ingestion.hot_state import HotStateEngine

server = OMCPServer(hot_state=HotStateEngine())
response = server.call_tool(
    "get_causal_chain",
    {"outcome_metric": "net_deposit_volume_usd", "window_days": 28},
    caller_role="Executive"
)
print(response)
```

---

## 3. Generate a 28-Day Forecast with 100% Additive Attribution

Compute multi-step forecast beating the seasonal-naive benchmark ($\text{MASE} < 1.0$) with strictly $100.0\%$ additive driver attribution:

```python
forecast = server.call_tool(
    "get_forecast",
    {"metric_id": "net_deposit_volume_usd", "horizon": 28},
    caller_role="CFO"
)

print(f"Point Estimate: ${forecast['point_estimate']:,.2f}")
print(f"95% Interval: [${forecast['ci_lower']:,.2f}, ${forecast['ci_upper']:,.2f}]")
print("Driver Attribution:")
for metric, pct in forecast["driver_attribution"].items():
    print(f"  - {metric}: {pct:.1f}%")
```

---

## 4. Run a Parametric Scenario Shock Simulation

Inject an exogenous shock (e.g., competitor increases affiliate payout by 15 bps) and simulate downstream impacts in $< 200\text{ms}$:

```python
simulation = server.call_tool(
    "run_scenario",
    {
        "shock_spec": {
            "scenario_name": "Competitor Payout Aggression",
            "shocks": {"competitor_payout_rate": 0.15},
            "duration_days": 28
        }
    },
    caller_role="Executive"
)

for metric, delta in simulation["propagated_deltas"].items():
    ci = simulation["confidence_intervals"][metric]
    print(f"{metric}: {delta:+.2f} (95% CI: [{ci[0]:.2f}, {ci[1]:.2f}])")
```

---

## 5. Fetch Daily Morning Briefing with Fallback Replay

Retrieve the executive briefing object with verified citations and interactive follow-ups:

```python
briefing = server.call_tool(
    "get_briefing",
    {"date": "2026-10-06"},
    caller_role="Executive"
)

print(f"Briefing ID: {briefing['briefing_id']}")
for item in briefing["insights"]:
    print(f"Insight: {item['title']} - {item['summary']}")
```

---

## 6. Propose a Governed Recommendation with AIPW Propensity Logging

Draft a KMS-signed Action Intent Token recording the agent's proposal propensity score $e(X)$:

```python
recommendation = server.call_tool(
    "propose_action",
    {
        "action_type": "AdjustPartnerTier",
        "params": {"partner_id": "PARTNER-1029", "proposed_tier": "TIER_1_RETAIN"},
        "evidence_refs": ["partner_360:PARTNER-1029", "metric:partner_churn_rate:v1.0.0"],
        "propensity_score": 0.85,
        "causal_context": {"churn_hazard": 0.72, "value_at_risk_usd": 45000.0}
    },
    caller_role="DomainAgent"
)

print(f"Intent ID: {recommendation['intent_id']}")
print(f"Status: {recommendation['status']}")
```
