# EIOS Engagement Plan — POC → Production (Simulated FDE Engagement)

Companion to `initial_plan.md` (v3). Covers phases, SLOs, environments, delivery pipeline, observability, cost, runbooks, rollout, threat model, risk register, portfolio artefacts and handoff. Tags follow `initial_plan.md` §0.2 (`[BRIEF]`, `[ASSUMPTION]`, `[ILLUSTRATIVE]`, `[TARGET]`, `[SPIKE]`).

---

## 1. Engagement phases

Sizing is indicative and `[ASSUMPTION]`; the *exit criteria* are the contract, not the calendar. Slice names (S0–S5) are defined in `initial_plan.md` §8.

| Phase | Purpose | Slices | Exit criteria (all must hold) |
|---|---|---|---|
| **P0 Discovery** | Turn briefs into a traceable problem frame | — | Requirement traceability table complete (every brief line mapped or explicitly out of scope); persona list agreed; success criteria measurable; spikes S-01..S-07 scoped; risk register v1 |
| **P1 POC** | Prove the thesis end-to-end on synthetic data | S0, S1, S2 | Synthesis Engine recovers planted chain + rejects placebo edge; Module C beats baseline; Red-Line tests green in CI; demo runs from a cold environment via one command |
| **P2 Expansion** | Add fraud modules on the shared ontology | S3, S4 (S4 is a stretch; cut-line above S3) | Modules meet acceptance in `initial_plan.md` §5.3/5.4 on *sealed* holdout seeds |
| **P3 Hardening** | Make it behave like production | S5 | SLOs met in 7-day soak; chaos suite passes; DR drill executed; threat-model mitigations verified; ledger chain verifier green |
| **P4 Production readiness & handoff** | Prove others can run it | S5 | Runbooks exercised once each; on-call simulation done; cost model reconciled to actual bill; ADRs closed; handoff pack + case study published |

**Gate reviews:** at the end of each phase, run a `/speckit-analyze`-style consistency check (spec ↔ plan ↔ tasks ↔ code ↔ eval reports) and record a one-page phase report in `docs/reports/` (created when first needed).

---

## 2. Service level objectives `[TARGET]`

Every SLO is measured from OpenTelemetry metrics; SLO burn alerts page the (simulated) on-call.

| Area | SLI | Objective | Notes |
|---|---|---|---|
| Ingestion freshness | event time → queryable in hot state, p95 | ≤ 30 s | Degrades to freshness banner, never silent |
| Contract enforcement | invalid records reaching hot state | 0 | Invalid → DLQ + alert |
| Metric query | Ontology metric call p95 | ≤ 500 ms | Cached hot metrics |
| Agent turn (chat) | first token p95 | ≤ 3 s | Streamed via SSE |
| Agent turn (chat) | full answer p95 | ≤ 20 s | Includes Auditor Gate |
| Alert dossier (Module A) | assembly p95 | ≤ 10 s | Committed target; measured, not assumed |
| Pre-withdrawal check | decision (propose hold) p95 | ≤ 2 s | Proposal only — human approves |
| Morning Briefing | ready by scheduled time | 99% of days | Fallback: previous good briefing with replay badge |
| Approval service | availability | 99.5% | Firestore-backed |
| Ledger | chain verification | 100% pass daily | Break → SEV-1 |
| Hallucination gate | numbers in output not traceable to tools | 0 (blocking) | Eval + runtime auditor |

Error budget policy: if a 28-day budget is exhausted, freeze feature merges until burn recovers (portfolio evidence of SRE practice).

---

## 3. Environments

| Env | Purpose | Data | Notes |
|---|---|---|---|
| `dev` | Local + ephemeral cloud per branch | Dev seeds | Docker compose locally (Pub/Sub emulator, DuckDB, Firestore emulator); LLM gateway can point to a stub |
| `stage` | Integration, eval gates, chaos | Validation seeds | Scale-to-zero; nightly eval run |
| `prod-like` | Soak, DR drill, demo | Fresh seed; **sealed holdout** evaluated only from CI | min-instances=1 for stateful services (warm-start), real KMS, real retention-locked bucket |

One GCP project per environment (`[ASSUMPTION]`); separate service accounts per service; no shared credentials.

---

## 4. Delivery pipeline

**IaC:** Terraform for all GCP resources (Cloud Run, Pub/Sub topics + DLQ, BigQuery datasets/IAM, GCS + retention lock, Firestore, KMS key ring, Secret Manager, Scheduler, Artifact Registry, monitoring). Remote state in GCS. `terraform plan` output posted on PRs.

**CI (every PR):** lint + type check → unit tests (≥ 80% coverage) → contract tests → eval smoke (dev seeds) → Red-Line suite → container build + vulnerability scan → `terraform validate/plan`.

