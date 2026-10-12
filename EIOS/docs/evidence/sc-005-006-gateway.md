# SC-005 and SC-006: LLM gateway outcomes, caps and traces

**Date**: 2026-10-02. **Scenario**: quickstart scenario 5 (T131). **Provider**: the deterministic stub, with no network and no real model (ADR-002 is open). **Result**: 11 of 11 checks pass, and `uv run python -m tools.repo_checks` exits 0.

## What was run

A throwaway script drove the real `Gateway` through the shared test kit in `tests/support/llm_gateway.py` (in-memory stores, a controllable clock, the stub provider) from `FEIOS/`. It is not part of the repository. The contract tests under `tests/contract/llm_gateway/` are the durable checks; the script re-exercised the same behaviour end to end to record evidence. Nothing here touched a real provider, so token counts, prices and caps below are synthetic `[ILLUSTRATIVE]` values from the dev-shaped test configuration.

## Results

| # | Check | Result | Observed |
|---|---|---|---|
| 1 | Normal call returns `ok` with text | pass | 5 tokens in, 3 out |
| 2 | Provider unavailable and empty replay store returns `unavailable`, no content | pass | content is null, nothing invented |
| 3 | Provider outage after a warmed call returns `replay` with the original timestamp | pass | `replay_original_at` 12:00:00Z, served 12:05:00Z |
| 4a | 50% and 80% daily-cap warnings fire once each, cap reached once | pass | events: warning, warning, reached, refused |
| 4b | `cap_reached` makes no provider call | pass | provider call count unchanged on the refused call |
| 5a | Every captured trace validates against `schemas/llm-call-trace.schema.json` | pass | 4 of 4 |
| 5b | One trace exists for each outcome | pass | ok, replay, unavailable, cap_reached |
| 5c | No secret-shaped strings appear in traces, including calls whose input was a secret | pass | none of the planted shapes leaked |
| 6a | A changed configuration changes `config_identity` | pass | |
| 6b | Removing a verification tag is rejected | pass | `verification.prices: is required` |
| 6c | The dev configuration loads | pass | |

Observation on 4: with a 1,000-token cap and 300 tokens per call, usage went 300, 600, 900, 1,200. The call that crosses the cap completes and the next one is refused, so the cap limits starting new calls and is not a hard ceiling on tokens spent. Actual usage can exceed the cap by up to one call.

## Captured traces, one per outcome

`config_identity` is the same sha256 on every record (`91b3fa4e...dd457` in the test configuration) and is omitted from the lines below for width; it was present and schema-validated on each. `trace_id` values repeat only because each outcome was captured from its own freshly built kit.

```json
{"outcome": "ok", "trace_id": "trace-0001", "correlation_id": "corr-1", "prompt_id": "smoke-echo", "prompt_version": "v1", "tokens_in": 5, "tokens_out": 3, "cost": 0.022, "latency_ms": 0, "recorded_at": "2026-01-01T12:00:00Z"}
{"outcome": "replay", "trace_id": "trace-0002", "correlation_id": "corr-1", "prompt_id": "smoke-echo", "prompt_version": "v1", "tokens_in": 0, "tokens_out": 0, "cost": 0.0, "latency_ms": 0, "recorded_at": "2026-01-01T12:05:00Z", "replay_original_at": "2026-01-01T12:00:00Z"}
{"outcome": "unavailable", "trace_id": "trace-0001", "correlation_id": "corr-1", "prompt_id": "smoke-echo", "prompt_version": "v1", "tokens_in": 0, "tokens_out": 0, "cost": 0.0, "latency_ms": 0, "recorded_at": "2026-01-01T12:00:00Z"}
{"outcome": "cap_reached", "trace_id": "trace-0006", "correlation_id": "c-final", "prompt_id": "smoke-echo", "prompt_version": "v1", "tokens_in": 0, "tokens_out": 0, "cost": 0.0, "latency_ms": 0, "recorded_at": "2026-01-01T12:00:00Z"}
```

## Limits

- The stub provider proves the gateway's control flow, not any real model's behaviour. Real token counts, latency and prices need a provider chosen through ADR-002, which stays open.
- Latency is 0 ms throughout because the test clock does not advance during a call. A non-zero latency is exercised only by the contract test in `tests/contract/llm_gateway/test_trace.py`.
- The replay store and counter are in-memory. The Firestore-backed stores are covered by tests that skip without the emulator (4 skipped), so their behaviour is unverified here.
- The UTC day reset is not exercised by this run; it is covered by `test_cap.py::test_the_counter_resets_on_the_next_utc_day`.
- Prices, rate limits and caps in the dev configuration are `[ILLUSTRATIVE]`; the warning thresholds are `[TARGET]`.
