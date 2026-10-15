# Assistant latency: what was measured and what changed

Status 2026-10-15, branch `feat/agent-latency`. Read with `docs/adk.md` (runtime) and `docs/agent-baseline.md` (the older quality baseline).

## Finding

The slow and erratic turns were the model endpoint, not quota and not our code.

- Retries off, 6 sequential small calls on the previously deployed model, thinking LOW: 5 of 6 answered in a median of 2.4 s `[MEASURED]`, one hung until the 40 s client timeout with no 429 `[MEASURED]`. A second run with no thinking level: median 4.6 s, one call 19 s `[MEASURED]`. A throttled endpoint returns 429; this one stalls.
- A real turn on that model through the runtime (6 turns, AML workstation, engine data plane): median 7.3 s, max 22.3 s `[MEASURED]`.
- Per call, model time is the whole turn. Tools, the assembler and ADK together are about 15 ms `[MEASURED]`; the one model call is about 2 s on the fast model `[MEASURED]`. Streaming cannot help: the assembler needs the whole draft before it fills any `{{fact:id}}`.

## Model comparison (same prompt, thinking LOW, retries off, 6 sequential calls)

| Registry key | Median | Max | Successes |
|---|---|---|---|
| `fast` (3.5 Flash-Lite) | 1.0 s | 2.0 s | 6 of 6 `[MEASURED]` |
| `standard` (3.5 Flash) | 2.9 s | 4.0 s | 6 of 6 `[MEASURED]` |
| `deep` (3.8 Flash, the previous default) | 2.4 s | 4.7 s, plus one 40 s hang | 5 of 6 `[MEASURED]` |

Through the runtime (3 questions twice): `fast` median 2.0 s, max 2.4 s, every turn assembled its figures on the first attempt `[MEASURED]`; `deep` median 7.3 s, max 22.3 s `[MEASURED]`. Six turns per model is a sample, not a distribution: the telemetry work (phase 6) is what turns it into one.

## What changed

1. **Model registry** (`llm_gateway/providers/assistant_models.yaml`, `registry.py`). Ordered fastest first; the first entry is the default. A turn may name another by key (`model` in the query body); an unknown key is a 422 before any work. `GET /api/cockpit/copilot/models` lists key, label, note and default, never an id. `EIOS_ASSISTANT_DEFAULT_MODEL` moves the default by key. `EIOS_GEMINI_MODEL` no longer selects the assistant's model (the live smoke test still reads it).
2. **Per-call timing** (`assistant/timing.py`). Every model call (a hedge included) and tool call is timed where it happens; the answer body carries `timing_ms` (`model`, `tools`, `other`, and each model call). This replaces guessing from event timestamps, which ADK stamps at the start of the work.
3. **Prefetch and hedge** (parked work, now on this branch). The platform runs the obvious tool before the model's first turn, and a model call still silent after `EIOS_ASSISTANT_HEDGE_AFTER_S` (default 3 s `[ASSUMPTION]`, was 5 s) is sent once more; the first answer wins. The cost is one extra call, only on a call that was already slow.
4. **Picker** in the chat header, remembered per browser, absent if the list cannot be read.

## Live quality baseline on the current code (83 turns each, 1 repeat, engine data plane)

| | `fast` (new default) | `deep` (old default) |
|---|---|---|
| pass / fail / inconclusive | 77 / 6 / 0 `[MEASURED]` | 69 / 4 / 10 `[MEASURED]` |
| faithfulness | 94.6% `[MEASURED]` | 88.2% `[MEASURED]` |
| p95 turn latency | 6.9 s `[MEASURED]` | 24.6 s `[MEASURED]` |

All 10 inconclusive turns on `deep` hit the 30 s turn deadline. `fast` had none. Both runs were started together, so absolute latencies are a little pessimistic for both; the gap is not.

`fast` failures (5 cases): three are trajectory (`ops_data_quality.t1`, `partner_integrity.t1`, `exec_causal_label.t1` took more model rounds than the bound; the last also has precision 0.67), plus `ops_red_lines.t1` and `partner_open_ended.t1` (a figure the model typed that no tool result carried; one consistency mismatch, 19.3% against 29.0 on the screen). `deep` failed `aml_timeline.t1`, `ops_red_lines.t1` and `partner_open_ended.t1`. The two shared ones are not about the model. The earlier run (`docs/agent-baseline.md` section 7, 62 turns: 43 / 7 / 12) is not comparable: the case set has since grown and the data plane moved onto engines.

## Not done, and why

- The `fast` failures, after fixes (re-run of the five failing cases, 1 repeat `[MEASURED]`): `ops_data_quality` and `partner_integrity` went from 4 model rounds and 3 rejected drafts to 2 rounds and 1 attempt, because names with digits in them (`client_360`, `Boom 1000`) were rejected as typed figures; a `*_name` or `market` field now counts as a name, and ring results carry the market as its own field. `exec_causal_label` went from 3 tools to 1 (2 model calls, about 4 s, correct "correlation only" answer, twice): the causal tool now says its ids are optional and lists the valid nodes when one is not found, and the prompt says a cause question needs only that tool. Three failures remain and are grader false positives, not wrong answers, and the old model fails them too: `ops_red_lines` (digits inside red-line names such as "p > 0.05"), `partner_open_ended` (`90 days` is part of a deal title; the consistency check compares the second deal's 19.3% with the first deal's 29.0 on screen), and a `1000` in `Boom 1000` in the judge though the assembler accepts it. Fixing the judge is left alone on purpose: loosening a grader to turn a result green is the thing the baseline exists to prevent. A proper fix binds names the tool returned, and should be validated with `--runtime recorded`.
- Hedging is unproven against a real stall: none occurred in the 12 live turns after the change. Per-call timing will show the first one.
- Model Armor: the prod-like templates exist (applied 2026-10-15, templates and the `eios-api` grant only; the service is not pointed at them yet). Screening adds p50 375 ms and p95 652 ms per turn `[MEASURED]`, 0 false positives on 32 golden questions, 1 of 15 attack questions blocked (the tool port and four-eyes are the real controls). The probe's p95 limit was re-based from 400 to 800 ms on this evidence.
- Deploy: the registry reaches production only with the next image, together with the service env vars (`GOOGLE_GENAI_USE_ENTERPRISE`, the two template names). A full prod-like apply is not safe yet: it would also lock the evidence bucket retention (irreversible), enable four org-policy guardrails and drop a phone sign-in block. Keep `evidence_lock_retention = false` and `enforce_guardrails = false` in the local tfvars until that is decided.

