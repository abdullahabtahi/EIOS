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

## Not done, and why

- No live quality baseline on the new default yet. The six live turns above are grounded, but `docs/agent-baseline.md` section 7 predates the ADK runtime; re-measure with `python -m evals.agent.baseline --runtime adk --live --repeats 1` when the owner approves the spend.
- Hedging is unproven against a real stall: none occurred in the 12 live turns after the change. Per-call timing will show the first one.
- Deploy: the registry reaches production only with the next image. Model Armor templates and `GOOGLE_GENAI_USE_ENTERPRISE` are a separate step.
