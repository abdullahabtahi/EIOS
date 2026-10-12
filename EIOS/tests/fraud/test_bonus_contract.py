"""Contract validation test for client-quality-profile schema (T020).

Authoritative Reference:
- specs/009-partner-fraud/contracts/client-quality-profile.schema.json
"""

import json
from pathlib import Path
import jsonschema
import pytest


def test_client_quality_profile_schema_contract() -> None:
    schema_path = Path("specs/009-partner-fraud/contracts/client-quality-profile.schema.json")
    if not schema_path.exists():
        schema_path = Path("..") / schema_path
    assert schema_path.exists(), f"Contract schema not found: {schema_path}"

    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    sample_payload = {
        "partner_id": "P-ABUSE-100",
        "total_referred_clients": 100,
        "fast_withdrawal_count_72h": 85,
        "micro_trade_only_count": 88,
        "median_holding_duration_hours": 36.5,
        "turnover_to_deposit_ratio": 1.25,
        "cpa_bounty_collected_usd": 17000.0,
        "client_quality_index": 0.12,
        "abuse_probability": 0.88,
        "status": "HIGH_BONUS_ABUSE_RISK",
    }

    jsonschema.validate(instance=sample_payload, schema=schema)