## Session writes, model client and plain figures (branch `feat/assistant-latency`, 2026-10-15)

Measured with `tools/assistant_latency_probe.py` on the real runtime (partner scenario, 3 runs of 2 turns, a laptop in the Philippines against us-central1, Firestore sessions, Model Armor on, `fast` model).

**Where the time went before `[MEASURED]`.** Median first turn 10.4 s and second turn 8.4 s. The model was 3.4 to 4.4 s of that. The rest was the Firestore session service: ADK writes each event of a turn as its own transaction and the turn waits for every one (6 to 8 events: 5.2 s to 6.2 s per turn, 14 s on a cold first turn), and Model Armor, 0.7 to 0.9 s. Tools were about 0 ms. The article this was checked against (Khissami, ADK post-mortem) lists schema bloat, oversized tool results, verbose output and remote tools; none applies here (prompts under 4k tokens, answers under 170, tools in-process), and ADK context caching needs a 4,096-token prefix on Gemini 3. Google's own guidance lists Firestore as the higher-latency choice for short-term agent memory.

**What changed.**
1. `session_cache.WriteBehindSessionService`: the turn reads and writes its session in memory; each session's events go to Firestore in order after the answer, with retries, a drain at shutdown and `EIOS_ASSISTANT_SESSION_WRITE_BEHIND=0` to restore write-through. The cost: the last turn can be missing from the copilot's conversation memory if the process dies right after replying (never from the decision ledger). Turn-only (`temp:`) state is cleared when a turn reads its session, and each turn starts unscreened.
2. One model client per model id for the life of the runtime (a new one cost 0.8 s per turn from a laptop `[MEASURED]`: 1,272 ms against 453 ms on the same call).
3. `timing_ms` splits `session` and `screening` out of `other`.
4. Plain figures (`assembly.py`, traced mode, `EIOS_ASSISTANT_PLAIN_FIGURES`, default on): the model writes "61.67%" or "$1.09M" and the assembler shows it only if a tool returned a matching value this turn, at the precision and in the unit written (a unit sign needs a fact of that unit; a bare number may also match a number a result held, such as days left or the 30 in `realized_volume_30d`). Text a user or dataset wrote is never a source of numbers. The figure is cited like a placeholder. One redraft, then fail closed (was two).

**After `[MEASURED]`.** Sessions alone: first turn 10.4 s to 4.2 s, second turn 8.4 s to 3.0 s. With the client reuse: 3.0 s and 3.9 s medians (3 runs, a hedge and an endpoint stall dominate the spread). A sandboxed comparison on 6 questions x 3 (same model, tools and prefetch) found the plain drafter at median 1.3 s against 2.0 s with the placeholder loop, with no invented figure in 18 answers; the 3-call turns on "why is this partner high value" came from rejected drafts. On the real runtime with plain figures: 18 turns, median 4.2 s with Model Armor on, 1.28 model calls per turn (was 1.67), no turn failed closed, every answer cited its figures, p90 7.7 s, max 8.4 s (the shared-IP question, which takes a second model call). The remaining spread is the model endpoint.

**Not measured.** Cloud Run, where Firestore is in the same region: the session saving there should be much smaller; run the probe against a deployed revision before quoting it. The live agent judges (`evals/agent`) were not re-run: they compare typed numbers with placeholders, so they need re-validating with `--runtime recorded` on a live run before the plain-figure rule is called done. The offline baseline passes 83 of 83.

## Answer depth (`assistant/intent.py`)

**What was wrong `[MEASURED]`.** On the default model, "Expound on PTR 9699" with PTR-8809 on screen failed closed; the same question on the two larger registry models failed closed or answered "has been provided", so the model tier was not the cause. The cause was ours: the entity on screen won over the entity the question named ("PTR 9699" was not read as an id), a broad question ran one tool, and rule 8 asked for a short answer with "a few supporting points", so the retention playbooks (cost, uplift, second approver) in the signals result were never shown.

**What changed.** `intent.py` reads two facts before any model call: the entity the question names (written as the system writes it) and whether the question is broad ("expound", "tell me more", "what should I do"). A broad partner question prefetches signals and the integrity check in one parallel step; a broad turn gets a four-part answer (where it stands, why, what can be done, what to check next) and rule 8 does not apply to it. No figure is typed by anything but the model and every figure still passes the assembler. The golden case `partner_open_ended` now allows `partner.integrity` as an extra tool.

**After `[MEASURED]`.** Default model, 6 questions x 3 repeats over HTTP: 18 of 18 answered, none failed closed, median 2.4 s, p90 3.7 s, max 7.0 s. Offline baseline 83 of 83. Not measured: the other two registry models on the new rules, the live agent judges, Cloud Run.
