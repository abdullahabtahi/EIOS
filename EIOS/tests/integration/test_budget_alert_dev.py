# ruff: noqa: E501
"""T192 cloud test: one threshold published to dev reaches the channel declared in infra code.

Skipped unless ``EIOS_TEST_CLOUD=1``. It also needs, from ``terraform output`` of ``infra/envs/dev``:

- ``EIOS_BUDGET_TOPIC``: the ``budget_topic_id`` output (``projects/<p>/topics/<t>``);
- ``EIOS_BUDGET_SUBSCRIPTION``: the ``budget_subscription_id`` output (the pull subscription the
  module attaches to that topic, so the test can read what the budget would publish to);
- ``EIOS_BUDGET_NOTIFICATION_CHANNEL`` (optional): the ``notification_channel_id`` output.

The probe publishes a synthetic budget notification; it cannot make the cloud send an email, so
email delivery stays a manual confirmation in ``docs/runbooks/budget-alert-test.md``. The channel
asserted here is the topic and subscription that ``infra/modules/budget_alerts`` declares.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from tools.budget_probe.__main__ import main

pytestmark = pytest.mark.requires_cloud

REPO = Path(__file__).resolve().parents[2]
PULL_DEADLINE_SECONDS = 60.0
PULL_BATCH = 10


def _required(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        pytest.fail(f"{name} must be set from the dev terraform outputs (see this file's header)")
    return value


def _pull_matching(subscription: str, probe_id: str) -> dict[str, object] | None:
    pubsub = pytest.importorskip("google.cloud.pubsub_v1")
    deadline = time.monotonic() + PULL_DEADLINE_SECONDS
    with pubsub.SubscriberClient() as client:
        while time.monotonic() < deadline:
            response = client.pull(
                request={"subscription": subscription, "max_messages": PULL_BATCH}
            )
            ack_ids = [m.ack_id for m in response.received_messages]
            if ack_ids:
                client.acknowledge(request={"subscription": subscription, "ack_ids": ack_ids})
            for received in response.received_messages:
                if received.message.attributes.get("probe_id") == probe_id:
                    loaded: dict[str, object] = json.loads(received.message.data)
                    return loaded
            time.sleep(2.0)
    return None


def test_a_dev_probe_is_delivered_to_the_declared_subscription(
    capsys: pytest.CaptureFixture[str],
) -> None:
    topic = _required("EIOS_BUDGET_TOPIC")
    subscription = _required("EIOS_BUDGET_SUBSCRIPTION")
    code = main(["--repo-root", str(REPO), "--env", "dev", "--threshold", "80", "--topic", topic])
    assert code == 0
    sent = json.loads(capsys.readouterr().out)
    delivered = _pull_matching(subscription, sent["probe_id"])
    assert delivered is not None, "the probe was not delivered to the declared subscription"
    assert delivered["alertThresholdExceeded"] == 0.8
    assert delivered["budgetDisplayName"] == "eios-dev-budget"


def test_the_declared_notification_channel_exists() -> None:
    channel = os.environ.get("EIOS_BUDGET_NOTIFICATION_CHANNEL", "")
    if not channel:
        pytest.skip("EIOS_BUDGET_NOTIFICATION_CHANNEL is not set")
    monitoring = pytest.importorskip("google.cloud.monitoring_v3")
    found = monitoring.NotificationChannelServiceClient().get_notification_channel(name=channel)
    assert found.type_ == "email"
