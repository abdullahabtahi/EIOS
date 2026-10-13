"""Tests asserting zero plaintext PII leakage in Hot State and API (RL-5, US5)."""

from fastapi.testclient import TestClient

from eios.ingestion.hot_state import HotStateEngine
from eios.ingestion.router import create_ingestion_app
from eios.ingestion.vault import TokenVault


def test_zero_raw_pii_in_hot_state_after_ingestion():
    """Ensure raw PII fields are pseudonymized with tok_client_ before DuckDB storage."""
    vault = TokenVault(master_salt=b"test-salt-secret-32bytes-01234567")
    engine = HotStateEngine()
    app = create_ingestion_app(hot_state=engine)
    app.state.vault = vault

    raw_email = "super_secret_vip@deriv.com"
    raw_tax = "TAX_MY_998877"
    raw_phone = "+60199887766"
    raw_name = "Alexander Hamilton"

    event_payload = {
        "event_id": "33333333-4444-5555-6666-777777777777",
        "product_name": "client_360",
        "schema_version": "1.0.0",
        "event_timestamp": "2026-10-04T12:00:00Z",
        "tenant_id": "DERIV_MFSA",
        "payload": {
            "client_id": "cli_vip_001",
            "tax_id": raw_tax,
            "full_name": raw_name,
            "email": raw_email,
            "phone": raw_phone,
            "dob": "1985-06-15",
            "country": "MYS",
            "kyc_status": "APPROVED",
            "declared_monthly_income": 25000.0,
            "lifetime_value": 50000.0,
            "segment": "VIP",
        },
    }

    client = TestClient(app)
    resp = client.post("/v1/events/ingest", json=event_payload)
    assert resp.status_code == 202
    assert resp.json()["accepted_count"] == 1

    # Query DuckDB hot state directly
    cursor = engine.get_cursor()
    row = cursor.execute(
        "SELECT tax_id, full_name, email, phone FROM client_360 WHERE client_id = 'cli_vip_001'"
    ).fetchone()
    assert row is not None
    tax_id_stored, name_stored, email_stored, phone_stored = row

    # CRITICAL: Plaintext PII MUST NOT exist in hot state (Principle IV, RL-5)
    assert raw_tax not in tax_id_stored
    assert raw_name not in name_stored
    assert raw_email not in email_stored
    assert raw_phone not in phone_stored

    # Must be tokenized
    assert tax_id_stored.startswith("tok_client_")
    assert name_stored.startswith("tok_client_")
    assert email_stored.startswith("tok_client_")
    assert phone_stored.startswith("tok_client_")
