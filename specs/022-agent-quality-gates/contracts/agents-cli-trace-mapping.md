# Contract: Turn Record to `agents-cli eval` trace

Verified by spike S-EVAL-1 (2026-10-14): a local deterministic metric file graded these traces with no cloud call.

| Turn Record | `agents-cli` eval case |
|---|---|
| `case_id` and `repeat` | `eval_case_id` = `<case_id>.<repeat>` |
| `question` | `prompt` = `{role: user, parts: [{text}]}` |
| `answer` | **`responses`** = `[{response: {role: model, parts: [{text}]}}]`. Required: without it every case errors with "No response found for candidate 0" |
| `tool_calls[]` | `agent_data.turns[0].events[]`: a `function_call` part (author = agent id) followed by a `function_response` part (author `tool`) per call |
| final text | last event of the turn, author = agent id, `parts: [{text}]` |
| `runtime` | `agent_data.agents[<agent_id>]` with `agent_type` and `instruction` |
| `bindings`, `data_origin`, `identity_source`, `is_replay_fallback` | extra fields on the case; allowed by the schema and visible to a metric as `instance[...]` |

## Metric shim contract

`evals/agent/metrics/<name>.py` defines `def evaluate(instance)` returning `{"score": float, "explanation": str}`. It:

1. rebuilds a Turn Record dict from `instance`,
2. calls the standard-library core (`eios.agent_gates.core.*`) loaded by path, never `import eios` (the CLI interpreter is Python 3.12 and our package needs 3.14),
3. returns score 1.0 for pass, 0.0 for fail, and a score of `None` with an explanation for inconclusive.

An acceptance test imports every `core/` module under Python 3.12 to keep this true.
