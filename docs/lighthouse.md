# Lighthouse: financial-crime alert to disposition

**Status**: DRAFT for your review, nothing measured yet. **Updated**: 2026-10-13. **Client persona**: Deriv (`docs/brief/monitoring.md`). **Companions**: `data-strategy.md`, `adk.md`, `synthetic_data_strategy.md`, `financial_geospatial.md` (v3).
**Tags**: `[BRIEF]` cited from `docs/brief/*`, `[ASSUMPTION]` a number we chose and must validate, `[TARGET]` a commitment we will measure, `[MEASURED]` reserved for results we produce. Nothing here is `[MEASURED]` yet.

> One workflow, measured end to end, before breadth. The platform stays domain-agnostic (`data-strategy.md`); this is the first thing that must work on it, and the proof that the platform is worth extending.

---

## 1. Hypothesis

An investigator who starts from an assembled, cited dossier instead of five systems can reach a justified disposition and a reviewable SAR draft materially faster, with no unsupported figure, and every consequential action still needs two distinct signed human approvals.

## 2. Why this workflow

- `[BRIEF monitoring.md]`: about 2,000 alerts a week, about 95% closed as false positives, context pulled from 5+ systems, SAR/STR filing under tight deadlines.
- `[BRIEF monitoring.md]` asks for "2,000 alerts into 50 high-confidence cases with full investigation packs".
- It exercises every constitutional invariant at once: RL-1 (no LLM metrics), RL-2 (no autonomous write-back), RL-3 (correlation vs causal), RL-4 (hub suppression), RL-5 (ledger), RL-7 (labelled replay).

**In scope**: alert triage, evidence assembly, disposition recommendation with uncertainty, SAR draft, a governed hold staged for four-eyes approval, ledger proof.
**Out of scope for the lighthouse**: training new detection models, case management, sanctions screening, the map, the other packs.

## 3. People and decision rights

| Role | Does | Never does |
|---|---|---|
| Investigator | Reviews the dossier, edits the draft, proposes the action | Approves their own action |
| Approver (second officer) | Authorises a staged action | Initiates it |
| Compliance head | Owns thresholds, signs off the SAR | Delegates the filing decision to the agent |
| Agent | Reads, assembles, drafts, proposes | Writes, signs, files |

## 4. Metrics

| ID | Metric | Definition | Baseline | Target | Measured how |
|---|---|---|---|---|---|
| M1 | Time to disposition | Median minutes from alert open to a justified disposition, same seeded cases, with and without the copilot | `[ASSUMPTION]` unmeasured; replace with a timed manual run | `[TARGET]` set after the first timed run | Timed study on seeded cases |
| M2 | SAR draft time | Median minutes to a reviewable narrative | `[ASSUMPTION]` unmeasured | `[TARGET]` set after the first timed run | Same study |
| M3 | Numeric faithfulness | Share of figures in an answer that resolve to a tool result field | n/a | 100% `[TARGET]` (a release blocker) | Deterministic check in CI, reported per release |
| M4 | Disposition agreement | Agreement with seeded labels on the sealed split, plus false-positive rate on the hard negatives | n/a | `[TARGET]` set after the first backtest; never claimed before measured | Eval harness, sealed seeds |
| M5 | Cost and latency | p95 seconds and dollars per turn | now up to 65 s `[ASSUMPTION]` (recorded in CLAUDE.md, not re-measured) | p95 under 15 s `[TARGET]` | OpenTelemetry, load test |
| M6 | Triage compression | Alerts in vs high-confidence cases out on a seeded week | n/a | `[BRIEF]` 2,000 to 50 as the stated ambition; our target set after M4 | Foundry week, eval harness |

No baseline is measured. M1, M2 and M5 need a timed run or a re-measurement before any improvement is claimed.

## 5. Evaluation design

| Suite | Question | Gate |
|---|---|---|
| Faithfulness (deterministic) | Does every figure resolve to a tool result field? The auditor cases already pinned in PR #33 seed this. | Every PR |
| Trajectory | Right tools in a bounded number of rounds; only allow-listed tools; correct refusal when a tool or data is unavailable | Every PR |
| Outcome | Disposition agreement on the `dev` and `validation` splits; false positives on hard negatives (legitimate high-volume traders, hedgers, shared-context IPs) | Every PR (validation), release (sealed) |
| Adversarial | Prompt injection through tool output and partner comms text; four-eyes bypass; unauthorised write attempts | Release |

Data comes from the foundry with the split policy of ADR-015 (dev, validation, sealed) and the anti-circularity controls in `synthetic_data_strategy.md`. Ground truth stays in the eval-only store and is never visible to the agent. Real public labels are a separate, independent check where a pack supports them.

## 6. Stop and pivot criteria

Set the thresholds with you before the first backtest; candidates are listed so they can be challenged.

| Trigger | Action |
|---|---|
| Any figure fails to resolve to a tool result in a release candidate | Do not release |
| Disposition agreement on the sealed split is below the bar you set after two prompt/tool iterations | Narrow to the alert typologies where agreement holds |
| p95 latency stays above target after context caching and model routing | Move work from the model to deterministic tools |
| Investigators in a timed study do not trust the dossier | Fix the evidence presentation before adding capability |

## 7. Acceptance script (the demo that is also the workflow)

1. Open a seeded alert; the dossier appears with every figure linked to the tool call that produced it.
2. The dossier shows counter-evidence and an honest uncertainty label ("Correlation Only" where the causal gate fails).
3. Ask follow-ups in plain language; the session keeps the entity and role of the verified operator.
4. Generate the SAR draft; every number is a resolved reference, statutory citations are normalised.
5. Stage a hold; it is a KMS-signed intent that the same operator cannot approve; a second operator can.
6. Verify the ledger chain; replay the evidence bundle.
7. Disconnect the data path; the answer is labelled replay with a reason, never presented as live.

## 8. Instrumentation required

Per turn: latency, tokens, tool calls and rounds, replay flag and reason, audit verdict, citation count, operator and session id. Per decision: accept, edit or reject of the agent's recommendation, written to the ledger as a labelled outcome (the flywheel input).

## 9. Open items

- Who sets the M4 bar and the stop thresholds: you, with what reference (a Deriv-like analyst's expectation, or a published benchmark)?
- A timed manual run on seeded cases for M1 and M2: who runs it?
- The deployed system still serves fixtures (`data-strategy.md` R1); the acceptance script needs a deployed data path to be demonstrated honestly.
