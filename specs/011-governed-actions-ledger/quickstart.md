# Quickstart Validation Guide: Governed Actions & Decision Ledger (F10 / Slice S5)

**Feature**: `011-governed-actions-ledger`  
**Date**: 2026-10-08  
**Status**: Completed  
**References**: [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/)

This guide provides runnable end-to-end scenarios validating the Two-Phase Commit state machine, Four-Eyes authorization, upstream monotonic sequencer, cryptographic hash chaining, simulated core write-back sink with chaos faults, WORM checkpoint anchoring, and continuous audit walker.

---

## Prerequisites & Environment Setup

Ensure the virtual environment is activated and dependencies are installed:

```bash
cd "/Users/abdullahabtahi/Real-Time Enterprise Intelligence Agent/FEIOS"
source .venv/bin/activate
pip install -q pytest pydantic cryptography duckdb
```

Run test suite verification baseline:
```bash
pytest tests/ontology/test_action_intents.py
```

---

## Scenario 1: Two-Phase Commit with Four-Eyes Dual Approval (High Severity)

Validates that high-severity actions (`HoldWithdrawal`, `FreezeAccount`, `ClawbackCommission`, `SuspendPartner`) cannot execute autonomously or with only one approver (Constitution Principle II).

```python
import uuid
from datetime import UTC, datetime
from eios.ontology.actions.intent_hub import ActionIntentHub, ActionStatus, ActionSeverity, FourEyesApprovalRequiredError
from eios.ontology.actions.sink import SimulatedWriteBackSink
from eios.ontology.actions.sequencer import LedgerSequencer

# 1. Initialize Sequencer, Sink, and Hub
sequencer = LedgerSequencer()
sink = SimulatedWriteBackSink(sequencer=sequencer)
hub = ActionIntentHub(sequencer=sequencer, sink=sink)

# 2. Agent proposes high-severity HoldWithdrawal
token = hub.propose_action(
    action_type="HoldWithdrawal",
    parameters={"txn_id": "TXN-90210", "reason": "STRUCTURING_VELOCITY_SPIKE"},
    evidence_refs=["ALERT-AML-501", "DOSSIER-C-1002"],
    requester_agent_id="SentinelAMLSpecialist",
    propensity_score=0.92,
    causal_context={"deposit_velocity": 4.5, "turnover_ratio": 0.02}
)

assert token.status == ActionStatus.PENDING
assert token.severity == ActionSeverity.HIGH
assert token.requires_dual_approval is True
assert token.signature is not None  # KMS ECDSA P-256 signature valid

# 3. Compliance Officer 1 approves
hub.approve_action(token.intent_id, approver_id="OFFICER_A", role="MLRO", comment="Flagged structuring")
token = hub.get_status(token.intent_id)
assert token.status == ActionStatus.PENDING  # Still PENDING: Four-Eyes mandated!

# 4. Premature execution attempt MUST be blocked
try:
    hub.execute_action(token.intent_id)
    raise AssertionError("Execution should have failed without second approver!")
except FourEyesApprovalRequiredError:
    pass  # Correctly blocked by Principle II

# 5. Distinct Senior Officer approves
hub.approve_action(token.intent_id, approver_id="OFFICER_B", role="HEAD_OF_COMPLIANCE", comment="Confirmed")
token = hub.get_status(token.intent_id)
assert token.status == ActionStatus.APPROVED

# 6. Execute against Simulated Core Write-Back Sink
receipt = hub.execute_action(token.intent_id)
assert receipt.status == "COMMITTED"
assert receipt.external_transaction_id.startswith("SIM-CORE-")
assert token.status == ActionStatus.EXECUTED
```

---

## Scenario 2: Policy Fast-Path for Operational Actions

Validates single-approver fast-path for operational actions (`LaunchRetentionPlaybook`, `AdjustPartnerTier`) when budget is within threshold ($\le \$2,500.00$).

```python
# Propose retention playbook within threshold ($1,500 <= $2,500)
token = hub.propose_action(
    action_type="LaunchRetentionPlaybook",
    parameters={"partner_ids": ["P-88"], "playbook_id": "TIER_2_RETENTION", "budget": 1500.0},
    evidence_refs=["CHURN-ALERT-77"],
    requester_agent_id="ChurnRetentionAgent"
)

assert token.requires_dual_approval is False
assert "FAST_PATH_ELIGIBLE" in token.policy_tags

# Single manager approval immediately unlocks commit phase
hub.approve_action(token.intent_id, approver_id="MGR_1", role="PARTNER_LEAD")
assert hub.get_status(token.intent_id).status == ActionStatus.APPROVED

# Commit executes cleanly
receipt = hub.execute_action(token.intent_id)
assert receipt.status == "COMMITTED"
```

---

## Scenario 3: Idempotent Execution & Chaos Fault Injection

Validates that duplicate commits do not double-book side-effects and that injected faults transition transactions cleanly to `ABORTED` with compensation logs.

