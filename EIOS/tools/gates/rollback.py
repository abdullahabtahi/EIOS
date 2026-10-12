"""Rollback: redeploy the previous revision, toggle the rollback flag, and time the whole thing.

Callers: a rehearsal or incident driver supplies a ``Deployer`` (the real adapter lives with the
infrastructure; tests use a fake) and ``RollbackSettings``. The elapsed time is compared with the
bound read from ``config/rollback.yaml`` (never from code) and recorded on a Pipeline Run Record
as a ``rollback`` gate result, because the run-record schema has no dedicated rollback field.
A rollback that exceeds the bound still happens; it is recorded as a failed run (exit code 1).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Protocol

from pydantic import Field, field_validator

from eios.common.errors import BoundaryValidationError, ConfigError, EiosError
from eios.common.provenance import parse_tag
from eios.common.validation import StrictModel, validate_at_boundary
from tools.common.yaml_io import load_yaml
from tools.gates.run_record import (
    Clock,
    GateResult,
    Outcome,
    PipelineRunRecord,
    Workflow,
    new_record,
    write_record,
)

ROLLBACK_GATE_ID = "rollback"
EXIT_OK = 0
EXIT_OVER_BOUND = 1

NonEmpty = Annotated[str, Field(min_length=1)]


class RollbackError(EiosError):
    """A rollback step failed; the message says which step and what state was reached."""


class NoPreviousRevisionError(RollbackError):
    """There is no earlier revision to return to."""


class Deployer(Protocol):
    def current_revision(self, service: str) -> str: ...

    def previous_revision(self, service: str) -> str | None: ...

    def redeploy(self, service: str, revision: str) -> None: ...

    def set_flag(self, flag: str, value: bool) -> None: ...


class RollbackConfig(StrictModel):
    """``config/rollback.yaml``: the time bound is a tagged target, decided in T100."""

    time_bound_seconds: float = Field(gt=0)
    time_bound_tag: NonEmpty
    flag: NonEmpty

    @field_validator("time_bound_tag")
    @classmethod
    def _known_tag(cls, value: str) -> str:
        parse_tag(value)
        return value


@dataclass(frozen=True)
class RollbackSettings:
    config: RollbackConfig
    clock: Clock
    commit_ref: str
    workflow: Workflow
    tool_root: Path
    repo_root: Path | None = None  # no root: the outcome is returned but nothing is written


@dataclass(frozen=True)
class RollbackOutcome:
    from_revision: str
    to_revision: str
    elapsed_seconds: float
    within_bound: bool
    record: PipelineRunRecord
    record_path: Path | None

    @property
    def exit_code(self) -> int:
        return EXIT_OK if self.within_bound else EXIT_OVER_BOUND


def load_rollback_config(path: Path) -> RollbackConfig:
    """Load and validate the configuration; every failure is a ``ConfigError`` naming the file."""
    data = load_yaml(path)
    if not isinstance(data, dict):
        raise ConfigError(str(path), "$", "expected a mapping with the rollback settings")
    try:
        return validate_at_boundary(RollbackConfig, data)
    except BoundaryValidationError as exc:
        raise ConfigError(str(path), "$", exc.message) from None


def _redeploy(deployer: Deployer, service: str, revision: str) -> None:
    try:
        deployer.redeploy(service, revision)
    except Exception as exc:
        raise RollbackError(
            f"redeploy of {service} to {revision} failed: {exc}; the rollback flag was not set"
        ) from exc


def _toggle_flag(deployer: Deployer, flag: str, service: str, revision: str) -> None:
    try:
        deployer.set_flag(flag, True)
    except Exception as exc:
        raise RollbackError(
            f"{service} was already redeployed to {revision} but setting flag {flag} failed: {exc}"
        ) from exc


def _record_outcome(
    settings: RollbackSettings, reason: str, within_bound: bool
) -> PipelineRunRecord:
    result = GateResult(
        gate_id=ROLLBACK_GATE_ID,
        outcome=Outcome.PASS if within_bound else Outcome.FAIL,
        reason=reason,
    )
    record = new_record(settings.workflow, settings.commit_ref, settings.clock)
    return record.start_gates().with_result(result).finish(settings.clock.now())


def rollback(service: str, deployer: Deployer, settings: RollbackSettings) -> RollbackOutcome:
    """Return ``service`` to its previous revision and time it against the configured bound."""
    current = deployer.current_revision(service)
    previous = deployer.previous_revision(service)
    if previous is None:
        raise NoPreviousRevisionError(
            f"no previous revision of {service} to roll back to (current: {current})"
        )
    started = settings.clock.now()
    _redeploy(deployer, service, previous)
    _toggle_flag(deployer, settings.config.flag, service, previous)
    elapsed = (settings.clock.now() - started).total_seconds()
    bound = settings.config.time_bound_seconds
    within_bound = elapsed <= bound
    reason = (
        f"elapsed_seconds={elapsed} bound_seconds={bound} "
        f"bound_tag={settings.config.time_bound_tag} from={current} to={previous}"
    )
    record = _record_outcome(settings, reason, within_bound)
    path = (
        write_record(record, settings.repo_root, settings.tool_root)
        if settings.repo_root is not None
        else None
    )
    return RollbackOutcome(current, previous, elapsed, within_bound, record, path)
