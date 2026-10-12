"""Tests for FastAPI Ingestion Router and Webhook Ingress (US1)."""

import time
from fastapi.testclient import TestClient
import pytest

from eios.ingestion.router import create_ingestion_app


@pytest.fixture
def api_client() -> TestClient:
    app = create_ingestion_app()
    return TestClient(app)


def test_healthz_liveness_probe(api_client: TestClient):
    """Test that /healthz responds with 200 OK immediately."""
    response = api_client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "LIVE"


def test_ingest_single_event_returns_202_fast(api_client: TestClient):
    """Test POST /v1/events/ingest with single event returns HTTP 202 under 50ms."""
    event_payload = {
        "event_id": "11111111-2222-3333-4444-555555555555",
        "product_name": "trading_activity",
        "schema_version": "1.0.0",
        "event_timestamp": "2026-10-04T12:00:00Z",
        "tenant_id": "DERIV_MFSA",
        "payload": {
            "trade_id": "TRD_98241029",
            "client_id": "CR84920",
            "symbol": "BOOM_1000",
            "side": "BUY",
            "volume": 2.5,
            "open_price": 1042.50,
            "open_ts": "2026-10-04T12:00:00Z",
        },
    }

    start = time.perf_counter()
    response = api_client.post("/v1/events/ingest", json=event_payload)
    duration_ms = (time.perf_counter() - start) * 1000.0

    assert response.status_code == 202
    assert duration_ms < 50.0  # SC-001 sub-50ms target
    data = response.json()
    assert data["status"] == "ACCEPTED"
    assert data["accepted_count"] == 1
    assert data["rejected_count"] == 0
    assert "receipt_id" in data


def test_ingest_batch_events_returns_202(api_client: TestClient):
    """Test POST /v1/events/ingest with multiple events."""
    events = [
        {
            "event_id": f"00000000-0000-0000-0000-{i:012d}",
            "product_name": "trading_activity",
            "schema_version": "1.0.0",
            "event_timestamp": "2026-10-04T12:00:00Z",
            "tenant_id": "DERIV_MFSA",
            "payload": {
                "trade_id": f"TRD_{i:06d}",
                "client_id": f"CR_{i:04d}",
                "symbol": "VOL_75",
                "side": "BUY",
                "volume": 1.0,
                "open_price": 500.0,
                "open_ts": "2026-10-04T12:00:00Z",
            },
        }
        for i in range(5)
    ]

    response = api_client.post("/v1/events/ingest", json=events)
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "ACCEPTED"
    assert data["accepted_count"] == 5
    assert data["rejected_count"] == 0


def test_ingest_malformed_json_returns_400(api_client: TestClient):
    """Test that malformed JSON request bodies are rejected with 400 Bad Request."""
    response = api_client.post(
        "/v1/events/ingest",
        content="invalid-json-string{",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code in (400, 422)


def test_ingest_contract_breach_routes_to_dlq(api_client: TestClient):
    """Test that payload violating contract schema is diverted to DLQ with zero loss."""
    event_payload = {
        "event_id": "22222222-3333-4444-5555-666666666666",
        "product_name": "trading_activity",
        "schema_version": "1.0.0",
        "event_timestamp": "2026-10-04T12:00:00Z",
        "tenant_id": "DERIV_MFSA",
        "payload": {
            "trade_id": "TRD_98241029",
            "client_id": "CR84920",
            "symbol": "BOOM_1000",
            "side": "BUY",
            "volume": -5.0,  # Range violation: gt=0.0
            "open_price": 1042.50,
            "open_ts": "2026-10-04T12:00:00Z",
        },
    }
    response = api_client.post("/v1/events/ingest", json=event_payload)
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "ACCEPTED"
    assert data["accepted_count"] == 0
    assert data["rejected_count"] == 1
    assert len(data["breach_summary"]) == 1
    assert "dlq_id" in data["breach_summary"][0]

