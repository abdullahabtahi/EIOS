"""T024: the Pipeline Run Record model, its state machine and its schema contract."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import pytest

from eios.common.errors import BoundaryValidationError, ConfigError
from tests.support.clock import FixedClock
from tests.support.repo_builder import build_repo
from tools.gates.commit_ref import compute_commit_ref
from tools.gates.run_record import (
    GateResult,
    InvalidTransitionError,
    Outcome,
    PipelineRunRecord,
    RunState,
    Workflow,
    new_record,
    validate_document,
    write_record,
)

REPO = Path(__file__).resolve().parents[3]
CLOCK = FixedClock()
SHA = "sha256:" + "a" * 64


def _passing(gate_id: str = "lint") -> GateResult:
    return GateResult(gate_id=gate_id, outcome=Outcome.PASS, report_ref=f"evals/reports/{gate_id}")


def _failing(gate_id: str = "types") -> GateResult:
    return GateResult(gate_id=gate_id, outcome=Outcome.FAIL, report_ref=f"evals/reports/{gate_id}")


def _running(workflow: Workflow = Workflow.PR) -> PipelineRunRecord:
    return new_record(workflow, SHA, CLOCK).start_gates()


def _passed(workflow: Workflow = Workflow.PR) -> PipelineRunRecord:
    return _running(workflow).with_result(_passing()).finish(CLOCK.now())


# --- schema conformance -------------------------------------------------------------------


def test_new_record_starts_in_started_state_and_validates() -> None:
    record = new_record(Workflow.PR, SHA, CLOCK)
    assert record.state is RunState.STARTED
    assert record.gate_results == ()
    validate_document(record.to_document(), REPO)


def test_full_lifecycle_document_validates_against_schema() -> None:
    record = _running().with_result(_passing()).with_result(_failing())
    document = record.finish(CLOCK.now()).to_document()
    validate_document(document, REPO)
    assert document["state"] == "failed"
    assert document["workflow"] == "pr"
    assert [r["gate_id"] for r in document["gate_results"]] == ["lint", "types"]


def test_schema_rejects_document_missing_correlation_id() -> None:
    document = new_record(Workflow.PR, SHA, CLOCK).to_document()
    del document["correlation_id"]
    with pytest.raises(ConfigError):
        validate_document(document, REPO)


def test_schema_rejects_unknown_fields() -> None:
    document = new_record(Workflow.PR, SHA, CLOCK).to_document()
    document["quarantined_count"] = 1
    with pytest.raises(ConfigError):
        validate_document(document, REPO)


# --- state machine ------------------------------------------------------------------------


def test_passed_then_promoted() -> None:
    promoted = _passed().promote()
    assert promoted.state is RunState.PROMOTED
    validate_document(promoted.to_document(), REPO)


def test_finish_with_any_fail_ends_failed() -> None:
    record = _running().with_result(_passing()).with_result(_failing())
    assert record.finish(CLOCK.now()).state is RunState.FAILED


def test_finish_with_only_pass_or_skip_ends_passed() -> None:
    skipped = GateResult(gate_id="x", outcome=Outcome.SKIPPED_WITH_REASON, reason="quarantined")
    record = _running().with_result(_passing()).with_result(skipped)
    assert record.finish(CLOCK.now()).state is RunState.PASSED


def test_a_failed_run_never_transitions_to_promoted() -> None:
    failed = _running().with_result(_failing()).finish(CLOCK.now())
    assert failed.state is RunState.FAILED
    with pytest.raises(InvalidTransitionError):
        failed.promote()


def test_a_record_with_a_failed_gate_cannot_be_constructed_as_promoted() -> None:
    document = _passed().to_document()
    document["state"] = "promoted"
    document["gate_results"][0]["outcome"] = "fail"
    with pytest.raises(BoundaryValidationError):
        PipelineRunRecord.from_document(document)


@pytest.mark.parametrize(
    "build",
    [
        lambda: new_record(Workflow.PR, SHA, CLOCK).promote(),
        lambda: _running().promote(),
        lambda: _passed().promote().promote(),
        lambda: new_record(Workflow.PR, SHA, CLOCK).finish(CLOCK.now()),
        lambda: _passed().finish(CLOCK.now()),
        lambda: _running().start_gates(),
        lambda: _passed().with_result(_passing("late")),
        lambda: new_record(Workflow.PR, SHA, CLOCK).with_result(_passing()),
    ],
    ids=[
        "promote-from-started",
        "promote-from-gates-running",
        "promote-twice",
        "finish-from-started",
        "finish-twice",
        "start-twice",
        "result-after-finish",
        "result-before-start",
    ],
)
def test_illegal_transitions_raise(build: Any) -> None:
    with pytest.raises(InvalidTransitionError):
        build()


def test_transitions_return_new_records_and_never_mutate() -> None:
    started = new_record(Workflow.PR, SHA, CLOCK)
    running = started.start_gates()
    with_result = running.with_result(_passing())
    assert started.state is RunState.STARTED
    assert running.gate_results == ()
    assert len(with_result.gate_results) == 1
    assert started is not running


def test_record_is_frozen() -> None:
    record = new_record(Workflow.PR, SHA, CLOCK)
    with pytest.raises(Exception, match="frozen"):
        record.state = RunState.PROMOTED
    assert isinstance(record.gate_results, tuple)


# --- gate outcomes ------------------------------------------------------------------------


def test_outcome_must_be_one_of_the_three_values() -> None:
    with pytest.raises(BoundaryValidationError):
        _ = _record_with_result({"gate_id": "lint", "outcome": "unknown"})


@pytest.mark.parametrize("reason", [None, "", "   "])
def test_skipped_with_reason_requires_a_non_empty_reason(reason: str | None) -> None:
    with pytest.raises(BoundaryValidationError):
        _record_with_result({"gate_id": "lint", "outcome": "skipped_with_reason", "reason": reason})


def test_skipped_with_reason_with_a_reason_is_valid() -> None:
    record = _record_with_result(
        {"gate_id": "lint", "outcome": "skipped_with_reason", "reason": "quarantined by F01"}
    )
    validate_document(record.to_document(), REPO)


def _record_with_result(result: dict[str, object]) -> PipelineRunRecord:
    document = _running().to_document()
    document["gate_results"] = [result]
    return PipelineRunRecord.from_document(document)


# --- sbom, approver, correlation id -------------------------------------------------------


def test_release_candidate_without_sbom_ref_is_rejected_when_written(tmp_path: Path) -> None:
    record = _passed(Workflow.RELEASE_CANDIDATE)
    with pytest.raises(ConfigError):
        validate_document(record.to_document(), REPO)
    with pytest.raises(ConfigError):
        write_record(record, tmp_path, REPO)
    assert not (tmp_path / "evals" / "reports" / "run-records").exists()


def test_release_candidate_with_sbom_ref_is_valid() -> None:
    record = _passed(Workflow.RELEASE_CANDIDATE).with_sbom_ref("evals/reports/sbom/sbom.json")
    validate_document(record.to_document(), REPO)
    assert record.to_document()["sbom_ref"] == "evals/reports/sbom/sbom.json"


def test_prod_like_promotion_requires_a_verified_approver() -> None:
    with pytest.raises(InvalidTransitionError):
        _passed(Workflow.PROMOTE_PROD_LIKE).promote()
    with pytest.raises(InvalidTransitionError):
        _passed(Workflow.PROMOTE_PROD_LIKE).promote(verified_approver="  ")


def test_prod_like_promotion_records_the_verified_approver() -> None:
    record = _passed(Workflow.PROMOTE_PROD_LIKE).promote(verified_approver="alice@example.invalid")
    assert record.approver == "alice@example.invalid"
    validate_document(record.to_document(), REPO)


@pytest.mark.parametrize(
    "workflow", [Workflow.PR, Workflow.PROMOTE_STAGE, Workflow.RELEASE_CANDIDATE]
)
def test_approver_is_only_accepted_for_prod_like_promotion(workflow: Workflow) -> None:
    passed = _passed(workflow)
    with pytest.raises(InvalidTransitionError):
        passed.promote(verified_approver="alice@example.invalid")


def test_approver_cannot_arrive_through_free_text_documents() -> None:
    document = _passed().to_document()
    document["approver"] = "mallory"
    with pytest.raises(BoundaryValidationError):
        PipelineRunRecord.from_document(document)
    prod = _passed(Workflow.PROMOTE_PROD_LIKE).to_document()
    prod["approver"] = "mallory"  # not promoted yet: approver is only set by promote()
    with pytest.raises(BoundaryValidationError):
        PipelineRunRecord.from_document(prod)


def test_promoted_prod_like_document_without_approver_is_rejected() -> None:
    document = _passed(Workflow.PROMOTE_PROD_LIKE).to_document()
    document["state"] = "promoted"
    with pytest.raises(BoundaryValidationError):
        PipelineRunRecord.from_document(document)
    with pytest.raises(ConfigError):
        validate_document(document, REPO)


def test_correlation_id_is_always_set_and_unique() -> None:
    first = new_record(Workflow.PR, SHA, CLOCK)
    second = new_record(Workflow.PR, SHA, CLOCK)
    assert re.fullmatch(r"[0-9a-f]{32}", first.correlation_id)
    assert first.correlation_id != second.correlation_id
    assert first.run_id != second.run_id


def test_explicit_correlation_id_is_kept_and_empty_is_rejected() -> None:
    assert new_record(Workflow.PR, SHA, CLOCK, correlation_id="abc").correlation_id == "abc"
    with pytest.raises(BoundaryValidationError):
        new_record(Workflow.PR, SHA, CLOCK, correlation_id="")


# --- commit_ref ---------------------------------------------------------------------------


def test_commit_ref_is_a_content_hash_when_there_is_no_git_repository(tmp_path: Path) -> None:
    build_repo(tmp_path, {"a.py": "x = 1\n", "pkg/b.py": "y = 2\n"})
    ref = compute_commit_ref(tmp_path)
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", ref)
    assert compute_commit_ref(tmp_path) == ref


def test_content_hash_changes_when_a_tracked_file_changes(tmp_path: Path) -> None:
    build_repo(tmp_path, {"a.py": "x = 1\n"})
    before = compute_commit_ref(tmp_path)
    build_repo(tmp_path, {"a.py": "x = 2\n"})
    assert compute_commit_ref(tmp_path) != before


def test_content_hash_depends_on_file_names(tmp_path: Path) -> None:
    left = build_repo(tmp_path / "left", {"a.py": "x\n"})
    right = build_repo(tmp_path / "right", {"b.py": "x\n"})
    assert compute_commit_ref(left) != compute_commit_ref(right)


@pytest.mark.parametrize(
    "ignored",
    [
        ".venv/lib/x.py",
        ".git/HEAD",
        "evals/reports/gates/lint.log",
        "pkg/__pycache__/x.pyc",
        ".mypy_cache/meta.json",
        ".pytest_cache/v/cache",
        ".ruff_cache/x",
        "node_modules/pkg/index.js",
        ".coverage",
    ],
)
def test_content_hash_excludes_environment_cache_and_report_paths(
    tmp_path: Path, ignored: str
) -> None:
    build_repo(tmp_path, {"a.py": "x = 1\n"})
    before = compute_commit_ref(tmp_path)
    build_repo(tmp_path, {ignored: "noise\n"})
    assert compute_commit_ref(tmp_path) == before


def test_empty_git_directory_falls_back_to_the_content_hash(tmp_path: Path) -> None:
    build_repo(tmp_path, {"a.py": "x = 1\n"})
    plain = compute_commit_ref(tmp_path)
    (tmp_path / ".git").mkdir()
    assert compute_commit_ref(tmp_path) == plain


def test_commit_ref_uses_the_git_revision_when_a_repository_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build_repo(tmp_path / "repo", {"a.py": "x = 1\n"})
    (tmp_path / "repo" / ".git").mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_git = bin_dir / "git"
    fake_git.write_text("#!/bin/sh\necho 0123456789abcdef0123456789abcdef01234567\n")
    fake_git.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    assert compute_commit_ref(tmp_path / "repo") == "0123456789abcdef0123456789abcdef01234567"


# --- writer -------------------------------------------------------------------------------


def test_write_record_validates_then_writes_atomically(tmp_path: Path) -> None:
    record = _passed()
    path = write_record(record, tmp_path, REPO)
    assert path == tmp_path / "evals" / "reports" / "run-records" / f"{record.run_id}.json"
    written = json.loads(path.read_text(encoding="utf-8"))
    validate_document(written, REPO)
    assert written["run_id"] == record.run_id
    assert [p.name for p in path.parent.iterdir()] == [path.name]


@pytest.mark.parametrize("run_id", ["../escape", "a/b", "", ".hidden", "x y"])
def test_run_id_must_be_a_safe_file_name(run_id: str) -> None:
    with pytest.raises(BoundaryValidationError):
        new_record(Workflow.PR, SHA, CLOCK, run_id=run_id)
