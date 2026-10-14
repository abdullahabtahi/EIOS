# Lighthouse timed-study protocol (M1 and M2)

**Status**: protocol only, not executed. **Owner of the run**: a person outside the code (you or an analyst). **Why**: `docs/lighthouse.md` metrics M1 (time to disposition) and M2 (SAR draft time) have no measured baseline, so no improvement can be claimed until this is run once without the assistant and once with it.
**Tags**: `[ASSUMPTION]` a starting value to revisit after the first run; nothing here is `[MEASURED]`.

## What is timed

| Interval | Starts | Stops | Metric |
|---|---|---|---|
| Time to disposition | The alert is opened | The participant records a justified disposition (close, escalate or hold) with their reason | M1 |
| SAR draft time | The participant starts the narrative | A narrative a second reviewer judges reviewable (every figure sourced, the rule cited, no unsupported claim) | M2 |

Timing is by stopwatch or screen recording; the reviewer's acceptance, not the participant's, ends M2.

## Design

- **Cases**: 12 seeded AML alerts from the synthetic foundry, development split only, `[ASSUMPTION]`: 4 true positives, 4 hard negatives (legitimate high-volume traders, hedgers, shared-network addresses), 4 ambiguous. The sealed split is never used here.
- **Conditions**: A) the current systems and dossier without the assistant; B) with the assistant. Each participant does 6 cases in each condition, in an order balanced across participants (case order randomised, condition order alternated) so learning does not favour one condition.
- **Participants**: at least 3 people who know the domain `[ASSUMPTION]`. Record role and years of experience; do not record names.
- **Briefing**: 10 minutes on the cockpit and the assistant, the same for everyone, using a case that is not in the study.
- **Ground truth**: the seeded label for each case is held by the study owner and is never shown to participants or to the assistant.

## Recording sheet (one row per case and participant)

`participant_code`, `case_id`, `condition`, `order_index`, `t_open`, `t_disposition`, `t_sar_start`, `t_sar_accepted`, `disposition`, `matches_label` (study owner fills in), `figures_checked_by_reviewer`, `unsupported_figures_found`, `notes`.

## Analysis

- M1 and M2: median per condition with the 25th and 75th percentiles, and the paired difference per participant; report the count of cases, not only the medians.
- Disposition agreement with the label (M4 input) and false-positive rate on the hard negatives, per condition.
- Report unsupported figures the reviewer found in assistant-assisted drafts; the target is zero (M3).
- Do not claim an improvement from fewer than the planned cases or participants; say what was run.

## Stop and pivot (from `lighthouse.md` section 6)

If participants do not trust the dossier, fix the evidence presentation before adding capability. If the assisted condition is slower, find out where the time went before changing anything else.
