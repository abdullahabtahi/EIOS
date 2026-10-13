"""Pipeline Run Record: frozen model, state machine, schema validation and atomic writer.

Contract: schemas/pipeline-run-record.schema.json. States run
``started -> gates_running -> (passed | failed)`` and ``passed -> promoted``; a failed run
never reaches ``promoted``. Every transition returns a new record.
"""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any, Protocol

from jsonschema import Draft202012Validator
from pydantic import Field, field_validator, model_validator

from eios.common.errors import ConfigError, EiosError, ToolError
from eios.common.validation import StrictModel, validate_at_boundary

SCHEMA_RELATIVE = Path("schemas") / "pipeline-run-record.schema.json"
RECORD_DIR = Path("evals") / "reports" / "run-records"
_SAFE_ID = r"^[A-Za-z0-9][A-Za-z0-9._-]*$"

NonEmpty = Annotated[str, Field(min_length=1)]


class Workflow(StrEnum):
    PR = "pr"
    PROMOTE_STAGE = "promote-stage"
    PROMOTE_PROD_LIKE = "promote-prod-like"
    RELEASE_CANDIDATE = "release-candidate"


class RunState(StrEnum):
    STARTED = "started"
    GATES_RUNNING = "gates_running"
    PASSED = "passed"
    FAILED = "failed"
    PROMOTED = "promoted"


class Outcome(StrEnum):
    PASS = "pass"  # noqa: S105
    FAIL = "fail"
    SKIPPED_WITH_REASON = "skipped_with_reason"


class InvalidTransitionError(EiosError):
    """A state transition the run-record state machine does not allow."""


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class GateResult(StrictModel):
    """One gate outcome; ``skipped_with_reason`` always carries a non-empty reason."""

    gate_id: NonEmpty
    outcome: Outcome
    reason: NonEmpty | None = None
    report_ref: str | None = None

    @model_validator(mode="after")
    def _skip_needs_reason(self) -> GateResult:
        if self.outcome is Outcome.SKIPPED_WITH_REASON and not (self.reason or "").strip():
            raise ValueError("skipped_with_reason requires a non-empty reason")
        return self


class PipelineRunRecord(StrictModel):
    run_id: str = Field(pattern=_SAFE_ID)
    commit_ref: NonEmpty
    workflow: Workflow
    state: RunState
    gate_results: tuple[GateResult, ...] = ()
    artefact_digests: tuple[NonEmpty, ...] = ()
    sbom_ref: NonEmpty | None = None
    approver: NonEmpty | None = None
    correlation_id: NonEmpty
    started_at: datetime
    finished_at: datetime | None = None

    @field_validator("started_at", "finished_at")
    @classmethod
    def _timezone_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def _invariants(self) -> PipelineRunRecord:
        has_fail = any(r.outcome is Outcome.FAIL for r in self.gate_results)
        if has_fail and self.state in (RunState.PASSED, RunState.PROMOTED):
            raise ValueError("a run with a failed gate cannot be passed or promoted")
        prod_promoted = (
            self.workflow is Workflow.PROMOTE_PROD_LIKE and self.state is RunState.PROMOTED
        )
        if prod_promoted and self.approver is None:
            raise ValueError("prod-like promotion requires an approver")
        if self.approver is not None and not prod_promoted:
            raise ValueError("approver is only recorded when a prod-like run is promoted")
        return self

    # --- construction ---------------------------------------------------------------------

    @classmethod
    def from_document(cls, document: object) -> PipelineRunRecord:
        """Validate untrusted data (for example a record read from disk) into a record."""
        return validate_at_boundary(cls, document)

    def _evolve(self, **changes: object) -> PipelineRunRecord:
        return validate_at_boundary(type(self), {**dict(self), **changes})

    def _require_state(self, expected: RunState, action: str) -> None:
        if self.state is not expected:
            raise InvalidTransitionError(
                f"cannot {action}: run {self.run_id} is {self.state.value}, "
                f"expected {expected.value}"
            )

    # --- transitions ----------------------------------------------------------------------

    def start_gates(self) -> PipelineRunRecord:
        self._require_state(RunState.STARTED, "start gates")
        return self._evolve(state=RunState.GATES_RUNNING)

    def with_result(self, result: GateResult) -> PipelineRunRecord:
        self._require_state(RunState.GATES_RUNNING, "record a gate result")
        return self._evolve(gate_results=(*self.gate_results, result))

    def finish(self, finished_at: datetime) -> PipelineRunRecord:
        self._require_state(RunState.GATES_RUNNING, "finish")
        failed = any(r.outcome is Outcome.FAIL for r in self.gate_results)
        state = RunState.FAILED if failed else RunState.PASSED
        return self._evolve(state=state, finished_at=finished_at)

    def promote(self, *, verified_approver: str | None = None) -> PipelineRunRecord:
        """``passed -> promoted``. The approver comes only from verified identity claims."""
        self._require_state(RunState.PASSED, "promote")
        approver = (verified_approver or "").strip() or None
        if self.workflow is Workflow.PROMOTE_PROD_LIKE:
            if approver is None:
                raise InvalidTransitionError("prod-like promotion needs a verified approver")
        elif verified_approver is not None:
            raise InvalidTransitionError("an approver is only accepted for prod-like promotion")
        return self._evolve(state=RunState.PROMOTED, approver=approver)

    def with_sbom_ref(self, sbom_ref: str) -> PipelineRunRecord:
        return self._evolve(sbom_ref=sbom_ref)

    def with_artefact_digests(self, digests: tuple[str, ...]) -> PipelineRunRecord:
        """Replace the image digests; callers decide how to merge (see tools.gates.promote)."""
        return self._evolve(artefact_digests=digests)

    # --- output ---------------------------------------------------------------------------

    def to_document(self) -> dict[str, Any]:
        """JSON-ready dict in the schema's shape; absent optional fields are omitted."""
        return self.model_dump(mode="json", exclude_none=True)


