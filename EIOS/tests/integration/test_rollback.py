"""T067 (FR-010, SC-009): rollback redeploys the previous revision, sets the flag, times itself."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from eios.common.errors import ConfigError
from tests.support.repo_builder import build_repo
from tools.gates.rollback import (
    NoPreviousRevisionError,
    RollbackConfig,
    RollbackError,
    RollbackSettings,
    load_rollback_config,
    rollback,
)
from tools.gates.run_record import RunState, Workflow, record_path

REPO = Path(__file__).resolve().parents[2]
SHA = "sha256:" + "d" * 64
SERVICE = "skeleton_core"
FLAG = "rollback_active"
START = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
REDEPLOY_SECONDS = 2.0
FLAG_SECONDS = 0.5


@dataclass
class SteppingClock:
    """Test clock; the fake deployer advances it, so elapsed time is exact and deterministic."""

    instant: datetime = START

    def now(self) -> datetime:
        return self.instant

    def advance(self, seconds: float) -> None:
        self.instant = self.instant + timedelta(seconds=seconds)


@dataclass
class FakeDeployer:
    history: Sequence[str]
    clock: SteppingClock
    fail_redeploy: bool = False
    fail_flag: bool = False
    deployed: list[tuple[str, str]] = field(default_factory=list)
    flags: dict[str, bool] = field(default_factory=dict)

    def current_revision(self, service: str) -> str:
        return self.history[-1]

    def previous_revision(self, service: str) -> str | None:
        return self.history[-2] if len(self.history) >= 2 else None

    def redeploy(self, service: str, revision: str) -> None:
        if self.fail_redeploy:
            raise RuntimeError("deployer unavailable")
        self.clock.advance(REDEPLOY_SECONDS)
        self.deployed.append((service, revision))

    def set_flag(self, flag: str, value: bool) -> None:
        if self.fail_flag:
            raise RuntimeError("flag store unavailable")
        self.clock.advance(FLAG_SECONDS)
        self.flags[flag] = value


def _config(bound: float = 600.0) -> RollbackConfig:
    return RollbackConfig(time_bound_seconds=bound, time_bound_tag="[TARGET]", flag=FLAG)


def _settings(
    clock: SteppingClock,
    repo: Path | None = None,
    bound: float = 600.0,
    workflow: Workflow = Workflow.PROMOTE_STAGE,
) -> RollbackSettings:
    return RollbackSettings(
        config=_config(bound),
        clock=clock,
        commit_ref=SHA,
        workflow=workflow,
        repo_root=repo,
        tool_root=REPO,
    )


def _setup(history: Sequence[str] = ("rev-1", "rev-2")) -> tuple[SteppingClock, FakeDeployer]:
    clock = SteppingClock()
    return clock, FakeDeployer(history, clock)


# --- behaviour ----------------------------------------------------------------------------


def test_rollback_redeploys_the_previous_revision_and_toggles_the_flag() -> None:
    clock, deployer = _setup()
    outcome = rollback(SERVICE, deployer, _settings(clock))
    assert deployer.deployed == [(SERVICE, "rev-1")]
    assert deployer.flags == {FLAG: True}
    assert (outcome.from_revision, outcome.to_revision) == ("rev-2", "rev-1")


def test_elapsed_time_is_measured_and_written_to_the_run_record(tmp_path: Path) -> None:
    clock, deployer = _setup()
    outcome = rollback(SERVICE, deployer, _settings(clock, tmp_path))
    assert outcome.elapsed_seconds == REDEPLOY_SECONDS + FLAG_SECONDS
    assert outcome.record_path == record_path(tmp_path, outcome.record.run_id)
    document = json.loads(outcome.record_path.read_text(encoding="utf-8"))
    (result,) = [r for r in document["gate_results"] if r["gate_id"] == "rollback"]
    assert result["outcome"] == "pass"
    assert "elapsed_seconds=2.5" in result["reason"]
    assert "bound_seconds=600.0" in result["reason"]
    assert document["state"] == "passed"
    assert document["commit_ref"] == SHA


def test_without_a_repo_root_nothing_is_written(tmp_path: Path) -> None:
    clock, deployer = _setup()
    outcome = rollback(SERVICE, deployer, _settings(clock))
    assert outcome.record_path is None
    assert not (tmp_path / "evals").exists()


def test_exceeding_the_configured_bound_is_recorded_as_a_failed_run(tmp_path: Path) -> None:
    clock, deployer = _setup()
    outcome = rollback(SERVICE, deployer, _settings(clock, tmp_path, bound=1.0))
    assert outcome.within_bound is False
    assert outcome.record.state is RunState.FAILED
    assert outcome.exit_code == 1
    assert deployer.deployed == [(SERVICE, "rev-1")]  # the rollback itself still happened


def test_within_the_bound_the_run_passes() -> None:
    clock, deployer = _setup()
    outcome = rollback(SERVICE, deployer, _settings(clock, bound=3.0))
    assert outcome.within_bound is True
    assert outcome.record.state is RunState.PASSED
    assert outcome.exit_code == 0


def test_the_bound_comes_from_the_configuration_not_the_code() -> None:
    clock_a, deployer_a = _setup()
    clock_b, deployer_b = _setup()
    tight = rollback(SERVICE, deployer_a, _settings(clock_a, bound=2.4))
    loose = rollback(SERVICE, deployer_b, _settings(clock_b, bound=2.6))
    assert (tight.within_bound, loose.within_bound) == (False, True)


# --- failures -----------------------------------------------------------------------------


def test_rollback_with_no_previous_revision_fails_clearly(tmp_path: Path) -> None:
    clock, deployer = _setup(history=("rev-1",))
    with pytest.raises(NoPreviousRevisionError, match="no previous revision"):
        rollback(SERVICE, deployer, _settings(clock, tmp_path))
    assert deployer.deployed == []
    assert deployer.flags == {}
    assert not (tmp_path / "evals").exists()


def test_a_failing_redeploy_does_not_toggle_the_flag() -> None:
    clock, deployer = _setup()
    deployer.fail_redeploy = True
    with pytest.raises(RollbackError, match="redeploy"):
        rollback(SERVICE, deployer, _settings(clock))
    assert deployer.flags == {}


def test_a_failing_flag_toggle_reports_that_the_revision_was_already_redeployed() -> None:
    clock, deployer = _setup()
    deployer.fail_flag = True
    with pytest.raises(RollbackError, match="already redeployed"):
        rollback(SERVICE, deployer, _settings(clock))
    assert deployer.deployed == [(SERVICE, "rev-1")]


# --- config/rollback.yaml -----------------------------------------------------------------


def test_the_shipped_configuration_loads_and_carries_the_target_tag() -> None:
    path = REPO / "config" / "rollback.yaml"
    config = load_rollback_config(path)
    assert config.time_bound_seconds > 0
    assert config.time_bound_tag == "[TARGET]"
    assert config.flag
    assert "T100" in path.read_text(encoding="utf-8")


def _config_file(tmp_path: Path, text: str) -> Path:
    build_repo(tmp_path, {"rollback.yaml": text})
    return tmp_path / "rollback.yaml"


def test_a_custom_configuration_is_honoured(tmp_path: Path) -> None:
    text = "time_bound_seconds: 42.5\ntime_bound_tag: '[TARGET]'\nflag: my_flag\n"
    config = load_rollback_config(_config_file(tmp_path, text))
    assert config == RollbackConfig(
        time_bound_seconds=42.5, time_bound_tag="[TARGET]", flag="my_flag"
    )


@pytest.mark.parametrize(
    "text",
    [
        "time_bound_seconds: 0\ntime_bound_tag: '[TARGET]'\nflag: f\n",
        "time_bound_seconds: -5\ntime_bound_tag: '[TARGET]'\nflag: f\n",
        "time_bound_seconds: 10\nflag: f\n",
        "time_bound_seconds: 10\ntime_bound_tag: untagged\nflag: f\n",
        "time_bound_seconds: 10\ntime_bound_tag: '[TARGET]'\n",
        "time_bound_seconds: 10\ntime_bound_tag: '[TARGET]'\nflag: f\nextra: 1\n",
        "- not\n- a mapping\n",
        "",
    ],
)
def test_a_malformed_configuration_is_a_config_error_naming_the_file(
    tmp_path: Path, text: str
) -> None:
    path = _config_file(tmp_path, text)
    with pytest.raises(ConfigError, match="rollback.yaml"):
        load_rollback_config(path)


def test_a_missing_configuration_is_a_config_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="rollback.yaml"):
        load_rollback_config(tmp_path / "rollback.yaml")
