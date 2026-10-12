"""End-to-End Pipeline Integration Test for Layer 1 Ingestion Spine & Contract Gateway (T047)."""

from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
import pytest

from eios.contracts.base import DataProductEnum, TenantEnum
from eios.ingestion.hot_state import HotStateEngine
from eios.ingestion.vault import TokenVault
from eios.ingestion.router import create_ingestion_app
from eios.ingestion.entity_resolution.coordinator import SCVCoordinator
from eios.ingestion.entity_resolution.deterministic import ClientProfileRecord


def test_full_e2e_ingestion_lifecycle():
    """Verify end-to-end integration across all 6 user stories."""
    engine = HotStateEngine()
    vault = TokenVault(master_salt=b"test-salt-secret-32bytes-01234567")
    app = create_ingestion_app(hot_state=engine, vault=vault)
    client = TestClient(app)

    # 1. Probe verification
    assert client.get("/healthz").status_code == 200
    assert client.get("/readyz").status_code == 200

    # 2. Ingest valid trade activity
    trade_evt = {
        "event_id": "99999999-0000-0000-0000-000000000001",
        "product_name": "trading_activity",
        "schema_version": "1.0.0",
        "event_timestamp": datetime.now(timezone.utc).isoformat(),
        "tenant_id": "DERIV_MFSA",
        "payload": {
            "trade_id": "TRD_E2E_01",
            "client_id": "CLI_E2E_JOHN",
            "symbol": "VOL_75",
            "side": "BUY",
            "volume": 3.0,
            "open_price": 750.25,
            "open_ts": datetime.now(timezone.utc).isoformat(),
        },
    }
    resp = client.post("/v1/events/ingest", json=trade_evt)
    assert resp.status_code == 202
    assert resp.json()["accepted_count"] == 1
    assert resp.json()["rejected_count"] == 0

    # 3. Ingest malformed event -> Zero-drop DLQ diversion
    malformed_evt = {
        "event_id": "99999999-0000-0000-0000-000000000002",
        "product_name": "trading_activity",
        "schema_version": "1.0.0",
        "event_timestamp": datetime.now(timezone.utc).isoformat(),
        "tenant_id": "DERIV_MFSA",
        "payload": {
            "trade_id": "TRD_E2E_BAD",
            "client_id": "CLI_E2E_JOHN",
            "symbol": "VOL_75",
            "side": "BUY",
            "volume": -10.0,  # Negative volume breach
            "open_price": 750.25,
            "open_ts": datetime.now(timezone.utc).isoformat(),
        },
    }
    resp_bad = client.post("/v1/events/ingest", json=malformed_evt)
    assert resp_bad.status_code == 202
    assert resp_bad.json()["accepted_count"] == 0
    assert resp_bad.json()["rejected_count"] == 1
    assert len(resp_bad.json()["breach_summary"]) == 1
    assert app.state.dlq.get_pending_count() == 1

    # 4. Ingest Client 360 with PII -> Deterministic Pseudonymization
    client_evt = {
        "event_id": "99999999-0000-0000-0000-000000000003",
        "product_name": "client_360",
        "schema_version": "1.0.0",
        "event_timestamp": datetime.now(timezone.utc).isoformat(),
        "tenant_id": "DERIV_MFSA",
        "payload": {
            "client_id": "CLI_E2E_JOHN",
            "tax_id": "TAX_JOHN_12345",
            "full_name": "Johnathan Doe",
            "email": "john.doe@deriv.com",
            "phone": "+60129876543",
            "dob": "1990-04-12",
            "country": "MYS",
            "kyc_status": "APPROVED",
        },
    }
    resp_client = client.post("/v1/events/ingest", json=client_evt)
    assert resp_client.status_code == 202
    assert resp_client.json()["accepted_count"] == 1

    # Verify DuckDB hot state contains pseudonymized data, zero plaintext PII
    cursor = engine.get_cursor()
    stored = cursor.execute("SELECT tax_id, full_name, email, phone FROM client_360 WHERE client_id = 'CLI_E2E_JOHN'").fetchone()
    assert stored is not None
    assert "john.doe@deriv.com" not in stored[2]
    assert stored[0].startswith("tok_client_")
    assert stored[1].startswith("tok_client_")
    assert stored[2].startswith("tok_client_")
    assert stored[3].startswith("tok_client_")

    # 5. Entity Resolution (SCV) with Hub Suppression
    scv = SCVCoordinator(hub_degree_threshold=5)
    p1 = ClientProfileRecord(
        account_id="MT5_JOHN",
        platform="MT5",
        tax_id="TAX_JOHN_12345",
        email_hash=vault.tokenize("email", "john.doe@deriv.com"),
        phone_hash=vault.tokenize("phone", "+60129876543"),
        device_id="shared_mac_01",
    )
    p2 = ClientProfileRecord(
        account_id="DT_JOHN",
        platform="DERIV_TRADER",
        tax_id="TAX_JOHN_12345",
        email_hash=vault.tokenize("email", "john.doe@deriv.com"),
        phone_hash=vault.tokenize("phone", "+60129876543"),
        device_id="shared_mac_01",
    )
    c1 = scv.resolve_record(p1)
    c2 = scv.resolve_record(p2)
    assert c1 == c2  # Deterministically merged

    # 6. Real-Time Data Quality & SLA Monitor status
    dq_resp = client.get("/v1/dq/status")
    assert dq_resp.status_code == 200
    dq_data = dq_resp.json()
    assert "products" in dq_data
    assert dq_data["products"]["trading_activity"]["total_events"] >= 1
    assert dq_data["products"]["client_360"]["total_events"] >= 1
