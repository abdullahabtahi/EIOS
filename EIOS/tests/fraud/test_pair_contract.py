"""Contract validation test for opposite-trading-pairs schema (T009).

Authoritative Reference:
- specs/009-partner-fraud/contracts/opposite-trading-pairs.schema.json
"""

import json
from pathlib import Path
import jsonschema
import pytest


def test_opposite_trading_pairs_schema_contract() -> None:
    schema_path = Path("specs/009-partner-fraud/contracts/opposite-trading-pairs.schema.json")
    if not schema_path.exists():
        schema_path = Path("..") / schema_path
    assert schema_path.exists(), f"Contract schema not found: {schema_path}"

    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    sample_payload = {
        "pairs": [
            {
                "pair_id": "PAIR-OPP-001",
                "account_a": "ACC-01",
                "partner_a": "P-100",
                "account_b": "ACC-02",
                "partner_b": "P-200",
                "symbol": "EURUSD",
                "co_occurrence_count": 12,
                "timing_correlation_pct": 92.5,
                "directional_type": "OPPOSITE",
                "size_symmetry_score": 0.98,
                "combined_net_pl_usd": -15.0,
                "total_commission_extracted_usd": 1200.0,
                "zero_sum_ratio": 0.985,
                "collusion_confidence": 0.94,
            }
        ],
        "total_pairs_flagged": 1,
        "aggregate_volume_usd": 2400000.0,
        "aggregate_commission_usd": 1200.0,
    }

    # Must validate cleanly against contract schema
    jsonschema.validate(instance=sample_payload, schema=schema)
