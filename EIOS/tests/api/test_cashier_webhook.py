"""Tests for Cashier Webhook Listener & In-Line Sentinel Interception (F019 Phase 4, T016)."""

import hashlib
import hmac
import json
import time
from fastapi.testclient import TestClient
import pytest

from eios.api.app import app
from eios.api.routes_webhooks import WEBHOOK_SECRET


@pytest.fixture
def client():
    return TestClient(app)


def _sign(payload: dict) -> str:
    body = json.dumps(payload).encode("utf-8")
    return hmac.new(WEBHOOK_SECRET, body, hashlib.sha256).hexdigest()


def test_webhook_rejects_missing_signature(client):
    payload = {
        "withdrawal_id": "W-9001",
        "client_id": "CR-100",
        "amount_usd": 5000.0,
        "nonce": f"nonce_{time.time()}_1",
        "timestamp": int(time.time() * 1000),
    }
    res = client.post("/api/v1/webhooks/cashier/withdrawal", json=payload)
    assert res.status_code == 401
    assert "Invalid HMAC" in res.json()["detail"]


def test_webhook_rejects_tampered_signature(client):
    payload = {
        "withdrawal_id": "W-9002",
        "client_id": "CR-101",
        "amount_usd": 12000.0,
        "nonce": f"nonce_{time.time()}_2",
        "timestamp": int(time.time() * 1000),
    }
    res = client.post(
        "/api/v1/webhooks/cashier/withdrawal",
        json=payload,
        headers={"X-Signature-SHA256": "0000deadbeef1234567890"},
    )
    assert res.status_code == 401


def test_webhook_processes_valid_withdrawal_release(client):
    nonce = f"nonce_{time.time()}_3"
    payload = {
        "withdrawal_id": "W-9003",
        "client_id": "CR-STABLE-USER",
        "amount_usd": 500.0,
        "payment_method": "USDT_ERC20",
        "nonce": nonce,
        "timestamp": int(time.time() * 1000),
        "hours_since_deposit": 120.0,
        "recent_alert_score": 0.05,
        "market_risk_pct": 0.45,
    }
    body_bytes = json.dumps(payload).encode("utf-8")
    sig = hmac.new(WEBHOOK_SECRET, body_bytes, hashlib.sha256).hexdigest()

    res = client.post(
        "/api/v1/webhooks/cashier/withdrawal",
        data=body_bytes,
        headers={"Content-Type": "application/json", "X-Signature-SHA256": sig},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "PROCESSED"
    assert data["disposition"] == "RELEASE"
    assert data["sla_met"] is True
    assert data["evaluation_latency_ms"] < 150.0


def test_webhook_triggers_hold_on_high_risk_withdrawal(client):
    nonce = f"nonce_{time.time()}_4"
    payload = {
        "withdrawal_id": "W-9004",
        "client_id": "CR-SUSPECT-84920",
        "amount_usd": 85000.0,
        "payment_method": "USDT_TRC20",
        "nonce": nonce,
        "timestamp": int(time.time() * 1000),
        "hours_since_deposit": 0.2,  # Funds leaving in 12 minutes!
        "recent_alert_score": 0.95,
        "market_risk_pct": 0.001,  # Zero market risk taken!
    }
    body_bytes = json.dumps(payload).encode("utf-8")
    sig = hmac.new(WEBHOOK_SECRET, body_bytes, hashlib.sha256).hexdigest()

    res = client.post(
        "/api/v1/webhooks/cashier/withdrawal",
        data=body_bytes,
        headers={"Content-Type": "application/json", "X-Signature-SHA256": sig},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "PROCESSED"
    assert data["disposition"] == "HOLD"
    assert data["action_intent_id"] is not None
    assert data["sla_met"] is True


def test_webhook_rejects_replay_attack(client):
    nonce = f"nonce_replay_{time.time()}"
    payload = {
        "withdrawal_id": "W-9005",
        "client_id": "CR-REPLAY-USER",
        "amount_usd": 1500.0,
        "nonce": nonce,
        "timestamp": int(time.time() * 1000),
    }
    body_bytes = json.dumps(payload).encode("utf-8")
    sig = hmac.new(WEBHOOK_SECRET, body_bytes, hashlib.sha256).hexdigest()

    # First request succeeds
    res1 = client.post(
        "/api/v1/webhooks/cashier/withdrawal",
        data=body_bytes,
        headers={"Content-Type": "application/json", "X-Signature-SHA256": sig},
    )
    assert res1.status_code == 200

    # Second request with identical nonce is rejected with 409 Conflict
    res2 = client.post(
        "/api/v1/webhooks/cashier/withdrawal",
        data=body_bytes,
        headers={"Content-Type": "application/json", "X-Signature-SHA256": sig},
    )
    assert res2.status_code == 409
    assert "Replay attack detected" in res2.json()["detail"]


def test_deployed_environment_refuses_to_start_without_the_webhook_secret(monkeypatch):
    from eios.api.routes_webhooks import _load_webhook_secret

    monkeypatch.delenv("EIOS_CASHIER_WEBHOOK_SECRET", raising=False)
    monkeypatch.setenv("EIOS_ENVIRONMENT", "prod-like")
    with pytest.raises(RuntimeError, match="EIOS_CASHIER_WEBHOOK_SECRET"):
        _load_webhook_secret()
    monkeypatch.setenv("EIOS_CASHIER_WEBHOOK_SECRET", "from-secret-manager")
    assert _load_webhook_secret() == b"from-secret-manager"
