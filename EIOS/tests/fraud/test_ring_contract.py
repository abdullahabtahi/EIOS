"""Contract validation test for referral-ring-attribution schema (T015).

Authoritative Reference:
- specs/009-partner-fraud/contracts/referral-ring-attribution.schema.json
"""

import json
from pathlib import Path
import jsonschema
import pytest


def test_referral_ring_attribution_schema_contract() -> None:
    schema_path = Path("specs/009-partner-fraud/contracts/referral-ring-attribution.schema.json")
    if not schema_path.exists():
        schema_path = Path("..") / schema_path
    assert schema_path.exists(), f"Contract schema not found: {schema_path}"

    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    sample_payload = {
        "ring_id": "RING-MASTER-01",
        "master_partner_id": "P-MASTER-01",
        "total_affiliated_partners": 5,
        "total_referred_clients": 100,
        "hierarchy_depth": 3,
        "total_ring_commission_usd": 29900.0,
        "flagged_abuse_commission_usd": 21400.0,
        "ring_risk_score": 0.88,
        "top_violating_sub_partners": ["P-LEAF-01-A1", "P-LEAF-01-A2"],
        "nodes": [
            {
                "partner_id": "P-MASTER-01",
                "parent_partner_id": None,
                "tier_level": 1,
                "direct_referred_clients": 5,
                "direct_commission_usd": 1500.0,
                "sub_affiliate_count": 2,
                "is_root_master": True,
            },
            {
                "partner_id": "P-SUB-01-A",
                "parent_partner_id": "P-MASTER-01",
                "tier_level": 2,
                "direct_referred_clients": 12,
                "direct_commission_usd": 4200.0,
                "sub_affiliate_count": 2,
                "is_root_master": False,
            },
            {
                "partner_id": "P-LEAF-01-A1",
                "parent_partner_id": "P-SUB-01-A",
                "tier_level": 3,
                "direct_referred_clients": 45,
                "direct_commission_usd": 12500.0,
                "sub_affiliate_count": 0,
                "is_root_master": False,
            },
        ],
    }

    jsonschema.validate(instance=sample_payload, schema=schema)
