"""Tests for Unified Ingestion Pipeline Core (processor.py)."""

from datetime import UTC, datetime

import pytest

from eios.contracts.base import DataProductEnum, DataProductEvent, TenantEnum
from eios.ingestion.processor import IngestionPipeline
from eios.ingestion.queue import IngestionQueue


@pytest.fixture
def pipeline() -> IngestionPipeline:
    return IngestionPipeline(queue=IngestionQueue())


def test_pipeline_processes_valid_event_end_to_end(pipeline: IngestionPipeline):
    event = DataProductEvent(
        product_name=DataProductEnum.TRADING_ACTIVITY,
        tenant_id=TenantEnum.DERIV_MFSA,
        event_timestamp=datetime.now(UTC),
        payload={
            "trade_id": "trd_pipe_001",
            "client_id": "cli_pipe_001",
            "symbol": "VOL_75",
            "side": "BUY",
            "volume": 2.0,
            "open_price": 600.0,
            "open_ts": datetime.now(UTC).isoformat(),
        },
    )

    result = pipeline.process_event(event)
    assert result.is_accepted is True
    assert result.dlq_id is None
    assert pipeline.queue.size() == 1

    # Verify event stored in hot state
    cursor = pipeline.hot_state.get_cursor()
    row = cursor.execute(
        "SELECT trade_id, symbol FROM trading_activity WHERE trade_id = 'trd_pipe_001'"
    ).fetchone()
    assert row == ("trd_pipe_001", "VOL_75")


def test_pipeline_diverts_breach_to_dlq(pipeline: IngestionPipeline):
    event = DataProductEvent(
        product_name=DataProductEnum.TRADING_ACTIVITY,
        tenant_id=TenantEnum.DERIV_MFSA,
        event_timestamp=datetime.now(UTC),
        payload={
            "trade_id": "trd_pipe_bad",
            "client_id": "cli_pipe_001",
            "symbol": "VOL_75",
            "side": "BUY",
            "volume": -10.0,  # Negative volume range breach
            "open_price": 600.0,
            "open_ts": datetime.now(UTC).isoformat(),
        },
    )

    result = pipeline.process_event(event)
    assert result.is_accepted is False
    assert result.dlq_id is not None
    assert len(result.errors) > 0
    assert pipeline.queue.size() == 0
    assert pipeline.dlq_dispatcher.get_pending_count() == 1


def test_pipeline_pseudonymizes_pii_before_hot_state(pipeline: IngestionPipeline):
    raw_email = "pipe_vip@deriv.com"
    event = DataProductEvent(
        product_name=DataProductEnum.CLIENT_360,
        tenant_id=TenantEnum.DERIV_MFSA,
        event_timestamp=datetime.now(UTC),
        payload={
            "client_id": "cli_pipe_vip",
            "tax_id": "TAX_PIPE_001",
            "full_name": "Pipeline VIP User",
            "email": raw_email,
            "phone": "+60123344556",
            "dob": "1992-05-10",
            "country": "MYS",
            "kyc_status": "APPROVED",
        },
    )

    result = pipeline.process_event(event)
    assert result.is_accepted is True

    # Hot state must not have raw email
    cursor = pipeline.hot_state.get_cursor()
    row = cursor.execute("SELECT email FROM client_360 WHERE client_id = 'cli_pipe_vip'").fetchone()
    assert row is not None
    assert raw_email not in row[0]
    assert row[0].startswith("tok_client_")
