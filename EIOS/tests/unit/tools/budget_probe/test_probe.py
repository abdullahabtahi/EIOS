"""The budget probe (FR-038, T192): build a notification, dev only, injected publisher."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

import pytest

from eios.common.errors import BoundaryValidationError, EiosError
from tests.support.budget_tree import BUDGETS_PATH, render_budgets
from tests.support.repo_builder import build_repo
from tools.budget_probe import payload as probe_payload
from tools.budget_probe.__main__ import main
from tools.budget_probe.payload import (
    PublishError,
    PubSubPublisher,
    build_message,
    load_settings,
    validate_topic,
)

TOPIC = "projects/placeholder-dev-project/topics/placeholder-budget-topic"
NOW = datetime(2026, 3, 15, 9, 30, tzinfo=UTC)
PROBE_ID = "probe-0001"


class FakePublisher:
    def __init__(self, fail: bool = False) -> None:
        self.calls: list[tuple[str, bytes, Mapping[str, str]]] = []
        self._fail = fail

    def publish(self, topic: str, data: bytes, attributes: Mapping[str, str]) -> str:
        if self._fail:
            raise PublishError("the topic rejected the message")
        self.calls.append((topic, data, dict(attributes)))
        return "message-1"


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    return build_repo(tmp_path, {BUDGETS_PATH: render_budgets()})


# --- payload ---------------------------------------------------------------------------------


def test_the_message_describes_the_chosen_threshold(repo: Path) -> None:
    message = build_message(load_settings(repo, "dev"), 80, now=NOW, probe_id=PROBE_ID)
    assert message.payload["alertThresholdExceeded"] == 0.8
    assert message.payload["budgetAmount"] == 20
    assert message.payload["costAmount"] == 16.0
    assert message.payload["currencyCode"] == "USD"
    assert message.payload["budgetDisplayName"] == "eios-dev-budget"
    assert message.payload["costIntervalStart"] == "2026-03-01T00:00:00Z"


def test_the_message_is_marked_as_a_probe_and_carries_a_correlating_id(repo: Path) -> None:
    message = build_message(load_settings(repo, "dev"), 50, now=NOW, probe_id=PROBE_ID)
    assert message.attributes["probe_id"] == PROBE_ID
    assert message.attributes["eios_probe"] == "true"
    assert message.attributes["environment"] == "dev"
    assert message.payload["eiosProbe"] is True


def test_the_wire_form_is_stable_json_of_the_payload(repo: Path) -> None:
    message = build_message(load_settings(repo, "dev"), 100, now=NOW, probe_id=PROBE_ID)
    assert json.loads(message.data) == dict(message.payload)
    assert (
        message.data
        == build_message(load_settings(repo, "dev"), 100, now=NOW, probe_id=PROBE_ID).data
    )


def test_a_default_probe_id_is_unique_per_message(repo: Path) -> None:
    settings = load_settings(repo, "dev")
    first = build_message(settings, 80, now=NOW)
    second = build_message(settings, 80, now=NOW)
    assert first.attributes["probe_id"] != second.attributes["probe_id"]


@pytest.mark.parametrize("threshold", [75, 0, -50, 1000, 80.5, True, "80"])
def test_a_threshold_that_is_not_configured_is_rejected(repo: Path, threshold: object) -> None:
    settings = load_settings(repo, "dev")
    with pytest.raises(BoundaryValidationError):
        build_message(settings, threshold, now=NOW)  # type: ignore[arg-type]


@pytest.mark.parametrize("env", ["stage", "prod-like", "prod", "", "DEV", "dev "])
def test_every_environment_but_dev_is_refused(repo: Path, env: str) -> None:
    with pytest.raises(BoundaryValidationError) as caught:
        load_settings(repo, env)
    assert "dev" in str(caught.value)


def test_a_missing_or_broken_budgets_file_is_a_typed_error(tmp_path: Path) -> None:
    with pytest.raises(EiosError):
        load_settings(tmp_path, "dev")
    broken = build_repo(tmp_path / "b", {BUDGETS_PATH: "thresholds_percent: [50\n"})
    with pytest.raises(EiosError):
        load_settings(broken, "dev")


def test_a_budgets_file_without_a_dev_amount_is_a_typed_error(tmp_path: Path) -> None:
    root = build_repo(tmp_path, {BUDGETS_PATH: render_budgets(amounts={"stage": 50})})
    with pytest.raises(EiosError):
        load_settings(root, "dev")


@pytest.mark.parametrize(
    "topic", ["", "topic", "projects//topics/x", "projects/p/topics/", "projects/p/subscriptions/s"]
)
def test_a_topic_must_be_a_full_topic_path(topic: str) -> None:
    with pytest.raises(BoundaryValidationError):
        validate_topic(topic)


def test_a_full_topic_path_is_accepted() -> None:
    assert validate_topic(TOPIC) == TOPIC


# --- command line ----------------------------------------------------------------------------


def _run(repo: Path, *args: str, publisher: FakePublisher | None = None) -> int:
    return main(["--repo-root", str(repo), *args], publisher=publisher)


def test_dry_run_prints_the_payload_and_publishes_nothing(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    publisher = FakePublisher()
    code = _run(repo, "--env", "dev", "--threshold", "80", "--dry-run", publisher=publisher)
    assert code == 0
    assert publisher.calls == []
    printed = json.loads(capsys.readouterr().out)
    assert printed["payload"]["alertThresholdExceeded"] == 0.8
    assert printed["dry_run"] is True


def test_dry_run_needs_no_topic(repo: Path) -> None:
    assert _run(repo, "--env", "dev", "--threshold", "50", "--dry-run") == 0


def test_publishing_goes_through_the_injected_publisher(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    publisher = FakePublisher()
    code = _run(repo, "--env", "dev", "--threshold", "80", "--topic", TOPIC, publisher=publisher)
    assert code == 0
    ((topic, data, attributes),) = publisher.calls
    assert topic == TOPIC
    assert json.loads(data)["alertThresholdExceeded"] == 0.8
    assert attributes["environment"] == "dev"
    out = json.loads(capsys.readouterr().out)
    assert out["message_id"] == "message-1"
    assert out["dry_run"] is False
    assert out["probe_id"] == attributes["probe_id"]


def test_the_topic_can_come_from_the_environment(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("EIOS_BUDGET_TOPIC", TOPIC)
    publisher = FakePublisher()
    assert _run(repo, "--env", "dev", "--threshold", "100", publisher=publisher) == 0
    assert publisher.calls[0][0] == TOPIC


def test_publishing_without_a_topic_exits_2_and_publishes_nothing(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("EIOS_BUDGET_TOPIC", raising=False)
    publisher = FakePublisher()
    assert _run(repo, "--env", "dev", "--threshold", "80", publisher=publisher) == 2
    assert publisher.calls == []


@pytest.mark.parametrize("env", ["stage", "prod-like"])
def test_other_environments_exit_2_and_publish_nothing(repo: Path, env: str) -> None:
    publisher = FakePublisher()
    code = _run(repo, "--env", env, "--threshold", "80", "--topic", TOPIC, publisher=publisher)
    assert code == 2
    assert publisher.calls == []


def test_dry_run_does_not_make_another_environment_acceptable(repo: Path) -> None:
    assert _run(repo, "--env", "prod-like", "--threshold", "80", "--dry-run") == 2


def test_an_unconfigured_threshold_exits_2(repo: Path) -> None:
    publisher = FakePublisher()
    assert (
        _run(repo, "--env", "dev", "--threshold", "75", "--topic", TOPIC, publisher=publisher) == 2
    )
    assert publisher.calls == []


def test_a_non_numeric_threshold_exits_2(repo: Path) -> None:
    assert _run(repo, "--env", "dev", "--threshold", "eighty", "--dry-run") == 2


def test_missing_arguments_exit_2(repo: Path) -> None:
    assert _run(repo, "--env", "dev") == 2
    assert _run(repo, "--threshold", "80") == 2


def test_a_publisher_failure_exits_2(repo: Path) -> None:
    publisher = FakePublisher(fail=True)
    assert (
        _run(repo, "--env", "dev", "--threshold", "80", "--topic", TOPIC, publisher=publisher) == 2
    )


# --- the real publisher ----------------------------------------------------------------------


def test_the_real_publisher_imports_its_client_lazily_and_reports_a_missing_library(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def refuse(name: str) -> object:
        raise ImportError(name)

    monkeypatch.setattr(probe_payload.importlib, "import_module", refuse)  # type: ignore
    publisher = PubSubPublisher()  # constructing must not import anything
    with pytest.raises(PublishError) as caught:
        publisher.publish(TOPIC, b"{}", {})
    assert "not installed" in str(caught.value)


def test_the_real_publisher_uses_the_client_it_is_given() -> None:
    class Future:
        def result(self, timeout: float) -> str:
            return "id-9"

    class Client:
        def __init__(self) -> None:
            self.sent: list[tuple[str, bytes, dict[str, str]]] = []

        def publish(self, topic: str, data: bytes, **attributes: str) -> Future:
            self.sent.append((topic, data, attributes))
            return Future()

    client = Client()
    publisher = PubSubPublisher(client=client)
    assert publisher.publish(TOPIC, b"x", {"probe_id": "p"}) == "id-9"
    assert client.sent == [(TOPIC, b"x", {"probe_id": "p"})]


def test_the_real_repository_budgets_allow_a_dev_probe_at_every_threshold() -> None:
    repo = Path(__file__).resolve().parents[4]
    settings = load_settings(repo, "dev")
    for threshold in (50, 80, 100):
        assert build_message(settings, threshold).payload["alertThresholdExceeded"] == (
            threshold / 100
        )