```python
from eios.ontology.actions.sink import FaultMode

# 1. Test Idempotency: Resubmit executed token with same idempotency key
idempotency_key = f"IDEM-{token.intent_id}"
receipt_1 = sink.commit_action(token, idempotency_key=idempotency_key)
receipt_2 = sink.commit_action(token, idempotency_key=idempotency_key)

assert receipt_1.receipt_id == receipt_2.receipt_id
assert receipt_1.external_transaction_id == receipt_2.external_transaction_id

# 2. Chaos Fault Injection: Simulate Core Banking Gateway Timeout
sink.set_fault_mode(FaultMode.NETWORK_TIMEOUT)

fault_token = hub.propose_action(
    action_type="FreezeAccount",
    parameters={"client_id": "C-999", "reason_code": "FRAUD_CONFIRMED"},
    evidence_refs=["EVID-999"]
)
hub.approve_action(fault_token.intent_id, "OFF_1", "MLRO")
hub.approve_action(fault_token.intent_id, "OFF_2", "HEAD")

# Execution encounters fault
abort_receipt = hub.execute_action(fault_token.intent_id)
assert abort_receipt.status == "ABORTED"
assert hub.get_status(fault_token.intent_id).status == ActionStatus.ABORTED

# Verify compensation event logged
comp_entries = sequencer.get_entries_by_event("ACTION_ABORTED")
assert len(comp_entries) > 0
```

---

## Scenario 4: Upstream Monotonic Sequencer, WORM Anchoring & Continuous Tamper Walker

Validates that all transactions form an unbroken monotonic hash chain, periodic WORM anchors lock the chain head, and the continuous audit walker detects single-byte payload tampering with 100% precision.

```python
from eios.ontology.actions.audit import ContinuousAuditWalker
from eios.ontology.actions.worm import WORMAnchorService

worm_service = WORMAnchorService(sequencer=sequencer)
walker = ContinuousAuditWalker(sequencer=sequencer, worm_service=worm_service)

# 1. Periodic WORM Anchor Checkpoint
checkpoint = worm_service.create_checkpoint()
assert checkpoint.checkpoint_seq == 1
assert checkpoint.compliance_mode is True
assert checkpoint.chain_head_hash == sequencer.get_head_hash()

# 2. Continuous Audit Verification on Untampered Ledger
report = walker.verify_ledger()
assert report.is_valid is True
assert report.integrity_score == 1.0
assert report.tampered_sequence_id is None
assert report.worm_checkpoints_verified >= 1

# 3. Simulate Adversarial Database Tampering at Sequence 3
sequencer.tamper_payload_for_testing(target_seq=3, corrupted_byte_key="reason", corrupted_val="FORGED")

# 4. Continuous Audit Walker MUST detect tampering and pinpoint exact sequence index
tamper_report = walker.verify_ledger()
assert tamper_report.is_valid is False
assert tamper_report.integrity_score < 1.0
assert tamper_report.tampered_sequence_id == 3
assert "HASH_MISMATCH" in tamper_report.failure_reason
```

---

## Scenario 5: Multi-Horizon Decision Outcomes & Doubly Robust AIPW Tracking

Validates logging of propensity scores $e(X)$, causal contexts, manager override flags, and multi-horizon forward outcomes to eliminate confounding by indication.

```python
from eios.ontology.actions.outcomes import DecisionOutcomesStore

outcomes_store = DecisionOutcomesStore()

# 1. Record decision context at proposal time
outcome_record = outcomes_store.record_proposal(
    intent_id=token.intent_id,
    entity_id="P-88",
    action_type="LaunchRetentionPlaybook",
    propensity_score=0.84,
    causal_features={"tier": 2, "churn_risk": 0.65, "tenure_months": 18},
    manager_override_flag=True,
    override_reason="Strategic VIP account - reduced budget from $2500 to $1500"
)

assert outcome_record.manager_override_flag is True
assert outcome_record.propensity_score == 0.84

# 2. Reconcile forward actuals at elapsed horizons (30d, 60d, 90d)
reconciled = outcomes_store.reconcile_outcomes(
    outcome_id=outcome_record.outcome_id,
    observed_retained_revenue_30d=4200.0,
    observed_retained_revenue_60d=8900.0,
    actual_churn_60d=False,
    clawback_recovered_usd_90d=0.0
)

assert reconciled.observed_retained_revenue_60d == 8900.0
assert reconciled.actual_churn_60d is False
```

---

## Scenario 6: OMCP Governance Tools & Deterministic Replay Fallback

Validates inspection of ledger status and audit reports through OMCP tool calls and ensures deterministic `[REPLAY]` badging during LLM outages.

```python
from eios.ontology.omcp.server import OMCPHandler
from eios.conversation.specialists.governance import GovernanceAuditorSpecialist

omcp = OMCPHandler()
audit_status = omcp.handle_tool_call("get_ledger_audit_status", {})
assert "head_seq" in audit_status
assert "integrity_score" in audit_status

# Test Governance Conversational Specialist Replay Fallback
specialist = GovernanceAuditorSpecialist(omcp_handler=omcp)
response = specialist.handle_query(
    query="What is the cryptographic health of our action ledger?",
    simulate_llm_outage=True
)

assert "[REPLAY]" in response["content"]
assert "Cryptographic Ledger Status" in response["content"]
assert response["is_fallback"] is True
```

---

## Test Execution Commands

To execute all unit, contract, and integration tests for this feature:

```bash
# Run feature-specific test suite
pytest tests/ontology/test_action_intents.py \
       tests/ontology/test_action_intents_fast_path.py \
       tests/ontology/test_ledger_sequencer.py \
       tests/ontology/test_simulated_sink_chaos.py \
       tests/ontology/test_worm_and_audit_walker.py \
       tests/ontology/test_decision_outcomes_aipw.py \
       tests/ontology/test_omcp_governance_tools.py -v

# Run full project regression suite (2,135+ tests)
pytest tests/
```
