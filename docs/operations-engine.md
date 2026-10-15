# Operations workstation on engines (Phase 2b, second half)

The operations board and the assistant's operations tools read `EngineOperationsService`
(`src/eios/dataplane/ops_service.py`), built with the other planes by `dataplane.plane`. Origin on the wire is `engine`.
`EIOS_DATA_PLANE=fixture` keeps the hand-written service for unit tests. Design of the executive half: `docs/executive-engine.md`.

## What is measured

| Surface | Source |
|---|---|
| Contract enforcement, quarantine | The AML world's last week of transactions replayed through the real `IngestionPipeline` (validator, DLQ, circuit breaker, DQ monitor, token vault, hot state) |
| Data products | Nine products profiled from the worlds' frames: rows, completeness over required fields, newest event, contract breach rate |
| Service objectives | `SLOMonitoringEngine`, fed by synthetic probes through the same tool port the assistant uses |
| Red lines | Probes and engine measurements (below) |
| Recovery proof | A real restore drill: export the accepted events to Parquet with lineage, rehydrate a fresh hot state, compare |
| Calibration | The partner engine's 30-day-old hazards against what partners then did (30-day volume fell by 15% or more) |

## How enforcement is checked

A small share of the replayed events is broken on purpose with the foundry's `BreachInjector`, and only the evaluation
knows which. All 11 planted breaches were quarantined and no healthy event was refused over 2,818 events `[MEASURED]`.
The breach rate of 0.39% is about eight times the circuit breaker's 0.05% budget, so `transactions_aml` reads DEGRADED
with 11 quarantined records: the board's one real incident. Redrive runs a record back through the pipeline; a record
that still breaks its contract is refused with the reason and stays quarantined.

## Honest gaps, kept visible

- **Freshness is reported, not judged.** The worlds are batch snapshots cut at the as-of; the newest event's age
  reflects how busy a product is (the AML world's last transaction before the cut is 85 minutes old `[MEASURED]`), not
  how late ingestion was. Judging it against a 30-second contract SLA would paint a false incident.
- **An unobserved objective reads `NO_DATA`**, with no compliance figure. Ingestion freshness, approvals and the agent's
  first-token time have no probe (the assistant does not stream, so there is no first token). Six of eleven objectives
  were observed at start-up `[MEASURED]`; the agent's full-answer latency and the hallucination gate fill in as real
  turns are served (`assistant/telemetry.py`): a timed-out or failed turn spends latency budget, and the gate counts the
  turns that went through the assembler (zero unverified figures passed is true by construction, so the count, not the
  zero, is the information). The window is the running instance's memory, not history.
- **Two red lines are `NOT_MEASURED`** and say why. RL-2 (four-eyes) is tested in CI, but a probe would write to the
  ledger. RL-7 (replay) does not apply: the assistant never replays by decision (ADR-019).
- **Only the warm-start path is drilled.** Key rotation shows `NOT_ASSESSED`. The other nine runbooks are still a
  catalogue whose execution is a timed placeholder, so the tools report them as catalogue only.
- **Identity conflicts are not computed** on this plane; the count is null, not zero.
- Probe-based objectives describe probe traffic at start-up, not production load. The board says how many events each had.

## Measured red lines `[MEASURED]`

RL-1 (the briefing and a governed metric recomputed twice are identical), RL-3 (every verified edge clears the placebo
and confidence thresholds and the control is not verified), RL-4 (the largest detected ring is no bigger than the
largest planted one), RL-5 (the ledger's hash chain walked end to end) and RL-6 (p95 of 100 what-if calls through the
port is well under the 200 ms budget) all pass. The restore drill rehydrated 2,807 of 2,807 rows.

## Removed

The hand-typed streaming lag, error budgets, red lines and recovery proof in the gateway; the two invented quarantine
records and the always-succeeding redrive; the "verify runbook" button that waited 400 ms and reported success; the
`[ILLUSTRATIVE]` baseline the board showed when it received nothing (it now says nothing arrived); the compliance
explorer's copy of the recovery card; the flywheel panel's typed counts on the engine plane.

## A finding: the churn hazards rank well and are not calibrated

Against what partners then did, the hazard model's probabilities overstate churn. Its mean hazard is 0.43 `[MEASURED]`
while the share of partners whose volume fell by 15% or more in the following 30 days is 0.21 `[MEASURED]`, and its
expected calibration error is 0.22 against the 0.15 drift line, so the status dialog reads DRIFT DETECTED. The ranking is
excellent (AUC 0.974 `[MEASURED]`), so the radar's order is trustworthy; the absolute probabilities are not. The verdict
does not hang on the label: with churn defined as a fall of 30% or 50% instead, the error is 0.37 and 0.42
`[MEASURED]`, always above the line. The remedy is recalibration against observed outcomes (isotonic or Platt), which is
the flywheel's job and is not done here.

## Calibration and the flywheel

`ops.calibration` now has a real basis. The flywheel's decision-outcomes ledger is still empty, so its causal
recalibration has nothing to learn from until actions are staged and their outcomes recorded.
