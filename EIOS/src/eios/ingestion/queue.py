"""Thread-safe bounded in-memory staging queue for micro-batch ingestion."""

import queue

from eios.contracts.base import DataProductEvent


class IngestionQueue:
    """Thread-safe bounded queue accumulating events for micro-batch flushing."""

    def __init__(self, maxsize: int = 10000):
        self._queue: queue.Queue[DataProductEvent] = queue.Queue(maxsize=maxsize)

    def push(self, event: DataProductEvent) -> None:
        """Push an event to the staging queue (blocks briefly on full queue)."""
        self._queue.put(event, block=True, timeout=1.0)

    def push_batch(self, events: list[DataProductEvent]) -> None:
        """Push multiple events to the staging queue."""
        for event in events:
            self.push(event)

    def drain_batch(self, max_items: int = 250) -> list[DataProductEvent]:
        """Drain up to max_items from the queue without blocking."""
        batch: list[DataProductEvent] = []
        while len(batch) < max_items:
            try:
                item = self._queue.get_nowait()
                batch.append(item)
                self._queue.task_done()
            except queue.Empty:
                break
        return batch

    def size(self) -> int:
        """Current number of items waiting in queue."""
        return self._queue.qsize()


# Global default ingestion queue instance
_default_queue: IngestionQueue | None = None


def get_ingestion_queue() -> IngestionQueue:
    """Retrieve or initialize the process-global IngestionQueue."""
    global _default_queue
    if _default_queue is None:
        _default_queue = IngestionQueue()
    return _default_queue
