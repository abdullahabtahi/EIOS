# Ambient dossiers: the brief exists before the alert is opened

Status: thin slice built on `feat/ambient-dossiers` (issue #70). Design: `docs/agent-architecture.md` section 4. Not deployed.

## What it is

For the top alerts, the assistant's own "Brief me on this case." turn runs ahead of time and its answer is kept with the time it was prepared. The AML dossier column shows it as "Prepared brief, prepared at 14:05 UTC", with the same figure badges and regulation sources an answer carries. Opening a top alert needs no model wait.

The engine dossier (sections, metrics, graph) was already computed instantly. What was slow is the assistant's narrated brief, a model turn of about two seconds; that is what is kept.

## Shape

```
refresh (API start-up, or POST /api/cockpit/ambient/refresh from Cloud Scheduler)
   -> top N alerts from the AML triage queue (existing deterministic ranking)
   -> for each, one at a time: the assistant's brief turn as the system identity `system:ambient`
        over a port restricted to evidence, compute and knowledge tools (no propose, no draft)
   -> kept only if the turn assembled (not blocked, not failed closed, not a replay): PreparedBrief in the record store
GET /api/cockpit/ambient/briefs/{entity_id} -> the brief, stale flag, or 404 "no brief has been prepared"
```

- **The guarantee carries over.** The turn is the one an operator would run, so the assembler's rule holds for the kept text: every figure came from a tool result of that turn, and it names its source. Nothing is rewritten after the fact.
- **Read-only by construction.** `GovernedToolPort.restricted_to` builds a port that does not offer propose or draft tools; a call to one is refused as an unknown tool (`tests/ambient/test_brief.py`). The brief carries no proposals.
- **Honest when absent or old.** No brief is a 404 the card states ("No brief was prepared for this alert"), never a placeholder. A brief past its time to live (`EIOS_AMBIENT_TTL_S`, default one hour `[ASSUMPTION]`) is still shown, marked "older than its time to live".
- **Storage.** The record store: Firestore when `EIOS_PERSISTENCE=firestore` (collection `eios_ambient_briefs`), memory in dev and test.
- **Control.** `EIOS_AMBIENT_TOP_N` (default 0: nothing runs at start-up, so tests and dev stay quiet; at most 25). `POST /api/cockpit/ambient/refresh` needs an approver or compliance head, answers 202 at once, and runs at most one refresh at a time.

## Measured (local gateway, dev project, fast model, 2026-10-16)

| What | Result `[MEASURED]` |
|---|---|
| Preparing the top 5 briefs, one at a time | 11.4 s in total (about 2.3 s each) |
| Reading a prepared brief | 4.4 ms median (5 alerts) |
| The same brief as a fresh turn | 1.82 s median, 1.34 to 2.81 s (5 alerts) |
| Figures in the prepared brief against a fresh turn, by returned value | 30 of 30 equal; the same fact ids in both |
| Fresh turns that assembled | 5 of 5 |

The first comparison read 29 of 30: one figure was written "$1,060" in the prepared brief and "$1060" in the fresh turn. The same value formatted differently is not a difference, so the check now compares the value the tool returned. A second full run gave 30 of 30 (the briefs from the first run were still current, so its preparation time is not reported). Reproduce with `python -m evals.agent.ambient_eval --base <gateway> --top 5` (it spends model calls).

## Not built, and why

- **Cloud Scheduler and the Pub/Sub push with dead-letter.** The refresh route and the start-up refresh are the thin version; wiring a scheduler is a Terraform change that needs the owner's go.
- **A "build one now" button.** Building needs an approver role by design (it spends model calls for everyone), so the card tells an operator to ask the assistant instead.
- **A judged faithfulness run over the cached text.** The brief is the assembler's own output, so its figures are supported by construction; a judge pass over stored briefs would show the judges agree, and can use `evals.agent.faithfulness_suite` once briefs are recorded.
- **Other workstations.** Only the AML dossier column shows a brief.
