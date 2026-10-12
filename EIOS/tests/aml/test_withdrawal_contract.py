"""Contract validation test for withdrawal-risk-assessment schema (T014).

Authoritative Reference:
- specs/010-client-aml/contracts/withdrawal-risk-assessment.schema.json
"""

import json
from pathlib import Path
import jsonschema
import pytest


def get_schema_path(rel_path: str) -> Path:
    candidates = [
        Path(rel_path),
        Path("..") / rel_path,
        Path(__file__).resolve().parents[3] / rel_path,
    ]
    for p in candidates:
        if p.exists():
            return p
    return candidates[0]


def test_withdrawal_risk_assessment_schema_contract() -> None:
    schema_path = get_schema_path("specs/010-client-aml/contracts/withdrawal-risk-assessment.schema.json")
    assert schema_path.exists(), f"Contract schema not found: {schema_path}"

    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    sample_payload = {
        "assessment_id": "WRA-001",
        "withdrawal_id": "WDL-1001",
        "client_id": "C-AML-ROUNDTRIP-01",
        "amount_usd": 495.0,
        "risk_score": 0.88,
        "recommendation": "PROPOSE_HOLD",
        "decision_latency_ms": 42.5,
        "intent_id": "INT-HOLD-001",
        "evaluated_at": "2026-10-07T12:00:00Z",
    }

    # Validate against JSON schema
    jsonschema.validate(instance=sample_payload, schema=schema)
