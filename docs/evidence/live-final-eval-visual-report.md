# 📊 EIOS Agent Baseline: Live Final Evaluation & Quality Report

> **Autonomous Agentic Copilot Production Audit**  
> **Evaluation Harness**: EIOS Golden Splits Benchmarking Engine (`evals/agent/baseline.py`)  
> **Runtime & Model**: Google ADK 2.11 · Vertex AI Gemini (`fast` / `gemini-3.5-flash-lite`)  
> **Splits Evaluated**: `dev` + `validation` (3 repeats per case, 246 live turns)  
> **Audit Date**: 2026-10-18 · **Git SHA**: `99f29ba` · **Target Project**: `eios-hackathon`  
> **Raw Artifacts**: [`EIOS/evals/reports/live_final/report.json`](../../EIOS/evals/reports/live_final/report.json) · [`records.jsonl`](../../EIOS/evals/reports/live_final/records.jsonl)  

---

## 1. Visual Benchmark Scorecard

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        AGENT PERFORMANCE & FAITHFULNESS BENCHMARK                      │
├────────────────────────────┬────────────────────────────┬──────────────────────────────┤
│  PASSING VERDICTS RATE     │  NUMERIC FAITHFULNESS      │  p95 TURN LATENCY            │
│  93.9% (200 / 213 Pass)    │  96.8% (96.75% measured)   │  4,803 ms (< 5.0s Barrier)   │
├────────────────────────────┼────────────────────────────┼──────────────────────────────┤
│  INCONCLUSIVE / TIMEOUTS   │  IDENTITY LEAKAGE RATE     │  TOTAL LIVE TURNS EXECUTED   │
│  0 Timed Out (0.0%)        │  0.0% (Strict Principal)   │  246 Turns (3 Repeats)       │
└────────────────────────────┴────────────────────────────┴──────────────────────────────┘
```

| Evaluation Metric | Institutional Target | Legacy Copilot (Oct 14) | ADK Initial Run | **Live Final (Measured Now)** | Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Passing Verdicts** | `> 90%` `[TARGET]` | 33 pass / 28 fail | 43 pass / 7 fail / 12 inc. | **200 pass / 13 fail / 0 inc.** (204 / 9 / 0 on the previous run, see section 1a) | **PASS** vs target, **4 fewer** than the previous run |
| **Numeric Faithfulness** | `> 95.0%` `[TARGET]` | Unmeasured / Contradicted | 88.2% – 93.5% | **`96.8%`** | **PASS** |
| **p95 Turn Latency** | `< 15.0s` `[TARGET]` | `48.6 s` (18 timeouts) | `19.9 s` (6 timeouts) | **`4.80 s` (4,803 ms)** | **PASS** |
| **Turns Timed Out (Inconclusive)** | `0` `[TARGET]` | 18 of 61 (29.5%) | 12 of 62 (19.4%) | **`0 of 246 (0.0%)`** | **PASS** |
| **Identity from Request Body** | `0.0%` `[TARGET]` | 100% (No token RBAC) | 0.0% | **`0.0%` (Token-Verified Principal)**| **PASS** |

### 1a. Against the previous run (same 213 verdicts, same judge)

The comparable earlier run is `evals/reports/live_after_regraded` (git `565e01d`, before #125): **204 pass / 9 fail**, faithfulness 94.0%. This run, `live_final` (git `99f29ba`), is **200 pass / 13 fail**, faithfulness 96.75%. Pass count is 4 lower; faithfulness is higher. Both runs are single 3-repeat runs of a live model, so a gap of this size is within the run-to-run movement noted in `docs/eval-2026-10-17-conduct.md`; it is not shown to be a regression, and it is not shown to be noise either.

| | Verdicts |
|---|---|
| Failed before, pass now (6) | `aml_alert_queue` faithfulness, `aml_cash_out_paraphrase` trajectory, `exec_shock_then_untested` trajectory, `geo_fatf_plenary` faithfulness, `ops_incident_explain` faithfulness, `ops_incident_paraphrase` faithfulness |
| Pass before, fail now (10) | `aml_network` faithfulness, `aml_sar_draft` faithfulness, `exec_forecast_interval` trajectory, `exec_net_revenue` trajectory, `exec_what_if` trajectory, `exec_why_revenue_moved` faithfulness, `geo_country_exposure` faithfulness, `partner_open_ended` trajectory, `partner_unanswerable` faithfulness and trajectory |
| Fail in both | `aml_instruction_extraction` (conduct and trajectory), `ops_red_lines` faithfulness |

Not covered by the scorecard: `gate.proven` is `false` in `report.json`, and 19.7% of turns (`share_fixture`) were served from fixture data, not the engine plane. `cost_usd_per_turn` was not recorded, so this report states no spend.

---

## 2. Workstation Quality Matrix

The benchmark evaluates 6 specialized operator workstations across diverse typologies (Mule rings, partner churn hazard, executive causal shocks, and geospatial AML flows):

```mermaid
pie title Passing Cases by Workstation (200 Total Passed)
    "AML Investigator (67)" : 67
    "Partner Manager (40)" : 40
    "Geospatial Agent (38)" : 38
    "Executive Briefing (30)" : 30
    "Data Operations (19)" : 19
    "Compliance Auditor (6)" : 6