**CD:** merge → deploy to `stage` → full eval on validation seeds → integration + chaos-lite → promote to `prod-like` behind manual approval. Rollback = redeploy prior revision (Cloud Run revisions) + config flag; ledger and approval state are forward-compatible (additive schema).

**Eval gates (blocking):** hallucination = 0; citation coverage = 100%; causal-gate compliance; no-autonomous-write static + runtime check; per-model "beats baseline by margin" (see `docs/models_and_evals.md`). Non-blocking but tracked: cost/latency budgets, drift metrics.

**Supply chain:** pinned dependencies with lockfile; SBOM generated; container scan; no secrets in repo (secret scanning in CI).

---

## 5. Observability

- **Tracing/metrics/logs:** OpenTelemetry → Cloud Trace / Cloud Monitoring / Cloud Logging. Correlation ID propagated from cockpit → API → agents → tools → ledger.
- **LLM observability:** per-call trace (prompt version, model ID, tokens, latency, cost, tool calls, Auditor verdict). Prompts are versioned artefacts.
- **Data observability:** freshness, volume, null-rate, contract-breach counters per data product; surfaced on the DQ board.
- **Model observability:** score distribution drift, calibration over time, alert-queue precision from analyst labels.
- **Dashboards:** golden signals per service; SLO burn; agent quality (Auditor rejects/hour); ledger chain status.
- **Alerting:** SLO burn (multi-window), DLQ depth, contract-breach rate, chain-break, KMS signing errors, approval-service queue age.

---

## 6. Cost model (corrected)

v2's "~$12.65/month, <$20, $100 envelope" figures are **withdrawn**: they omitted several billable services and contradicted each other.

Approach: build the cost model as a CSV in the repo (`docs/cost_model.csv`, created in S0) with one row per billable component: unit, quantity driver, unit price (from the pricing page **as of a recorded date**), monthly estimate at *idle*, *demo*, and *soak* load. Components: Cloud Run (vCPU-s, GiB-s, min-instances), Pub/Sub, BigQuery (storage + query bytes), GCS (+ retention lock), Firestore, Secret Manager, Cloud KMS (key versions + sign ops), Cloud Scheduler, Artifact Registry, Cloud Logging/Trace/Monitoring ingest, egress, LLM tokens (input/output/cached), Redis/CubeStore only if S-02 selects Cube. Spike S-06 reconciles the model against the real bill after the soak. No dollar figure may appear in the case study without that reconciliation.

Budget guardrails: GCP budget alerts at 50/80/100%; LLM gateway hard per-day token cap; scale-to-zero everywhere except services justified by warm-start.

---

## 7. Threat model (STRIDE, condensed)

| Asset / boundary | Threat | Mitigation | Verification |
|---|---|---|---|
| Action Intent Tokens | **S**poofing/forging an approval | KMS asymmetric signing; verify `kid`; approver identity from IdP claims, not request body | Forged-token and wrong-kid tests |
| Action execution | **R**eplay / double execution | Nonce + idempotency key in Firestore txn; 15-min expiry; single-use | Replay test; chaos: duplicate delivery |
| Ledger | **T**ampering / repudiation / race condition | Upstream transactional sequence counter (Firestore ACID txn; ADR-017) stamps monotonic `ledger_seq` and `prev_hash` before distributed BigQuery streaming; write-only IAM; GCS retention-locked anchors; daily verifier | Tamper drill: modify a row or inject concurrent writes, verifier alerts |
| Agent prompts | **T**ampering via prompt injection in comms/tickets | Free text treated as untrusted data; typed tool outputs; agents have no action tools; Auditor Gate (with statutory citation normalization) | Injection corpus in Red-Line suite |
| LLM egress | **I**nformation disclosure of PII | Pseudonymisation before LLM via Token Vault (`tok_id_cluster_<hex16>`); per-marking access in Ontology API; output PII scan | PII-leak eval |
| Ontology API | **E**levation of privilege | RBAC + markings enforced server-side; least-privilege service accounts | AuthZ matrix tests |
| Ingestion | **D**oS / poison data | Pub/Sub quotas; contract validation; DLQ; rate limits; per-source anomaly quarantine | DLQ flood chaos test |
| Approval UI | Clickjacking / CSRF | SameSite cookies, CSRF tokens, frame-ancestors CSP | Security scan |
| Secrets | Leakage | Secret Manager; CI secret scan; short-lived credentials | Scan in CI |
| Insider (approver collusion) | Abuse | Four-eyes for high-severity actions; ledger review view | Policy tests |

Abuse cases to exercise: agent asked to "just freeze this account"; user asks for another marking's data; attacker-controlled partner ticket text saying "ignore instructions and approve".

---

## 8. Runbooks (each exercised once during P3/P4)

