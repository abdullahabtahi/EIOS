"""Contract validation test for roundtrip-structuring-alerts schema (T020).

Authoritative Reference:
- specs/010-client-aml/contracts/roundtrip-structuring-alerts.schema.json
"""

import json
from pathlib import Path

import jsonschema


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


def test_roundtrip_structuring_alerts_schema_contract() -> None:
    schema_path = get_schema_path(
        "specs/010-client-aml/contracts/roundtrip-structuring-alerts.schema.json"
    )
    assert schema_path.exists(), f"Contract schema not found: {schema_path}"

    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    sample_payload = {
        "alerts": [
            {
                "event_id": "EV-RT-001",
                "client_id": "C-AML-ROUNDTRIP-01",
                "deposit_txn_id": "TXN-DEP-001",
                "withdrawal_txn_id": "TXN-WDL-001",
                "deposit_amount_usd": 500.0,
                "withdrawal_amount_usd": 499.50,
                "trade_count": 1,
                "net_pl_usd": 0.01,
                "market_risk_pct": 0.00002,
                "holding_duration_seconds": 600.0,
                "hours_since_kyc": 12.0,
                "typology_risk_score": 0.94,
            }
        ],
        "total_detected": 1,
        "window_hours": 72.0,
        "evaluated_at": "2026-10-07T12:00:00Z",
    }

    # Validate against JSON schema
    jsonschema.validate(instance=sample_payload, schema=schema)