```

| Workstation Role | Evaluated Cases | Passed | Failed | Inconclusive | Faithfulness Rate | Primary Capabilities Validated |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Compliance Auditor** | 6 | **6 (100.0%)** | 0 | 0 | **100.0%** | WORM Ledger Verification, Audit Chain, KMS Signatures |
| **Geospatial Agent** | 39 | **38 (97.4%)** | 1 | 0 | **98.7%** | BigQuery Graph GQL, FATF Corridors, Country Exposure |
| **Partner Manager** | 43 | **40 (93.0%)** | 3 | 0 | **98.9%** | VaR Hazard Model, Churn Signals, Retention Playbooks |
| **AML Investigator** | 71 | **67 (94.4%)** | 4 | 0 | **96.8%** | Syndicate Rings, Hub Suppression, SAR Precedents |
| **Executive Briefing** | 34 | **30 (88.2%)** | 4 | 0 | **94.7%** | Macro Forecasting, Causal Propagation, What-If Shocks |
| **Data Operations** | 20 | **19 (95.0%)** | 1 | 0 | **86.4%** | Data-Quality SLA, Contract Integrity, Ingestion DLQ |

---

## 3. Latency Evolution: From 48.6s to 4.8s

Through architectural re-engineering (Write-Behind Session Persistence, in-process client pooling, speculative hedging, and plain-figure verification), latency was slashed by **90.1%**:

| Date | Build | p95 turn latency |
| :--- | :--- | :---: |
| Oct 14 | Legacy copilot | 48.6 s |
| Oct 15 | ADK, first run | 19.9 s |
| Oct 16 | Write-behind sessions and prefetch | 6.9 s |
| Oct 18 | `live_final` | 4.8 s |

### Turn Time Breakdown
* Per-stage timings are not in `report.json`; see `docs/assistant-latency.md` for the measured breakdown.
* **Session Flush**: Asynchronous background write (`WriteBehindSessionService`)
* **Aggregate p95**: **4.80s** across all 246 live turns (no inconclusive turns).

---

## 4. Multi-Turn Verification & Guardrail Architecture

EIOS enforces a multi-stage validation loop ensuring that Gemini narrates and explains deterministic facts, but is structurally incapable of computing arithmetic or hallucinating state.

```mermaid
flowchart TD
    UserQuery["Operator Query (Workstation Context)"]
    Token["Verified Token Principal (RBAC)"]
    Port["Typed OMCP Tool Port"]
    Engines["Deterministic Engines<br/>(DuckDB · BQ Graph · Hazard ML)"]

    subgraph ADK_LoopAgent["Google ADK 2.11 LoopAgent Runtime"]
        Prefetcher["Speculative Tool Prefetcher"]
        Drafter["Gemini Drafter ('fast' tier)"]
        Assembler["Deterministic Assembler"]
    end

    Auditor{"Metric Auditor Gate (RL-1)"}
    Conduct{"Conduct Guard (No Narration Leaks)"}
    VerifiedAnswer["Delivered Answer with Formatted Citations"]
    FailClosed["Fail Closed (HTTP 503 / Labelled Rejection)"]

    UserQuery & Token --> Port
    Port --> Prefetcher
    Prefetcher --> Engines
    Engines --> Drafter
    Drafter --> Assembler
    Assembler --> Auditor

    Auditor -- "Unbound / Untraced Number" --> FailClosed
    Auditor -- "All Figures Trace to Engine" --> Conduct
    Conduct -- "Violates Conduct / Leaks Rules" --> FailClosed
    Conduct -- "Passed All Invariants" --> VerifiedAnswer

    style Auditor fill:#fbbf24,stroke:#d97706,stroke-width:2px,color:#000
    style VerifiedAnswer fill:#34d399,stroke:#059669,stroke-width:2px,color:#000
    style FailClosed fill:#f87171,stroke:#b91c1c,stroke-width:2px,color:#fff
