# Quickstart: Conversational Analytics & Multi-Agent Reasoning Mesh (F06)

**Feature**: `007-conversational-analytics` | **Date**: 2026-10-07  
**Status**: Completed  
**References**: `specs/007-conversational-analytics/spec.md`, `specs/007-conversational-analytics/research.md`, `specs/007-conversational-analytics/data-model.md`.

---

## 1. Initialize the Conversational Engine

Instantiate the Layer 3 `ConversationEngine`, wiring the `SupervisoryRouter`, `ArbitratingCoordinatorAgent`, and underlying `OMCPServer`:

```python
from eios.ingestion.hot_state import HotStateEngine
from eios.ontology.omcp.server import OMCPServer
from eios.conversation.engine import ConversationEngine

# Initialize hot state and OMCP tool router
hot_state = HotStateEngine()
omcp_server = OMCPServer(hot_state=hot_state)

# Initialize conversational engine with coordinator and metric auditor
engine = ConversationEngine(omcp_server=omcp_server)
```

---

## 2. Execute Single-Turn Executive Inquiry (Supervisory Routing)

Query the engine with a cross-domain performance inquiry:

```python
response = engine.chat(
    user_query="What's driving the quarterly variance in our revenue forecast?",
    user_role="Executive",
)

print(f"Assigned Route: {response.route}")
print(f"Turn Latency: {response.turn_latency_ms:.2f} ms")
print(f"Auditor Passed: {not response.is_replay_fallback}")
print(f"Response:\n{response.response_markdown}")
print(f"Citations: {response.citations}")
```

**Expected Behavior**:
- Routed automatically to `SpecialistDomain.SYNTHESIS`.
- Dispatches `get_forecast` and `attribution` OMCP tools.
- Response narrative explains variance with driver shares summing to exactly $100.0\%$.
- 100% of numerical figures pass the Metric Auditor Gate.

---

## 3. Execute Multi-Turn Drill-Down Session

Execute consecutive turns maintaining entity context and pronominal resolution:

```python
# Turn 1: Discover high-risk affiliate partners
turn1 = engine.chat(
    session_id="exec-session-001",
    user_query="Which tier-1 affiliate partners show significant disengagement risk in the last 14 days?",
    user_role="PartnerManager",
)
print("Turn 1 Route:", turn1.route)  # ChurnRadar
print("Turn 1 Response:", turn1.response_markdown)

# Turn 2: Pronominal reference to partner P-102
turn2 = engine.chat(
    session_id="exec-session-001",
    user_query="What is the recommended retention playbook for partner P-102?",
    user_role="PartnerManager",
)
print("Turn 2 Route:", turn2.route)  # ChurnRadar
print("Turn 2 Citations:", turn2.citations)  # Contains ['P-102']
print("Turn 2 Response:", turn2.response_markdown)
```

**Expected Behavior**:
- Turn 2 automatically resolves entity context from Turn 1.
- Tool trace executes `get_retention_playbook` with `P-102`.
- Turn latency is under $3.5\text{s}$.

---

## 4. Test Assumption Challenge & Counterfactual Exploration

Stress-test an assumption using scenario shock simulation:

```python
turn3 = engine.chat(
    session_id="exec-session-001",
    user_query="What if the competitor reverses their spread reduction next month? How does that alter the forecast?",
    user_role="Executive",
)
print("Turn 3 Route:", turn3.route)  # Synthesis
print("Causal Projection:", turn3.response_markdown)
```

**Expected Behavior**:
- Supervisory Router identifies counterfactual condition and routes to `Synthesis`.
- Executes `run_scenario` with parametric shocks.
- Outputs 95% confidence bounds and sensitivity intervals.

---

## 5. Test Honest Refusal on Speculative / Unanswerable Queries

Verify that speculative inquiries lacking data are cleanly refused without hallucinated figures:

```python
refusal = engine.chat(
    user_query="Exactly how much profit will competitor Apex Global report for Q4 2030?",
    user_role="Executive",
)
print("Refusal Output:", refusal.response_markdown)
assert "insufficient data" in refusal.response_markdown.lower()
assert len(refusal.evidence_ledger) == 0
```

**Expected Behavior**:
- Identified as an unanswerable external speculation.
- Emits the canonical declaration `"insufficient data"`.
- Zero OMCP tools called and zero invented numbers.

---

## 6. Run Golden Dialogue Trajectory Benchmark Suite

Execute the automated test suite evaluating all 10 golden dialogue scenarios in `evals/golden/dialogues/`:

```bash
uv run pytest tests/evals/test_golden_dialogues.py tests/evals/test_trajectory_eval.py -v
```

Assert that:
1. Supervisory Router accuracy $\ge 95.0\%$.
2. Trajectory validity is 100% (zero redundant or forbidden calls).
3. 100% of unanswerable queries emit valid honest refusals.
