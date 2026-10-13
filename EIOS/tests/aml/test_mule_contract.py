"""Contract validation test for mule-ring-cluster schema (T026).

Authoritative Reference:
- specs/010-client-aml/contracts/mule-ring-cluster.schema.json
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


def test_mule_ring_cluster_schema_contract() -> None:
    schema_path = get_schema_path("specs/010-client-aml/contracts/mule-ring-cluster.schema.json")
    assert schema_path.exists(), f"Contract schema not found: {schema_path}"

    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    sample_payload = {
        "cluster_id": "MULE-RING-001",
        "member_client_ids": ["C-MULE-01", "C-MULE-02", "C-MULE-03"],
        "shared_payment_tokens": ["tok_pay_card_alpha_99"],
        "shared_device_tokens": ["tok_dev_hw_nexus_42"],
        "shared_ip_tokens": [],
        "suppressed_hub_tokens": ["tok_ip_airport_cgnat_hub"],
        "cluster_size": 3,
        "total_volume_usd": 48500.0,
        "is_syndicate": True,
        "plain_language_explanation": "Network of 3 client accounts sharing 1 payment method and 1 hardware device ID. Public IP gateway was suppressed.",
    }

    # Validate against JSON schema
    jsonschema.validate(instance=sample_payload, schema=schema)
