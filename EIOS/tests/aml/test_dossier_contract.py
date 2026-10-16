"""Contract validation test for aml-case-dossier schema (T036).

Authoritative Reference:
- specs/010-client-aml/contracts/aml-case-dossier.schema.json
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


def test_aml_case_dossier_schema_contract() -> None:
    schema_path = get_schema_path("specs/010-client-aml/contracts/aml-case-dossier.schema.json")
    assert schema_path.exists(), f"Contract schema not found: {schema_path}"

    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    sample_payload = {
        "case_id": "CASE-AML-001",
        "client_id": "C-AML-ROUNDTRIP-01",
        "as_of": "2026-10-07T12:00:00Z",
        "kyc_tier": "TIER_2_VERIFIED",
        "kyc_approved_at": "2026-10-01T10:00:00Z",
        "composite_risk_score": 0.92,
        "priority_tier": "CRITICAL",
        "recommended_action": "HoldWithdrawal",
        "total_deposit_usd": 500.0,
        "total_withdrawal_usd": 499.50,
        "net_trading_pl_usd": 0.01,
        "deposit_withdrawal_ratio": 0.999,
        "mule_ring_id": "MULE-RING-01",
        "mule_ring_size": 4,
        "citations": ["DP2:trading_activity", "DP1:transactions_aml"],
        "statutory_references": ["31 CFR 1010.410", "31 U.S.C. 5318(g)"],
        "narrative_summary": "Subject conducted a rapid deposit and micro-P&L round-trip within 24 hours of KYC verification.",
    }

    # Validate against JSON schema
    jsonschema.validate(instance=sample_payload, schema=schema)


def test_aml_case_dossier_assembler_contract_compliance() -> None:
    from eios.aml.dossier import AMLDossierAssembler

    schema_path = get_schema_path("specs/010-client-aml/contracts/aml-case-dossier.schema.json")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    assembler = AMLDossierAssembler()
    dossier = assembler.assemble_dossier(
        client_id="C-AML-TEST-CONTRACT",
        kyc_tier="TIER_2_VERIFIED",
        total_deposit=1000.0,
        total_withdrawal=990.0,
        net_pl=0.05,
        mule_ring_id="MULE-TEST-01",
        mule_ring_size=3,
    )
    contract_dict = AMLDossierAssembler.to_contract_dict(dossier)
    jsonschema.validate(instance=contract_dict, schema=schema)


def test_aml_case_dossier_zero_deposit() -> None:
    from eios.aml.dossier import AMLDossierAssembler

    assembler = AMLDossierAssembler()
    dossier = assembler.assemble_dossier(
        client_id="C-AML-ZERO-DEP",
        kyc_tier="TIER_1_VERIFIED",
        total_deposit=0.0,
        total_withdrawal=0.0,
        net_pl=0.0,
    )
    assert dossier.total_deposit_usd == 0.0
    assert dossier.deposit_withdrawal_ratio == 0.0
