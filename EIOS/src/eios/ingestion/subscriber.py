"""Google Cloud Pub/Sub background subscriber worker for real-time telemetry."""

import json
import logging
from typing import Any

from eios.contracts.base import DataProductEvent
from eios.ingestion.config import IngestionConfig, get_ingestion_config
from eios.ingestion.processor import IngestionPipeline
from eios.ingestion.queue import IngestionQueue, get_ingestion_queue

logger = logging.getLogger(__name__)


class IngestionSubscriber:
    """Asynchronous subscriber worker consuming from Cloud Pub/Sub with pipeline governance."""

    def __init__(
        self,
        config: IngestionConfig | None = None,
        queue: IngestionQueue | None = None,
        pipeline: IngestionPipeline | None = None,
    ):
        self.config = config or get_ingestion_config()
        self.queue = queue or get_ingestion_queue()
        self.pipeline = pipeline or IngestionPipeline(config=self.config, queue=self.queue)
        self._future = None
        self._subscriber_client = None

    def handle_message(self, message: Any) -> None:
        """Process an individual incoming Pub/Sub message through unified pipeline."""
        try:
            raw_data = message.data
            if isinstance(raw_data, bytes):
                raw_data = raw_data.decode("utf-8")
            data_dict = json.loads(raw_data)

            event = DataProductEvent.model_validate(data_dict)
            self.pipeline.process_event(event)
            message.ack()
        except Exception as exc:
            logger.error("Failed to process Pub/Sub message: %s", exc, exc_info=True)
            message.nack()

    def start(self) -> None:
        """Start background streaming pull with flow control."""
        try:
            from google.cloud import pubsub_v1

            self._subscriber_client = pubsub_v1.SubscriberClient()
            subscription_path = self._subscriber_client.subscription_path(
                self.config.pubsub_project_id,
                self.config.pubsub_subscription_id,
            )
            flow_control = pubsub_v1.types.FlowControl(
                max_messages=self.config.flow_control_max_messages,
                max_bytes=self.config.flow_control_max_bytes,
            )
            self._future = self._subscriber_client.subscribe(
                subscription_path,
                callback=self.handle_message,
                flow_control=flow_control,
            )
            logger.info("Pub/Sub subscriber listening on %s", subscription_path)
        except Exception as exc:
            logger.warning("Pub/Sub client initialization skipped or offline in dev: %s", exc)

    def stop(self) -> None:
        """Stop background subscriber and cancel subscription future."""
        if self._future:
            self._future.cancel()
            self._future = None
        if self._subscriber_client:
            self._subscriber_client.close()
            self._subscriber_client = None
