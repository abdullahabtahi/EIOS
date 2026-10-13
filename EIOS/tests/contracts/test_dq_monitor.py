"""Tests for Data Quality & Freshness SLA Monitor (US6)."""

import time
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from eios.contracts.base import DataProductEnum
from eios.ingestion.dq import DQMonitor
from eios.ingestion.router import create_ingestion_app


def test_dq_monitor_tracks_freshness_lag_and_sla():
    monitor = DQMonitor()
    product = DataProductEnum.TRANSACTIONS_AML

    # Freshness SLA for transactions_aml is 30s
    event_time_fresh = datetime.now(UTC) - timedelta(seconds=10)
    monitor.record_event(
        product,
        event_time_fresh,
        {"txn_id": "txn_01", "amount": 100.0, "currency": "USD"},
    )

    status = monitor.get_product_status(product)
    assert status.freshness_sla_met is True
    assert status.freshness_lag_seconds <= 15.0

    # Product with stream delayed by 45s (> 30s SLA)
    stale_product = DataProductEnum.TRADING_ACTIVITY
    event_time_stale = datetime.now(UTC) - timedelta(seconds=45)
    monitor.record_event(
        stale_product,
        event_time_stale,
        {"trade_id": "trd_02", "volume": 1.0},
    )
    status_stale = monitor.get_product_status(stale_product)
    assert status_stale.freshness_lag_seconds >= 40.0
    assert status_stale.freshness_sla_met is False


def test_dq_monitor_tracks_null_rates():
    monitor = DQMonitor()
    product = DataProductEnum.CLIENT_360
    now = datetime.now(UTC)

    # 10 records: 3 with partner_id None, 7 with partner_id populated
    for i in range(10):
        partner = None if i < 3 else f"partner_{i}"
        monitor.record_event(
            product,
            now,
            {"client_id": f"cli_{i}", "partner_id": partner},
        )

    null_rates = monitor.get_null_rates(product)
    assert "partner_id" in null_rates
    assert abs(null_rates["partner_id"] - 0.30) < 0.01


def test_dq_status_endpoint_performance():
    """Verify /v1/dq/status responds in <= 25ms."""
    app = create_ingestion_app()
    client = TestClient(app)

    start = time.perf_counter()
    resp = client.get("/v1/dq/status")
    duration_ms = (time.perf_counter() - start) * 1000.0

    assert resp.status_code == 200
    assert duration_ms < 25.0
    data = resp.json()
    assert "products" in data
    assert "client_360" in data["products"]
    assert "transactions_aml" in data["products"]
