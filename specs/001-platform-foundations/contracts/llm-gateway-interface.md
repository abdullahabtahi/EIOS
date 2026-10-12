# Contract: LLM Gateway Interface

**Feature**: F00 | **Requirements**: FR-021..FR-028, FR-037 | **Constitution**: I, III, VIII | **Open decisions kept open**: ADR-002, S-01

Design-time contract for the in-process gateway library (`src/eios/llm_gateway`). Not a network API. Field names are illustrative of shape.

## Single access point

Every model call in the platform goes through one operation:

```text
complete(request: GatewayRequest) -> GatewayResponse
```

Direct use of a vendor SDK outside `providers/` is forbidden and enforced by a ruff banned-import rule (FR-021).

## GatewayRequest

| Field | Type | Rules |
|---|---|---|
| prompt_id | string | must exist in `prompts.lock.json` |
| prompt_version | string | must match a locked version |
| inputs | map string→string | validated; untrusted text arrives wrapped by `untrusted_text` |
| correlation_id | string | required |
| caller | string | service identity name |

The request has no field for model name, price or provider: those come from configuration only (FR-022).

## GatewayResponse

| Field | Type | Rules |
|---|---|---|
| outcome | enum | `ok`, `replay`, `unavailable`, `cap_reached` |
| content | string or null | non-null only for `ok` and `replay` |
| trace_id | string | always present |
| replay_original_at | timestamp or null | non-null only for `replay` |

There is no `guess`, `estimate` or numeric-claim field. The gateway returns text; business numbers come from deterministic tools (Constitution I).

## Behaviour rules

| Situation | Outcome | Notes |
|---|---|---|
| Provider call succeeds | `ok` | result stored in the replay store; trace written |
| Provider unavailable or times out, cached result exists for the request key | `replay` | carries `replay_original_at` so a replay badge can show age (FR-025) |
| Provider unavailable, no cached result | `unavailable` | never fabricated output |
| Daily token cap reached, cached result exists for the request key | `replay` | provider is not called; carries `replay_original_at`; cached replays remain allowed after the cap (FR-023, spec edge case) |
| Daily token cap reached, no cached result | `cap_reached` | provider is not called; explicit, non-silent refusal (FR-023) |
| Usage at 50% / 80% of cap `[TARGET]` | `ok` plus a warning event | warnings do not block |
| Prompt id/version missing from lockfile | validation error | raised before any provider call |
| No model configured in a deployed environment | startup failure | no default model (FR-028) |
| Config value lacks a verification tag | startup failure | FR-022 |

Replay key: hash of prompt id, prompt version, inputs and configuration identity.

## Provider protocol

```text
Provider.generate(rendered_prompt, model_id, limits) -> ProviderResult
  ProviderResult: content, tokens_in, tokens_out
  raises ProviderUnavailable on outage or timeout
```

F00 ships only the stub provider (deterministic canned responses, configurable failure). Real providers are added after S-01 closes and ADR-002 is accepted.

## Store interfaces

```text
CounterStore.add_tokens(day, count) -> running_total
ReplayStore.get(key) -> (content, stored_at) or none
ReplayStore.put(key, content, stored_at)
```

Implementations: `memory` (dev and CI) and `firestore` (deployed environments). Stores hold no secrets.

## Trace

Every call, whatever the outcome, emits one LLM Call Trace conforming to [llm-call-trace.schema.json](./llm-call-trace.schema.json). Configuration conforms to [llm-gateway-config.schema.json](./llm-gateway-config.schema.json).

## Contract tests (owned by F00)

- Every outcome above is reachable with the stub provider.
- A request cannot carry model, price or provider.
- With the provider forced unavailable and an empty replay store the result is `unavailable`, never text.
- The cap blocks at 100% and never calls the provider afterwards.
- At the cap, a request with a cached result for its key returns `replay`, and one without returns `cap_reached`; neither calls the provider.
- A trace exists for every outcome and never contains secret-shaped strings.
