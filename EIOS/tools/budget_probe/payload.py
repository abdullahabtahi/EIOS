# ruff: noqa: E501, B904
import importlib
import json
import typing
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

import yaml

from eios.common.errors import BoundaryValidationError, EiosError


class PublishError(Exception):
    pass



class PubSubPublisher:
    def __init__(self, client: typing.Any = None) -> None:
        self._client = client

    def publish(self, topic: str, data: bytes, attributes: Mapping[str, str]) -> str:
        if self._client is None:
            try:
                pubsub_v1 = importlib.import_module("google.cloud.pubsub_v1")
                self._client = pubsub_v1.PublisherClient()
            except ImportError as e:
                raise PublishError(f"google-cloud-pubsub is not installed: {e}")
        try:
            future = self._client.publish(topic, data, **attributes)
            return str(future.result(timeout=10.0))
        except Exception as e:
            raise PublishError(str(e))


class ProbeMessage:
    def __init__(self, payload: dict[str, typing.Any], attributes: dict[str, str], data: bytes) -> None:
        self.payload = payload
        self.attributes = attributes
        self.data = data


def validate_topic(topic: str) -> str:
    if not topic or not topic.startswith("projects/") or "/topics/" not in topic:
        raise BoundaryValidationError("invalid topic")
    parts = topic.split("/")
    if len(parts) != 4 or not parts[1] or not parts[3]:
        raise BoundaryValidationError("invalid topic")
    return topic


def load_settings(repo: Path, env: str) -> dict[str, typing.Any]:
    if env != "dev":
        raise BoundaryValidationError(f"env must be dev, got {env}")
    budget_file = repo / "config" / "budgets.yaml"
    try:
        with budget_file.open() as f:
            data = yaml.safe_load(f)
    except Exception as e:
        raise EiosError(f"broken budget file: {e}")
    if not isinstance(data, dict):
        raise EiosError("budget file invalid")
    try:
        _ = data["environments"]["dev"]["amount"]
    except (KeyError, TypeError):
        raise EiosError("dev amount missing")
    return data


def build_message(
    settings: dict[str, typing.Any], threshold: float, now: datetime | None = None, probe_id: str | None = None
) -> ProbeMessage:
    if threshold not in settings.get("thresholds_percent", []):
        raise BoundaryValidationError(f"threshold {threshold} not configured")
    if now is None:
        now = datetime.now(UTC)
    if probe_id is None:
        probe_id = str(uuid.uuid4())

    amount = settings["environments"]["dev"]["amount"]
    cost = amount * (threshold / 100.0)

    payload = {
        "alertThresholdExceeded": threshold / 100.0,
        "budgetAmount": amount,
        "costAmount": cost,
        "currencyCode": settings.get("currency", "USD"),
        "budgetDisplayName": "eios-dev-budget",
        "costIntervalStart": now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "eiosProbe": True,
    }
    attributes = {"probe_id": probe_id, "eios_probe": "true", "environment": "dev"}
    data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return ProbeMessage(payload, attributes, data)
