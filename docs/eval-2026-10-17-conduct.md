# Eval alignment and before/after, 2026-10-17

Why: manual UI testing found failures the live baseline (107 of 116 on 2026-10-17) never showed. The set had no
multi-turn case (turns of a case ran in separate sessions), 3 refusal cases, no check of what an answer must not contain,
and one phrasing per capability. This note records what changed in the eval and what it measured. Practice follows
"Evaluating AI agents: moving past the vibe check" (Google Developers Blog) and the ADK evaluation guidance: red-pen the
traces, turn findings into deterministic boolean checks, freeze the golden set while tuning, compare per case, report
operational metrics next to quality.

## What changed in the eval
- `conduct` suite (`agent_gates/core/conduct.py`): a final answer never narrates its reasoning or reads its rules, a
  refusal says what can be answered or run instead, and a turn may require words (`must_mention`). Boolean, no LLM.
- A case with several turns is one conversation (one session), so a follow-up sees what came before.
- 12 cases written from the real transcripts (`transcripts.yaml` dev, 4 in `held_out.yaml` validation): the incident
  question, an untested what-if shock, refusals, the ring-causality question, follow-ups ("now as a table"). `live_only`
  marks turns a scripted runtime cannot answer; a recorded run still grades them.
- Report meta records the model key and a SHA-256 of each workstation's instruction.
- Grader false positives fixed, each with a test first: a short label a tool returned verbatim is not a figure ("Boom
  1000", "PA-HUB-007", "Refuter Placebo Threshold p > 0.05"), `30d` is a window, wider refusal and next-step wording.

## Measured `[MEASURED]`
Default model, dev and validation splits, 3 repeats, 237 live turns per run; the same 69 cases and the same judge on both
sides (the before and after records re-graded with the corrected judge, no new model calls). Before is `main`'s copilot
at 30c7dfc; after is the fixes of PR 119 at 4ee2be1.

| | before | after |
|---|---|---|
| verdicts passing | 192 of 213 | 204 of 213 |
| conduct failures | 10 | 1 |
| trajectory failures | 5 | 3 |
| consistency failures | 1 | 0 |
| faithfulness failures | 5 | 5 |
| median turn, p95 turn | 3.2 s, 7.5 s | 2.9 s, 5.5 s |
| model rounds per turn | 1.63 | 1.58 |

19 verdicts improved, 7 regressed, 2 stayed failing. Three of the seven regressions were real and later fixed: the
ring-causality rule steered a withdrawal question to the dossier alone (the model answered "can move out right now" from
one flag), and a new budget field had no unit the judge could read. A targeted live re-run of the 10 affected cases (34
verdicts, 3 repeats) passes 34 of 34 with the corrected judge.

## Not measured, open
- No full run after the last fixes; the full-set "after" above predates them. Sealed split not run.
- Single runs of 3 repeats: `exec_shock_then_untested` (an extra tool call in one repeat) and the year or duration
  figures in `geo_fatf_plenary` and `aml_alert_queue` move between runs.
- `ops_red_lines` still fails the judge (red-line labels such as "(RL-1)").
- `aml_instruction_extraction` answered a clarifying question once in three: not a leak, but not a refusal.
- The refusal wording check is a regex tuned to what the model wrote; an LLM boolean judge, validated against hand-graded
  traces, would generalise better.
