"""Contract validation test for sar-draft schema (T037).

Authoritative Reference:
- specs/010-client-aml/contracts/sar-draft.schema.json
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


def test_sar_draft_schema_contract() -> None:
    schema_path = get_schema_path("specs/010-client-aml/contracts/sar-draft.schema.json")
    assert schema_path.exists(), f"Contract schema not found: {schema_path}"

    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    sample_payload = {
        "sar_id": "SAR-2026-001",
        "case_id": "CASE-AML-001",
        "client_id": "C-AML-ROUNDTRIP-01",
        "jurisdiction": "US_FINCEN",
        "filing_type": "INITIAL",
        "subject_info": {
            "client_id": "C-AML-ROUNDTRIP-01",
            "kyc_status": "VERIFIED",
            "country": "US",
        },
        "suspicious_activity_summary": "Structuring and rapid micro-P&L movement within 24h of KYC approval.",
        "chronological_transactions": [
            {
                "date": "2026-10-01",
                "type": "DEPOSIT",
                "amount": 500.0,
                "currency": "USD",
                "details": "Initial account deposit",
            },
            {
                "date": "2026-10-01",
                "type": "TRADE",
                "amount": 0.01,
                "currency": "USD",
                "details": "10-minute micro-trade with negligible market exposure",
            },
            {
                "date": "2026-10-01",
                "type": "WITHDRAWAL",
                "amount": 499.50,
                "currency": "USD",
                "details": "Full withdrawal request",
            },
        ],
        "narrative_basis": "The subject engaged in a zero-market-risk round-trip transaction sequence pursuant to 31 CFR 1010.",
        "statutory_provisions": ["31 CFR 1010", "31 U.S.C. 5318(g)"],
        "evidence_citations": ["DP1:transactions_aml", "DP2:trading_activity"],
        "created_at": "2026-10-07T12:00:00Z",
        "is_replay_fallback": False,
    }

    # Validate against JSON schema
    jsonschema.validate(instance=sample_payload, schema=schema)


def test_sar_composer_contract_compliance() -> None:
    from eios.aml.dossier import AMLDossierAssembler
    from eios.aml.sar_composer import SARComposer

    schema_path = get_schema_path("specs/010-client-aml/contracts/sar-draft.schema.json")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    assembler = AMLDossierAssembler()
    composer = SARComposer()

    dossier = assembler.assemble_dossier(
        client_id="C-AML-TEST-SAR",
        kyc_tier="TIER_2_VERIFIED",
        total_deposit=500.0,
        total_withdrawal=499.50,
        net_pl=0.01,
        mule_ring_id="MULE-01",
        mule_ring_size=4,
    )
    sar = composer.compose_sar(dossier, jurisdiction="US_FINCEN")
    contract_dict = SARComposer.to_contract_dict(sar)
    jsonschema.validate(instance=contract_dict, schema=schema)