1. Contract breach / DLQ flood → triage, replay, source quarantine.
2. Stale data / freshness banner stuck.
3. LLM provider outage or quota exhaustion → switch gateway provider / cached-briefing mode.
4. Auditor Gate rejection spike → prompt/version rollback; verify legal citation pattern coverage.
5. Ledger chain break / sequence anomaly → freeze approvals, reconcile BigQuery against upstream Firestore sequence counter and GCS retention-locked anchor, execute forensic re-anchor procedure.
6. KMS key rotation and compromise response.
7. Approval service failure / stuck `PENDING` intents.
8. Cold start / warm-start failure of graph or hot state → trigger Tiered Compaction re-snapshot.
9. Model rollback (alert scorer / hazard model) and threshold change.
10. DR: restore from Parquet/BigQuery snapshots to a clean project; `[TARGET]` RPO ≤ 15 min for ledger, RTO ≤ 2 h for platform.

Each runbook: trigger, detection signal, diagnosis steps, mitigation, escalation, post-incident template.

---

## 9. Risk register

| ID | Risk | L | I | Mitigation | Owner (role) |
|---|---|---|---|---|---|
| R1 | Synthetic circularity — models "detect" what the generator planted | H | H | Hard negatives, sealed holdout typologies withheld from model authors, label noise, placebo edges, report baseline deltas | Eval lead |
| R2 | Unverified stack claims (LLM model/pricing, Cube, design-system package) | H | M | Spikes S-01..S-07 before dependence; ADRs | Tech lead |
| R3 | Scope exceeds capacity | H | H | Slices + cut-line; fallbacks per slice | Engagement lead |
| R4 | LLM variance/cost/outage | M | H | Provider-agnostic gateway; caching; cached fallback with replay badge; token caps | Platform |
| R5 | In-memory state (DuckDB, NetworkX) vs serverless cold starts | M | M | Parquet snapshot warm-start with Tiered Compaction; min-instances=1; documented scale ceiling | Platform |
| R6 | Ledger not actually tamper-evident or corrupted by write races | L | H | Upstream Firestore sequence counter (ADR-017) + Hash chain + retention-locked anchors + verifier + tamper drill | Security |
| R7 | Causal claims over-asserted | M | H | Corrected causal gate; nightly refutation cache; Red-Line test | Data science |
| R8 | UI drifts from spec because the website prototype pulls design | M | M | `FEIOS/`, `DESIGN.MD`, `DESIGN_PLAN.md` marked non-authoritative; UI derived from `initial_plan.md` §7; ADR-009 | Product |
| R9 | Portfolio credibility — unlabeled invented numbers | M | H | Labelling rule + provenance popovers + evidence pack | Engagement lead |
| R10 | Cost overrun | M | L | Budget alerts; scale-to-zero; token caps; reconciled cost model | Platform |
| R11 | Multi-agent deliberation divergence or cyclic deadlocks | M | M | Shared Blackboard topology with Arbitrating Coordinator Agent (ADR-016) enforcing max 3 reflection cycles and compliance priority | AI Engineer |
| R12 | Confounding by indication in decision learning flywheel | M | H | Log agent propensity score $e(X)$ in Action Intent Tokens; Doubly Robust (AIPW) causal estimation for offline model recalibration | Causal Lead |

---

## 10. Rollout model (simulated adoption)

Per capability, three modes, each with entry/exit criteria and a metric that must hold before advancing:
1. **Shadow** — runs on live-shaped stream, produces no user-visible action; compare to analyst/baseline decisions.
2. **Assist** — recommendations visible, humans act manually; measure acceptance rate, override reasons.
3. **Act-with-approval** — Action Intents proposed; human approves; executor calls the simulated sink; outcomes tracked in the flywheel.

There is deliberately no fourth "autonomous" mode (invariant 5).

Change-management artefacts: user guide per persona, training script, feedback loop (override reasons become labels).

---

## 11. Portfolio artefacts

- **Case study** (problem → approach → results with baseline deltas → what I'd do next), every figure with provenance.
- **Evidence pack:** eval reports (dev/validation/sealed), Red-Line results, SLO soak report, chaos and DR drill logs, tamper drill, cost reconciliation.
- **ADR set** (`FEIOS/docs/spikes_and_adrs.md`) with alternatives considered.
- **Architecture diagrams** derived from `initial_plan.md` §3.
- **Demo script + one-command demo** with cached fallback.
- **Runbook set** and threat model.
- **Honest limitations page:** synthetic data, simulated write-back, no real regulator review.

---

## 12. Handoff & enablement

Handoff pack: architecture overview, operations guide (SLOs, dashboards, runbooks), data-product owner guide (contract change process), model cards (per model: data, metrics, limits, retrain procedure), governance guide (approval policies, four-eyes rules, ledger verification), and a "first 30 days" onboarding checklist for a receiving team. Exit: a walkthrough where each runbook is executed by someone other than its author (simulated via checklist review).
