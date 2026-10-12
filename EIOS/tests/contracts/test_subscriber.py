"""Tests for Pub/Sub Ingestion Subscriber Worker (US1)."""

import json
from unittest.mock import MagicMock
import pytest

from eios.contracts.base import DataProductEvent
from eios.ingestion.subscriber import IngestionSubscriber


def test_subscriber_message_ack_on_success():
    """Verify subscriber acknowledges valid incoming messages."""
    mock_queue = MagicMock()
    subscriber = IngestionSubscriber(queue=mock_queue)

    mock_msg = MagicMock()
    valid_payload = {
        "event_id": "22222222-3333-4444-5555-666666666666",
        "product_name": "trading_activity",
        "schema_version": "1.0.0",
        "event_timestamp": "2026-10-04T12:00:00Z",
        "tenant_id": "DERIV_MFSA",
        "payload": {
            "trade_id": "TRD_99999",
            "client_id": "CR12345",
            "symbol": "VOL_75",
            "side": "BUY",
            "volume": 1.0,
            "open_price": 500.0,
            "open_ts": "2026-10-04T12:00:00Z",
        },
    }
    mock_msg.data = json.dumps(valid_payload).encode("utf-8")

    subscriber.handle_message(mock_msg)

    # Assert queue received event and message was acknowledged
    assert mock_queue.push.called
    mock_msg.ack.assert_called_once()
    assert not mock_msg.nack.called


def test_subscriber_message_nack_on_transient_error():
    """Verify subscriber nacks message when unexpected internal failure occurs."""
    mock_queue = MagicMock()
    mock_queue.push.side_effect = RuntimeError("Temporary memory buffer error")
    subscriber = IngestionSubscriber(queue=mock_queue)

    mock_msg = MagicMock()
    mock_msg.data = b'{"event_id": "invalid"}'

    subscriber.handle_message(mock_msg)

    # In case of internal processing error, message must be nacked for redelivery
    mock_msg.nack.assert_called_once()
    assert not mock_msg.ack.called


def test_subscriber_diverts_malformed_event_to_dlq_and_acks():
    """Verify subscriber safely diverts contract breach to DLQ and acknowledges message."""
    mock_queue = MagicMock()
    mock_dlq = MagicMock()
    from eios.ingestion.processor import IngestionPipeline
    pipeline = IngestionPipeline(queue=mock_queue, dlq_dispatcher=mock_dlq)
    subscriber = IngestionSubscriber(queue=mock_queue, pipeline=pipeline)

    mock_msg = MagicMock()
    breach_payload = {
        "event_id": "33333333-3333-4444-5555-666666666666",
        "product_name": "trading_activity",
        "schema_version": "1.0.0",
        "event_timestamp": "2026-10-04T12:00:00Z",
        "tenant_id": "DERIV_MFSA",
        "payload": {
            "trade_id": "TRD_99999",
            "client_id": "CR12345",
            "symbol": "VOL_75",
            "side": "BUY",
            "volume": -50.0,  # Negative volume range breach
            "open_price": 500.0,
            "open_ts": "2026-10-04T12:00:00Z",
        },
    }
    mock_msg.data = json.dumps(breach_payload).encode("utf-8")

    subscriber.handle_message(mock_msg)

    # Message is safely captured in DLQ, so message is acked and not lost
    mock_dlq.create_breach_record.assert_called_once()
    mock_msg.ack.assert_called_once()
    assert not mock_queue.push.called
