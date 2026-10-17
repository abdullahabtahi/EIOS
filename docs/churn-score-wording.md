# What the cockpit calls the churn score

Decision (2026-10-17): the partner radar's score is shown as a **current disengagement risk score**, not as a "30-day churn
probability". Reason: read at the cut it ranks the planted churners at AUC 0.974 `[MEASURED]`, but scored 14 days earlier
it is 0.72 and 30 days earlier 0.44, no better than chance `[MEASURED]` (lead-time table, PR #110, `docs/operations-engine.md`).
It detects disengagement that is under way; nothing validates it as a 30-day forecast, and its level is too high (mean 0.43
against a 0.21 base rate `[MEASURED]`). The brief's "probability" wording is kept in `docs/brief/`, which is the client's.

## Changed (words only; no number, tier, wire field or model changed)
- Partner radar (axis, quadrant corners, node titles, selected-partner chip, triage column): "Risk", "Disengagement risk score".
- Partner inspector label: "CURRENT DISENGAGEMENT RISK" (was "30-DAY CHURN HAZARD").
- Copilot dossier tile: "Disengagement risk score" with "Detects, does not forecast" (was "Survival Hazard P(churn)" with "DoWhy SCM calibrated", which nothing supported).
- Partner dossier section "Disengagement risk"; executive briefing "N partners are at high disengagement risk (score 50% or more)"; the partner tool's description.
- `DiscreteTimeHazardModel.predict_30d_hazard` docstring says what the score is and is not.

## Deliberately unchanged
- The metric id `churn_hazard_probability`, the `hazard_probability_30d` field and the risk-tier cut-offs: wire and registry contracts (ADR-003); renaming is its own change.
- Value at risk (score times 30-day volume) still scales with the level; it is an exposure ranking, and it is overstated while the level is.
- The executive what-if node "Partner Churn Hazard" (a causal-graph shock), the operations calibration card (`churn-hazard-30d`), and the assistant's own wording, which follows the tool descriptions.
- `docs/brief/*`, the client's text.

## Next
Recalibrating the level needs real decision outcomes (the flywheel ledger is empty) or a world with early precursors; either must
be judged on the lead-time table, not on ECE alone.
