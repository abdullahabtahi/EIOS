# Models, Baselines & Evaluation Harness

Companion to `initial_plan.md` §5 and §9. Every model has a **baseline it must beat**; results are reported as deltas on **sealed holdout** seeds. Tags per `initial_plan.md` §0.2. Numeric targets here are `[TARGET]` commitments to measure, not claims.

---

## 1. Evaluation principles

1. **Data splits by seed:** `dev` seeds (used freely while building), `validation` seeds (model selection/CI), `sealed` seeds (generated from a spec the model authors have not seen; evaluated only by CI on release candidates). Touching sealed results outside CI invalidates the run.
2. **Baselines first:** implement the naive baseline before the model. Ship a model only if it beats the baseline by a pre-registered margin.
3. **Break circularity:** hard negatives, label noise (`[ASSUMPTION]` 3–8% flipped analyst labels), planted **placebo** causal edges (true effect = 0), and **unplanted** holdout typologies.
4. **Report uncertainty:** bootstrap CIs across seeds (≥ 10 validation seeds; ≥ 5 sealed).
5. **Everything reproducible:** every eval report records generator seed(s), git SHA, model version, prompt version, dataset hash.

---

## 2. Module A — Client Fraud Sentinel / AML (source: `docs/brief/monitoring.md`)

| Component | Method | Baseline to beat | Metrics & targets |
|---|---|---|---|
| Behavioural anomaly | Peer-group baselines (segment × tenure × product) + per-customer robust z-score / isolation forest | Static threshold rules (deposit > X, velocity > Y) | Recall at fixed alert volume; hard-negative FPR (legit high-volume traders) `[TARGET]` ≥ 30% relative reduction vs baseline |
| Alert scorer | LightGBM on anomaly scores, KYC recency ("activity within 72 h of KYC approval" `[BRIEF]`), deposit/withdrawal ratio, graph features, alert history; trained on analyst labels | Rules-engine score | precision@50, PR-AUC; queue reduction 2,000 → ≤ 50 cases (`[BRIEF]` figures) retaining ≥ 90% of planted true positives `[TARGET]` |
| Graph ring detector | Shared device/IP/payment-method/timing edges; **hub suppression** (drop nodes above a robust degree quantile or in a shared-context list); connected components + Louvain | Naive shared-IP components | Ring recall; **hub false-merge rate** (must be lower than naive) |
| Round-trip typology | Sequence pattern: deposit → short-hold micro-P&L trades → withdrawal within window (`$500 → 10 min → $0.01 → withdraw` `[BRIEF]`) | Rule "deposit and withdraw within N minutes" | Recall on planted + sealed variants; FPR on hard negatives |
| Novel typology discovery | Unsupervised clustering / novelty scores on residuals | None (qualitative + sealed-typology hit rate) | Sealed-holdout typology surfaced in top-k novelty list `[TARGET]` ≥ 1 of 2 |
| Analyst feedback loop | Batch retraining from decisions | Frozen model | Uplift in precision@50 after simulated feedback batches |
| SAR composer | Template + retrieved cited evidence; LLM only for narrative from tool outputs | Human checklist | Completeness checklist 100%; citation coverage 100%; Auditor pass |
| Pre-withdrawal check | Risk score at withdrawal request → `HoldWithdrawal` **proposal** | Rules | Decision latency p95 ≤ 2 s; hold precision on planted round-trips |

---

## 3. Module B — Partner & Affiliate Fraud Sentinel (source: `docs/brief/fraud`)

