"""Contract tests validating governance JSON Schemas (Slice S5 / F10)."""

import json
from pathlib import Path

import jsonschema

from eios.ontology.actions.models import (
    ActionIntentToken,
    ActionSeverity,
    ActionStatus,
    ApprovalRecord,
    AuditVerificationReport,
    ExecutionReceipt,
    ExecutionStatus,
    LedgerEntry,
    LedgerEventType,
    WORMAnchorCheckpoint,
)

CONTRACTS_DIR = (
    Path(__file__).resolve().parents[3] / "specs" / "011-governed-actions-ledger" / "contracts"
)


def load_schema(schema_name: str) -> dict:
    schema_path = CONTRACTS_DIR / schema_name
    assert schema_path.exists(), f"Schema file not found at {schema_path}"
    with open(schema_path, encoding="utf-8") as f:
        return json.load(f)


def test_action_intent_token_contract_validation():
    schema = load_schema("action-intent-token.schema.json")
    token = ActionIntentToken(
        intent_id="550e8400-e29b-41d4-a716-446655440000",
        action_type="HoldWithdrawal",
        parameters={"txn_id": "TXN-909", "reason": "VELOCITY_SPIKE"},
        evidence_refs=["ALERT-1", "ALERT-2"],
        severity=ActionSeverity.HIGH,
        status=ActionStatus.PENDING,
        nonce="11223344556677889900aabbccddeeff",
        issued_at="2026-10-08T08:00:00Z",
        expires_at="2026-10-08T08:15:00Z",
        requester_agent_id="SentinelAMLSpecialist",
        kms_key_id="local-mock-kms-p256",
        signature="MEQCIBZ53G...",
        approvals=[
            ApprovalRecord(
                approver_id="OFFICER_A",
                approver_role="MLRO",
                comment="Initial review passed",
            )
        ],
        propensity_score=0.91,
        causal_context={"deposit_velocity": 4.5},
        requires_dual_approval=True,
        policy_tags=["DUAL_APPROVAL_MANDATORY"],
    )

    data = json.loads(token.model_dump_json())
    jsonschema.validate(instance=data, schema=schema)


def test_ledger_entry_contract_validation():
    schema = load_schema("ledger-entry.schema.json")
    entry = LedgerEntry(
        ledger_seq=1,
        prev_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        current_hash="4a7f8e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b785",
        event_type=LedgerEventType.PROPOSAL_CREATED,
        entity_id="550e8400-e29b-41d4-a716-446655440000",
        payload_digest="d41d8cd98f00b204e9800998ecf8427e00000000000000000000000000000000",
        payload={"action_type": "HoldWithdrawal", "status": "PENDING"},
        recorded_at="2026-10-08T08:00:00Z",
        worm_checkpoint_seq=None,
    )

    data = json.loads(entry.model_dump_json())
    jsonschema.validate(instance=data, schema=schema)


def test_execution_receipt_contract_validation():
    schema = load_schema("execution-receipt.schema.json")
    receipt = ExecutionReceipt(
        receipt_id="770e8400-e29b-41d4-a716-446655440000",
        intent_id="550e8400-e29b-41d4-a716-446655440000",
        idempotency_key="IDEM-550e8400",
        external_transaction_id="SIM-CORE-TXN-1001",
        action_type="HoldWithdrawal",
        status=ExecutionStatus.COMMITTED,
        simulated_latency_ms=12.5,
        executed_at="2026-10-08T08:05:00Z",
        side_effects={"withdrawal_status": "HELD"},
    )

    data = json.loads(receipt.model_dump_json())
    jsonschema.validate(instance=data, schema=schema)


def test_worm_anchor_checkpoint_contract_validation():
    schema = load_schema("worm-anchor-checkpoint.schema.json")
    checkpoint = WORMAnchorCheckpoint(
        checkpoint_seq=1,
        chain_head_seq=100,
        chain_head_hash="4a7f8e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b785",
        locked_at="2026-10-08T08:00:00Z",
        retention_until="2033-10-08T08:00:00Z",
        compliance_mode=True,
        lock_signature="MEYCIQDw01...",
    )

    data = json.loads(checkpoint.model_dump_json())
    jsonschema.validate(instance=data, schema=schema)


def test_audit_verification_report_contract_validation():
    schema = load_schema("audit-verification-report.schema.json")
    report = AuditVerificationReport(
        report_id="990e8400-e29b-41d4-a716-446655440000",
        verified_at="2026-10-08T08:30:00Z",
        total_entries=100,
        genesis_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        head_hash="4a7f8e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b785",
        is_valid=True,
        integrity_score=1.0,
        tampered_sequence_id=None,
        failure_reason=None,
        worm_checkpoints_verified=2,
        audit_duration_ms=4.2,
    )

    data = json.loads(report.model_dump_json())
    jsonschema.validate(instance=data, schema=schema)
