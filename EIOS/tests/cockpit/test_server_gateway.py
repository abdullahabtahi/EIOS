"""FastAPI Cockpit Server API Gateway tests."""

import json
from pathlib import Path
from fastapi.testclient import TestClient
import jsonschema
import pytest

from eios.cockpit.server import app, _build_contract_state


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def ui_contract_schema():
    schema_path = (
        Path(__file__).resolve().parents[3]
        / "specs"
        / "016-cockpit-frontend"
        / "contracts"
        / "cockpit-ui-contract.schema.json"
    )
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "UP"
    assert "EIOS" in data["engine"]


@pytest.mark.parametrize(
    "role",
    ["executive", "aml_investigator", "partner_manager", "compliance_auditor", "data_operations"],
)
def test_workstation_state_contract_conformance(client, ui_contract_schema, role):
    response = client.get(f"/api/cockpit/workstations/{role}")
    assert response.status_code == 200
    data = response.json()
    validator = jsonschema.Draft202012Validator(ui_contract_schema)
    validator.validate(data)


def test_what_if_simulation(client):
    response = client.post(
        "/api/cockpit/simulate",
        json={"shock_param": "competitor_commission_bps", "magnitude_pct": 50.0},
    )
    assert response.status_code == 200
    data = response.json()
    assert "attribution_waterfall" in data
    # Principle: waterfall attributions must sum to 100% +- 0.01%
    assert 99.99 <= data["attribution_sum_pct"] <= 100.01


def _stage(client, **overrides):
    body = {
        "action_type": "DeployRetentionVIPDeal",
        "target_entity_id": "AP-1029",
        "severity": "HIGH",
        "initiator_officer_id": "OFFICER_CHENG",
        "requires_four_eyes": True,
        "metadata": {"deal_discount_bps": 20},
    }
    return client.post("/api/cockpit/actions/stage", json={**body, **overrides})


def _authorize(client, intent_id, who):
    return client.post(
        "/api/cockpit/actions/authorize", json={"intent_id": intent_id, "authorizer_id": who}
    )


def test_stage_and_authorize_action(client):
    stage_resp = _stage(client)
    assert stage_resp.status_code == 200
    staged = stage_resp.json()
    assert staged["status"] == "STAGED"
    intent_id = staged["card"]["intent_id"]

    # The proposer cannot approve their own intent (Four-Eyes Violation)
    fail_resp = _authorize(client, intent_id, "OFFICER_CHENG")
    assert fail_resp.status_code == 400
    assert "Four-Eyes" in fail_resp.json()["detail"]

    # Dual approval needs two distinct approvers; one is not enough
    first = _authorize(client, intent_id, "OFFICER_DUAL_VALIDATOR")
    assert first.status_code == 200
    assert first.json()["status"] == "PENDING_SECOND_EYE"

    second = _authorize(client, intent_id, "OFFICER_SECOND_EYE")
    assert second.status_code == 200
    assert second.json()["status"] == "COMMITTED"


def test_staged_card_carries_a_real_verified_signature(client):
    card = _stage(client).json()["card"]
    signature = card["kms_signature"]
    assert signature["verified"] is True
    assert signature["key_id"]
    assert len(signature["signature_digest"]) > 40  # a DER ECDSA signature, not a sha256 hex digest


def test_unknown_action_type_is_rejected(client):
    resp = _stage(client, action_type="DropAllTables")
    assert resp.status_code == 422
    assert "Unknown Action Type" in resp.json()["detail"]


def test_authorizing_a_missing_intent_is_404(client):
    assert _authorize(client, "nope", "OFFICER_X").status_code == 404


def test_every_transition_is_in_the_hash_chained_ledger(client):
    from eios.cockpit import server

    before = server.governance.sequencer.current_seq
    intent_id = _stage(client).json()["card"]["intent_id"]
    _authorize(client, intent_id, "OFFICER_A")
    _authorize(client, intent_id, "OFFICER_B")
    events = [e.event_type.value for e in server.governance.sequencer.entries[before:]]
    assert events.count("PROPOSAL_CREATED") == 1
    assert events.count("APPROVAL_RECORDED") == 2
    assert "ACTION_EXECUTED" in events


def test_copilot_grounded_and_blocked_queries(client):
    # Grounded query
    grounded_resp = client.post(
        "/api/cockpit/copilot/query",
        json={"query": "What is the 30-day net deposit turnover for partner P-882?"},
    )
    assert grounded_resp.status_code == 200
    g_data = grounded_resp.json()
    assert g_data["auditor_status"] == "PASS"
    assert len(g_data["provenance_citations"]) > 0

    # Ungrounded query
    blocked_resp = client.post(
        "/api/cockpit/copilot/query",
        json={"query": "Give me an estimate without tools speculative"},
    )
    assert blocked_resp.status_code == 200
    b_data = blocked_resp.json()
    assert b_data["auditor_status"] == "BLOCKED"
    assert "Blocked" in b_data["response"]


def test_flywheel_feedback_and_ledger_verify(client):
    fb_resp = client.post(
        "/api/cockpit/flywheel/feedback",
        json={
            "case_id": "case_aml_84920",
            "feedback_type": "SAR_NARRATIVE_EDIT",
            "original_text": "Original auto narrative",
            "revised_text": "Revised operator narrative",
            "annotator_id": "INVESTIGATOR_ALICE",
            "false_positive": False,
        },
    )
    assert fb_resp.status_code == 200
    assert fb_resp.json()["status"] == "RECORDED"

    verify_resp = client.get("/api/cockpit/audit/verify")
    assert verify_resp.status_code == 200
    assert verify_resp.json()["status"] == "VALID"


def test_data_operations_dossier_narrative_is_derived_from_computed_health(client):
    """The dossier text must never claim health that the computed SLA statuses contradict."""
    data = client.get("/api/cockpit/workstations/data_operations").json()
    payload = data["kinetic_canvas"]["payload"]
    products = payload["sla_statuses"]
    gates = payload["red_line_gates"]
    summary = data["active_dossier"]["executive_summary"]

    breached = [p for p in products if p["status"] == "BREACHED"]
    degraded = [p for p in products if p["status"] == "DEGRADED"]
    passing = sum(1 for g in gates if g["status"] == "PASS")

    if breached:
        assert f"{len(breached)} of {len(products)} data products breached" in summary
        for p in breached:
            assert p["product_name"] in summary
        assert "meeting" not in summary.lower()
    elif degraded:
        assert f"{len(degraded)} of {len(products)} data products degraded" in summary
    else:
        assert f"All {len(products)} data products meeting freshness SLAs" in summary
    assert f"{passing} of {len(gates)} red-line gates passing" in summary