| Component | Method | Baseline | Metrics & targets |
|---|---|---|---|
| Opposite/mirror trading | Pair-level features: temporal overlap, direction anti-correlation, size symmetry, net P&L ≈ 0 while commission accrues | "Same instrument, opposite direction within N s" | Precision/recall on planted pairs; FPR on hard negatives (real hedgers, IB portfolios) |
| Ring & master attribution | Referral-tree traversal + shared-attribute links; 3-layer attribution to master partner | Direct-parent attribution only | Master-partner recovery rate; ring-shape recovery |
| Bonus abuse | Sequence scorer: deposit → minimal activity → withdrawal | Rule "withdraw within N h of bonus credit" | PR-AUC |
| Client quality score | Composite of retention, activity, bonus dependence, loss/profit | Deposit-only ranking | Rank correlation with 90-day realised value |
| Client recycling | Entity match on identity/device/payment attrs across partners | Exact-key match only | Recall on planted recycled identities; ER precision |
| Traffic/bot fraud & impossible conversion | Beta-binomial / z-score of click→signup→deposit conversion vs peers; burst timing | Fixed conversion cap | Planted anomalous partners recovered (brief's "12 partners with impossible conversion rates" is `[BRIEF]`; planted counts are generator-defined `[ILLUSTRATIVE]`) |
| Emerging-pattern miner | Unsupervised on residual cases | None | Sealed typology hit-rate |

Dossier requirements: evidence list with IDs, confidence, relationship context (partner tenure/value), proposed Action Intent (`ClawbackCommission`, `SuspendPartner`), never auto-executed.

---

## 4. Module C — Partner Churn Radar (source: `docs/brief/churn`)

| Component | Method | Baseline | Metrics & targets |
|---|---|---|---|
| Hazard model | Discrete-time hazard (logistic on person-period data) or Cox PH over the five signal families; window configurable (30/60/90 d) | "No login for N days" | AUROC, PR-AUC, **calibration (Brier, reliability)**, lead time at fixed precision; `[TARGET]` PR-AUC ≥ baseline + 0.10, median lead time ≥ baseline + 7 days |
| Dip vs disengagement | Change-point (CUSUM / BOCPD) vs seasonal baseline | Fixed drop threshold | FPR on seasonal-dip hard negatives |
| Cohort detector | Region/segment aggregation + permutation/Z-test for simultaneous decline | Per-partner alerts only | Planted cohort detected; false-cohort rate |
| Prioritisation | Priority = P(disengage in window) × value at risk (commission trend / client LTV) | Risk-only ranking | Top-k value captured |
| Comms signal | Poaching/competitor-language classifier over tickets/emails (embedding + logistic head; LLM only to help create the labelled set) | Keyword list | F1 on labelled synthetic set incl. sarcasm/negation hard cases |
| Intervention uplift | T-learner uplift or contextual bandit over playbooks with simulated outcomes | Random / rule-based playbook | Uplift@k; regret in simulation |
| Threshold trade-off | Sweep report of sensitivity vs specificity | — | Report produced per brief |

---

## 5. Executive Synthesis Engine (source: `docs/brief/data.md`)

| Component | Method | Baseline | Metrics & targets |
|---|---|---|---|
| Causal DAG | Authored; each edge has rationale + expected sign; structural equations fitted in batch | Correlation-only ranking | Planted chain (Competitive → Partner → Client → Financial) ordered correctly; **placebo edges rejected** |
| Causal-evidence gate | Effect CI excludes 0; **placebo-treatment refuter effect ≈ 0 (p > 0.05 on the placebo is the pass)**; random-common-cause and data-subset refuters stable; confidence ≥ 0.80; otherwise emit "correlation detected; insufficient evidence for causation" | — | 100% compliance on gate tests (blocking) |
| Forecast | Seasonal-naive vs gradient-boosted/regression with leading indicators; prediction intervals | Seasonal-naive | MASE / MAPE on holdout; interval coverage within ±5 pts of nominal |
| Driver attribution | Counterfactual decomposition normalised to 100% (brief's 40/35/25 example `[BRIEF]` is illustrative of format) | Equal split | Sum = 100% exactly; rank agreement with generator ground-truth drivers |
| Scenario simulation | Shock injection on cached SCM → propagated deltas + intervals | Static sensitivity table | Sign and rough magnitude vs generator's true intervention effect |
| Recommendation composer | Templates + tool outputs; schema (impact range, trade-offs, confidence, evidence, linked Action Type) | — | Schema completeness 100%; Auditor pass |
| Morning Briefing | Scheduled synthesis → ranked insights | Static KPI email | Golden-briefing match on planted overnight events; on-time SLO |

---

## 6. Agent & LLM evaluation (cross-cutting)

**Red-Line tests (blocking in CI):**

| ID | Test | Pass |
|---|---|---|
| RL-1 | Metric hallucination: adversarial prompts asking for numbers not in tools | 0 untraceable numbers in output |
| RL-2 | Citation coverage: every assertion carries an Ontology entity ID or data product + as-of | 100% |
| RL-3 | Causal-gate compliance: correlational-only edges never asserted causally | 100% |
| RL-4 | No autonomous write: agents have no action tool; static import check + runtime deny | 0 direct writes |
| RL-5 | PII leakage: pseudonymised fields never appear in LLM prompts/outputs | 0 |
| RL-6 | Prompt-injection corpus in tickets/comms | 0 successful injections (no tool misuse, no intent emitted) |
| RL-7 | Action Intents signed, single-use, expiring | Forgery/replay tests all rejected |

**Agent quality:**
- **Trajectory evals:** expected tool calls/order per golden task; penalise redundant calls.
- **Multi-turn dialogues:** ≥ 10 golden dialogues incl. follow-ups, assumption challenges ("what if the competitor reverses?"), and unanswerable questions (must say insufficient data).
- **Router accuracy:** correct specialist ≥ 95% on labelled queries `[TARGET]`.
- **LLM-as-judge** only for style/clarity rubrics, calibrated against a human-labelled subset; never for numeric correctness (that is deterministic).
- **Cost & latency budgets** per turn tracked and gated at regression thresholds.

**Non-functional:** load (ingest 10× demo rate), chaos (kill worker, DLQ flood, LLM outage → cached fallback, duplicate Pub/Sub delivery), cold-start and warm-start correctness, DR restore.

---

## 7. Harness structure

```
evals/
  golden/            # golden Q&A, briefings, dialogues (versioned)
  suites/            # per-capability suites (a, b, c, synth, redlines, nfr)
  fixtures/          # generator seeds + dataset hashes
  reports/           # machine-readable + rendered reports (per run)
  cli.py             # `eval run --suite ... --seeds dev|validation|sealed`
```

CI: smoke (dev seeds) on every PR; validation on merge; sealed on release candidate only. Reports are portfolio evidence.

Model cards (per model): intended use, data, metrics vs baseline, calibration, known failure modes, retrain procedure, rollback.
