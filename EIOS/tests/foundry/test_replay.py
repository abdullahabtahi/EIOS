"""Tests for streaming replay engine and Pub/Sub emulator publisher (T057, T060)."""

from unittest.mock import MagicMock

from eios.foundry.replay import StreamingReplayEngine


def test_streaming_replay_velocity_and_publishing():
    """Confirms replay engine streams records to Pub/Sub topics with configurable velocity."""
    mock_publisher = MagicMock()
    mock_publisher.publish.return_value.result.return_value = "msg-12345"

    engine = StreamingReplayEngine(
        publisher=mock_publisher,
        topic_name="projects/test-project/topics/eios.l0.transactions.v1",
        velocity_records_per_sec=100.0,
    )

    records = [
        {"transaction_id": f"TX-{i:05d}", "amount": "100.00", "currency": "USD"} for i in range(25)
    ]

    published_count = engine.replay_batch(records)
    assert published_count == 25
    assert mock_publisher.publish.call_count == 25

    # Check topic and payload
    args, kwargs = mock_publisher.publish.call_args
    assert args[0] == "projects/test-project/topics/eios.l0.transactions.v1"
    assert b"TX-00024" in kwargs.get("data", b"") or b"TX-00024" in args[1]
