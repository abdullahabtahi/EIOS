"""Streaming Pub/Sub replay engine for Layer 1 ingestion replay (FR-007)."""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional
from google.cloud import pubsub_v1


class StreamingReplayEngine:
    """Replays synthetic Parquet and batch records as real-time streaming Pub/Sub events."""

    def __init__(
        self,
        publisher: Optional[Any] = None,
        topic_name: str = "projects/feios-synthetic-dev/topics/eios.l0.transactions.v1",
        velocity_records_per_sec: float = 100.0,
    ) -> None:
        self.publisher = publisher or pubsub_v1.PublisherClient()
        self.topic_name = topic_name
        self.velocity_records_per_sec = velocity_records_per_sec

    def replay_batch(self, records: List[Dict[str, Any]]) -> int:
        """Publishes records to the configured Pub/Sub topic respecting velocity throttle."""
        sleep_interval = 1.0 / self.velocity_records_per_sec if self.velocity_records_per_sec > 0 else 0.0
        published_count = 0

        for record in records:
            payload = json.dumps(record, default=str).encode("utf-8")
            future = self.publisher.publish(self.topic_name, data=payload)
            if hasattr(future, "result"):
                future.result()
            published_count += 1

            if sleep_interval > 0 and published_count < len(records):
                time.sleep(sleep_interval)

        return published_count
