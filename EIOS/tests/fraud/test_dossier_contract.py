"""Contract validation test for fraud-case-dossier schema (T033).

Authoritative Reference:
- specs/009-partner-fraud/contracts/fraud-case-dossier.schema.json
"""

import json
from pathlib import Path
import jsonschema
import pytest


def test_fraud_case_dossier_schema_contract() -> None:
    schema_path = Path("specs/009-partner-fraud/contracts/fraud-case-dossier.schema.json")
    if not schema_path.exists():
        schema_path = Path("..") / schema_path
    assert schema_path.exists(), f"Contract schema not found: {schema_path}"

    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    sample_payload = {
        "case_id": "CASE-FRAUD-001",
        "partner_id": "P-FRAUD-RING-01",
        "master_partner_id": "P-MASTER-01",
        "primary_typology": "OPPOSITE_TRADING_SYNDICATE",
        "fraud_risk_score": 0.94,
        "total_exposure_usd": 12500.0,
        "confidence_level": "CRITICAL",
        "implicated_accounts": ["ACC-OPP-A1", "ACC-OPP-B1"],
        "evidence_refs": ["trading_activity/TRD-0001", "commission_ledger/COM-001"],
        "narrative_summary": "Detected coordinated account cluster between P-FRAUD-RING-01 and P-FRAUD-RING-02 with unearned incentive volume.",
        "recommended_action": "ClawbackCommission",
        "status": "OPEN",
    }

    jsonschema.validate(instance=sample_payload, schema=schema)
