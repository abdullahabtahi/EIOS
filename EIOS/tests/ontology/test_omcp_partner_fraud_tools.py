"""Integration tests verifying the 4 partner fraud OMCP tools on OMCPServer (T037).

Authoritative References:
- specs/009-partner-fraud/spec.md (US6, SC-004)
- specs/009-partner-fraud/contracts/
"""

import json
from pathlib import Path

import jsonschema
import pytest

from eios.ingestion.hot_state import HotStateEngine
from eios.ontology.omcp.server import OMCPServer


@pytest.fixture
def omcp_server() -> OMCPServer:
    hs = HotStateEngine()
    # Insert a sample pair into hot state
    cursor = hs.get_cursor()
    cursor.execute(
        """
        INSERT INTO partner_opposite_trading_pairs VALUES
        ('PAIR-EURUSD-01', 'P-100', 'ACC-01', 'P-200', 'ACC-02', 'EURUSD', 10, 95.0, 'OPPOSITE', -20.0, 1500.0, 0.92, CURRENT_TIMESTAMP)
        """
    )
    return OMCPServer(hot_state=hs)


def _load_contract_schema(rel_path: str) -> dict:
    p = Path(rel_path)
    if not p.exists():
        p = Path("..") / rel_path
    return json.loads(p.read_text(encoding="utf-8"))


def test_omcp_get_opposite_trading_pairs_contract(omcp_server: OMCPServer) -> None:
    schema = _load_contract_schema(
        "specs/009-partner-fraud/contracts/opposite-trading-pairs.schema.json"
    )
    res = omcp_server.call_tool(
        "get_opposite_trading_pairs", {"partner_id": "P-100"}, caller_role="ComplianceOfficer"
    )
    jsonschema.validate(instance=res, schema=schema)
    assert res["total_pairs_flagged"] == 1


def test_omcp_get_partner_referral_ring_contract(omcp_server: OMCPServer) -> None:
    schema = _load_contract_schema(
        "specs/009-partner-fraud/contracts/referral-ring-attribution.schema.json"
    )
    res = omcp_server.call_tool(
        "get_partner_referral_ring", {"partner_id": "P-100"}, caller_role="ComplianceOfficer"
    )
    jsonschema.validate(instance=res, schema=schema)
    assert res["master_partner_id"] == "P-100"


def test_omcp_get_client_quality_profile_contract(omcp_server: OMCPServer) -> None:
    schema = _load_contract_schema(
        "specs/009-partner-fraud/contracts/client-quality-profile.schema.json"
    )
    res = omcp_server.call_tool(
        "get_client_quality_profile", {"partner_id": "P-100"}, caller_role="ComplianceOfficer"
    )
    jsonschema.validate(instance=res, schema=schema)
    assert res["partner_id"] == "P-100"


def test_omcp_get_partner_fraud_dossier_contract(omcp_server: OMCPServer) -> None:
    schema = _load_contract_schema(
        "specs/009-partner-fraud/contracts/fraud-case-dossier.schema.json"
    )
    res = omcp_server.call_tool(
        "get_partner_fraud_dossier", {"partner_id": "P-100"}, caller_role="ComplianceOfficer"
    )
    jsonschema.validate(instance=res, schema=schema)
    assert res["partner_id"] == "P-100"
    assert res["status"] == "OPEN"