def new_record(
    workflow: Workflow,
    commit_ref: str,
    clock: Clock,
    *,
    run_id: str | None = None,
    correlation_id: str | None = None,
) -> PipelineRunRecord:
    """A fresh record in ``started``; ids default to uuid4 hex."""
    return validate_at_boundary(
        PipelineRunRecord,
        {
            "run_id": uuid.uuid4().hex if run_id is None else run_id,
            "commit_ref": commit_ref,
            "workflow": workflow,
            "state": RunState.STARTED,
            "correlation_id": uuid.uuid4().hex if correlation_id is None else correlation_id,
            "started_at": clock.now(),
        },
    )


# --- schema validation and writer ---------------------------------------------------------


def _load_schema(tool_root: Path) -> dict[str, Any]:
    path = tool_root / SCHEMA_RELATIVE
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ConfigError(str(path), "$", f"cannot load run-record schema: {exc}") from exc
    if not isinstance(schema, dict):
        raise ConfigError(str(path), "$", "run-record schema must be a JSON object")
    return schema


def validate_document(document: object, tool_root: Path) -> None:
    """Validate ``document`` against the contract schema; raises ConfigError on violations."""
    validator = Draft202012Validator(_load_schema(tool_root))
    errors = sorted(validator.iter_errors(document), key=lambda e: list(map(str, e.path)))
    if errors:
        detail = "; ".join(
            f"{'.'.join(str(p) for p in e.absolute_path) or '$'}: {e.message}" for e in errors
        )
        raise ConfigError(str(SCHEMA_RELATIVE), "$", f"run record violates schema: {detail}")


def record_path(repo_root: Path, run_id: str) -> Path:
    return repo_root / RECORD_DIR / f"{run_id}.json"


def write_record(record: PipelineRunRecord, repo_root: Path, tool_root: Path) -> Path:
    """Validate against the schema, then atomically write the record; returns its path."""
    document = record.to_document()
    validate_document(document, tool_root)
    path = record_path(repo_root, record.run_id)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    except OSError as exc:
        raise ToolError(f"could not prepare run record directory {path.parent}: {exc}") from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(document, indent=2, sort_keys=True) + "\n")
        Path(tmp_name).replace(path)
    except OSError as exc:
        Path(tmp_name).unlink(missing_ok=True)
        raise ToolError(f"could not write run record {path}: {exc}") from exc
    return path


__all__ = [
    "Clock",
    "GateResult",
    "InvalidTransitionError",
    "Outcome",
    "PipelineRunRecord",
    "RunState",
    "SystemClock",
    "Workflow",
    "new_record",
    "record_path",
    "validate_document",
    "write_record",
]