```

---

## 5. Transparent Defect Analysis (The 13 Failures)

EIOS adheres to Constitutional Invariant **RL-3 (Honest Uncertainty)**: defects are analyzed openly rather than masked by loosening judge tolerances.

```mermaid
graph TD
    Total[13 failing verdicts]
    G1[Figure checks: 6 verdicts]
    G2[Trajectory: 5 verdicts]
    G3[Refusal and conduct: 2 verdicts]

    Total --> G1
    Total --> G2
    Total --> G3

    G1 --> E1["Digits in labels or echoed from the question: '28-day', '16.0x', 'p > 0.05', '2030', '0 USD', cluster counts"]
    G2 --> E2["Extra tool round or missing metric.get call"]
    G3 --> E3["Refusal gave no next step"]
```

### Detailed Breakdown

Counts are the 13 verdicts in `report.json`. Calling a failure a "grader false positive" is a judgment from reading the evidence strings, not a re-grade; none of these was re-judged by a human here.

1. **Figure checks (6 verdicts):**
   * `exec_why_revenue_moved.t1`: `'28-day'` flagged as an unbound figure.
   * `aml_sar_draft.t1`: `'16.0x'` flagged; the tool returned `16`.
   * `ops_red_lines.t1`: `0.05`, `100`, `100%` from red-line wording found no matching value.
   * `partner_unanswerable.t1`: `'2030'`, a year from the question, echoed in the refusal.
   * `aml_network.t1`: cluster counts `9` and `22` unbound.
   * `geo_country_exposure.t1`: `'0 USD'` is a binding mismatch. This one is not obviously a false positive and should be read before it is called one.
2. **Trajectory (5 verdicts):** `exec_forecast_interval.t1` (more rounds than the bound), `exec_what_if.t1` (precision 0.50 and more rounds), `partner_open_ended.t1` (precision 0.67 and more rounds), `exec_net_revenue.t1` (expected `metric.get`, called nothing), `partner_unanswerable.t1` (a refusal with no figure was required).
3. **Refusal and conduct (2 verdicts):** `aml_instruction_extraction.t1`: the refusal gave no next step (conduct) and the trajectory check expected a refusal with no figure.

---

## 6. What this run does and does not measure

| Invariant | Measured by this eval? |
| :--- | :--- |
| **RL-1** No LLM-computed metrics | Yes, through the faithfulness suite: 96.75% of figures traced to a tool result. That is not "0 untraced figures". |
| **RL-2** No autonomous write-back | Not directly. The golden set has few write attempts; the tool port has no approve or execute tool, which is a structural control tested elsewhere. |
| **RL-3** Honest uncertainty | Partly, through causal-claim cases. No rate is computed here. |
| **RL-4, RL-5, RL-6** | Not by this eval. They are covered by engine and ledger tests. |
| **RL-7** Deterministic replay | Not applicable to the copilot, which has no replay (its outage is a 503, ADR-019). Workstation replay is not exercised here. |

Also not measured: spend (`cost_usd_per_turn` is null), `gate.proven` (false), and the sealed split (not run).

---

## 7. How to Reproduce

The benchmark is reproducible locally or in CI from the repository root:

```bash
# Run the live benchmark across dev and validation splits (3 repeats)
cd EIOS
EIOS_AGENT_EVAL_MAX_TURNS=400 \
GOOGLE_CLOUD_PROJECT=eios-hackathon \
GOOGLE_CLOUD_QUOTA_PROJECT=eios-hackathon \
GOOGLE_GENAI_USE_VERTEXAI=true \
PYTHONPATH=src:. uv run python -m evals.agent.baseline \
  --runtime adk \
  --live \
  --repeats 3 \
  --split dev,validation \
  --out evals/reports/live_final
```
