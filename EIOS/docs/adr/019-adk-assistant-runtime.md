# ADR-019: Google ADK as the assistant runtime, embedded in the API service

## Status

Accepted

## Date

2026-10-14

## Supersedes

ADR-016

## Context

The copilot was a hand-written tool loop (`conversation/copilot_engine.py`) beside a keyword-routed LangGraph mesh (`conversation/graph.py`, ADR-016) that was a stub. Both are deleted. The measured baseline (`docs/agent-baseline.md`) records failing golden and attack cases, a live turn time well above the target, no role scoping, and answers that contradict the workstation screen. Spec 023 now provides one typed, role-scoped tool port (`eios.ontology.omcp.port`) and spec 022 the gates that judge any runtime through one agent port.

The pieces the runtime needs (sessions with durable per-user history, input and output screening, a bounded loop agent, a runner with a call bound and plugins for telemetry) exist as supported parts of Google's Agent Development Kit 2.11.0, pinned in PR #40.

## Options considered

- **Keep the hand-written loop and fix its defects**: Cons: we own session storage, screening, routing, retries and the loop forever; the baseline defects (shared session, role from the body) are in code we would keep.
- **LangGraph mesh completed** (ADR-016 as written): Cons: the shared-blackboard coordinator was never built; it adds a topology we do not need for five single-purpose workstation assistants.
- **ADK, one agent per workstation, embedded in `eios-api` on Cloud Run (chosen)**: ADK's Firestore session service, Model Armor plugin, `LoopAgent` and `Runner` replace custom code; our code is limited to the tool adapter over `GovernedToolPort`, the answer assembler that inserts figures from governed results, and the eval adapter.
- **Agent Runtime (managed) deployment**: Cons: a second trust boundary and a second deploy path; deferred to a later channel decision.

## Decision

1. The assistant runs on ADK, embedded in the existing API service; no separate agent service in v1.
2. Each workstation has its own agent offered only the tools of `GovernedToolPort.list_tools(principal)`; the principal comes from the verified operator.
3. The model drafts text with figure placeholders; the system inserts every figure from a governed result and fails closed after at most three attempts (a `LoopAgent` bound, deterministic, not a prompt instruction).
4. Sessions use ADK's Firestore session service in deployed environments; in-memory sessions are refused outside dev and test.
5. Input and output screening uses ADK's Model Armor plugin and blocks when the service is unavailable.
6. The runtime is judged only through the spec 022 agent port against `evals/agent/thresholds.yaml`. The legacy loop and mesh are removed and ADR-016 is Superseded. The thresholds stay the gate for the next gating run; they were not met when the legacy copilot was retired (see Evidence).

## Consequences

- Positive: less custom code to own; per-operator durable memory and screening come from supported parts.
- Positive: faithfulness no longer depends on a regex checker; unsupported figures cannot be displayed.
- Negative: ADK 2.11.0 caps `opentelemetry` at 1.42.1, which holds `fastapi` below 0.142.0 (PR #40, Dependabot ignores).
- Negative: there is no legacy fallback. If the model or the data fails, the copilot answers 503 `offline`; a deployed environment also needs the Model Armor templates and the Vertex environment variable before it can answer at all.

## Evidence

Baseline and gates: `docs/agent-baseline.md`, `specs/022-agent-quality-gates`. Tool port: `specs/023-governed-tool-port`. Dependency evidence: PR #40.

Threshold override, decided by the user on 2026-10-14. The last live run (`docs/agent-baseline.md` section 7) fell short of the pre-registered faithfulness and p95 turn latency targets in `evals/agent/thresholds.yaml`. The legacy copilot was retired anyway, because it answered any input it could not match with a canned net revenue figure and a "Qualitative Pass" banner. The three-repeat gating run is still owed.

Retired behaviour, with the reason it is not ported:
- Keyword routing and the canned "grounded replay" answers: a wrong answer served as an answer; the assistant now says it cannot answer.
- Replay of a stored answer on model failure: replaced by an honest 503 `offline` (decision of 2026-10-14).
- The Metric Auditor bridge and the audit banner: the assistant fills every figure from a governed result, so the audit is not run and is never claimed.
- The LangGraph supervisor, reflection cap and the five specialist classes: replaced by one ADK agent per workstation and the bounded `LoopAgent`.
- Kept and still tested: the OMCP tool handlers, the identity and scope rules of the endpoint (`tests/cockpit/test_copilot_identity.py`), and the ledger and quickstart scenarios.

## Revisit when

The ADK major version changes, a managed runtime or an agent-to-agent channel is required, or the live run fails the acceptance thresholds.
