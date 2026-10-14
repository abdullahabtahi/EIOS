# Contract: Agent Port

The single entry point every suite uses (FR-003). A runtime is judged only through this interface.

```python
class AgentPort(Protocol):
    runtime_name: str
    def run_turn(self, request: TurnRequest) -> TurnRecord: ...
```

## TurnRequest

| Field | Meaning |
|---|---|
| `question` | Operator text |
| `role` | One of the five workstation roles |
| `operator_id` | Verified identity to act as; adapters that cannot honour it record `identity_source = request_body` |
| `session_id`, `turn_index` | Conversation position |
| `entity_context` | Optional entity id and type |
| `tool_fixtures` | Optional map of capability to fields overlaid on the real tool result where the runtime dispatches tools, so injected text rides on a result that keeps its shape; used for injection cases |
| `repeat` | Repeat index, recorded |
| `deadline_s` | Hard limit; exceeding it yields an `inconclusive` record, never an exception |

## Obligations of an adapter

1. Return a complete `TurnRecord` for every call, including outages (`outcome = inconclusive` with a reason, or a labelled replay with `is_replay_fallback = true`).
2. Record every tool call with arguments and results exactly as the model saw them.
3. Never read case ground truth, expected values or the case's `must_not` list.
4. Be side-effect free outside the process: no network except the runtime's own model and tool calls, no writes to production stores.
5. Report `data_origin` as the runtime declares it; do not infer `live`.

## Provided adapters

| Adapter | Purpose |
|---|---|
| `copilot` | Today's `CopilotEngine.process_query`; tool calls captured by spying on its dispatcher |
| `standin:always42` | Answers "42" with no tools; must fail faithfulness and trajectory |
| `standin:scripted` | Returns scripted records; used by unit tests of the suites |
| `adk` (spec 021) | The new runtime, same port |
