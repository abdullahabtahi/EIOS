"""The gateway serves the operations screen and the quarantine API from the engine service (spec 035)."""

import pytest
from fastapi.testclient import TestClient

from eios.api import routes_ops
from eios.api.app import app as api_app
from eios.cockpit import server
from eios.cockpit.server import ENGINE_DATA_BADGE, app


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, ops_models) -> TestClient:
    models, ops = ops_models
    monkeypatch.setattr(server, "operations_engine_service", lambda: ops)
    monkeypatch.setattr(server, "operations_svc", ops)
    monkeypatch.setattr(routes_ops, "operations_engine_service", lambda: ops)
    monkeypatch.setattr(routes_ops, "ops_svc", ops)
    return TestClient(app)


@pytest.fixture
def api(client: TestClient) -> TestClient:  # `client` patched the services
    return TestClient(api_app)


def test_the_workstation_carries_measured_cards_gates_quarantine_and_the_drill(
    client: TestClient,
) -> None:
    body = client.get("/api/cockpit/workstations/data_operations").json()
    assert body["fallback_state"]["badge_label"] == ENGINE_DATA_BADGE
    payload = body["kinetic_canvas"]["payload"]
    assert body["kinetic_canvas"]["canvas_type"] == "OPERATIONS_SLO"
    assert {c["product_name"] for c in payload["sla_statuses"]} >= {
        "transactions_aml",
        "partner_comms",
    }
    statuses = {b["slo_id"]: b["status"] for b in payload["error_budgets"]}
    assert (
        statuses["agent_turn_full_answer"] == "NO_DATA"
        and statuses["contract_enforcement"] == "HEALTHY"
    )
    gates = {g["gate_id"]: g["status"] for g in payload["red_line_gates"]}
    assert gates["RL-6"] == "PASS" and gates["RL-2"] == "NOT_MEASURED"
    assert payload["dlq"] and all(
        r["status"] in {"QUARANTINED", "REDRIVEN_COMMITTED"} for r in payload["dlq"]
    )
    proof = body["dr_proofs"][0]
    assert (
        proof["verification_status"] == "PASS"
        and proof["kms_keyring_rotation_status"] == "NOT_ASSESSED"
    )
    assert len(proof["backup_checkpoint_hash"]) == 64
    assert "18.4" not in str(body["active_dossier"])  # the old hand-typed streaming lag


def test_the_api_lists_the_real_quarantine_and_refuses_a_redrive_that_still_breaks(
    api: TestClient,
) -> None:
    listed = api.get("/api/v1/ops/dlq").json()
    assert listed["total_quarantined"] == len(listed["records"]) > 0
    target = next(r for r in listed["records"] if r["status"] == "QUARANTINED")
    bad = api.post("/api/v1/ops/dlq/redrive", json={"dlq_id": target["dlq_id"]})
    assert bad.status_code == 422 and "amount" in bad.json()["detail"]
    good = api.post(
        "/api/v1/ops/dlq/redrive",
        json={"dlq_id": target["dlq_id"], "sanitized_payload": {"amount": 99.0}},
    )
    assert good.status_code == 200 and good.json()["redrive_count"] >= 1
    assert api.post("/api/v1/ops/dlq/redrive", json={"dlq_id": "nope"}).status_code == 404
    telemetry = api.get("/api/v1/ops/telemetry").json()
    assert telemetry["slo_met"] is False  # a degraded product is not an SLO met
