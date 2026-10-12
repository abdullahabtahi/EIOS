"""T066 (FR-007, FR-008, FR-018): promotion rules on the Pipeline Run Record and its CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.support.clock import FixedClock
from tools.gates import promote as promote_cli
from tools.gates.promote import PromotionError, promote
from tools.gates.run_record import (
    GateResult,
    Outcome,
    PipelineRunRecord,
    RunState,
    Workflow,
    new_record,
    record_path,
    write_record,
)

REPO = Path(__file__).resolve().parents[4]
CLOCK = FixedClock()
SHA = "sha256:" + "c" * 64
DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64
APPROVER_ENV = "EIOS_VERIFIED_APPROVER"


def _gate(gate_id: str, outcome: Outcome = Outcome.PASS) -> GateResult:
    reason = "not applicable yet" if outcome is Outcome.SKIPPED_WITH_REASON else None
    return GateResult(gate_id=gate_id, outcome=outcome, reason=reason)


def _finished(
    workflow: Workflow = Workflow.PROMOTE_STAGE,
    results: tuple[GateResult, ...] = (),
    run_id: str | None = None,
) -> PipelineRunRecord:
    record = new_record(workflow, SHA, CLOCK, run_id=run_id).start_gates()
    for result in results or (_gate("validation-one"),):
        record = record.with_result(result)
    return record.finish(CLOCK.now())


# --- the state rule -----------------------------------------------------------------------


def test_promotion_moves_a_passed_run_to_promoted() -> None:
    promoted = promote(_finished())
    assert promoted.state is RunState.PROMOTED


def test_skipped_with_reason_gates_do_not_block_promotion() -> None:
    results = (_gate("one"), _gate("two", Outcome.SKIPPED_WITH_REASON))
    assert promote(_finished(results=results)).state is RunState.PROMOTED


def test_a_failed_run_never_promotes() -> None:
    failed = _finished(results=(_gate("one"), _gate("two", Outcome.FAIL)))
    assert failed.state is RunState.FAILED
    with pytest.raises(PromotionError, match="failed"):
        promote(failed)


@pytest.mark.parametrize("state", [RunState.STARTED, RunState.GATES_RUNNING, RunState.PROMOTED])
def test_only_a_passed_run_can_be_promoted(state: RunState) -> None:
    record = new_record(Workflow.PROMOTE_STAGE, SHA, CLOCK)
    if state is not RunState.STARTED:
        record = record.start_gates()
    if state is RunState.PROMOTED:
        record = promote(record.with_result(_gate("one")).finish(CLOCK.now()))
    with pytest.raises(PromotionError, match=state.value):
        promote(record)


def test_promotion_returns_a_new_record_and_leaves_the_input_unchanged() -> None:
    passed = _finished()
    promoted = promote(passed, image_digests=(DIGEST_A,))
    assert passed.state is RunState.PASSED
    assert passed.artefact_digests == ()
    assert promoted is not passed


# --- the approver rule (FR-007, FR-018) ---------------------------------------------------


@pytest.mark.parametrize("approver", [None, "", "   "])
def test_prod_like_promotion_refuses_without_a_verified_approver(approver: str | None) -> None:
    passed = _finished(Workflow.PROMOTE_PROD_LIKE)
    with pytest.raises(PromotionError, match="approver"):
        promote(passed, verified_approver=approver)


def test_prod_like_promotion_records_the_approver() -> None:
    promoted = promote(_finished(Workflow.PROMOTE_PROD_LIKE), verified_approver="reviewer-1")
    assert promoted.state is RunState.PROMOTED
    assert promoted.approver == "reviewer-1"


@pytest.mark.parametrize("workflow", [Workflow.PROMOTE_STAGE, Workflow.RELEASE_CANDIDATE])
def test_an_approver_is_only_accepted_for_prod_like(workflow: Workflow) -> None:
    record = _finished(workflow).with_sbom_ref("evals/reports/sbom/x.cdx.json")
    with pytest.raises(PromotionError, match="approver"):
        promote(record, verified_approver="someone")


# --- release candidates (FR-008) ----------------------------------------------------------


def test_a_release_candidate_refuses_without_an_sbom_ref() -> None:
    with pytest.raises(PromotionError, match="sbom_ref"):
        promote(_finished(Workflow.RELEASE_CANDIDATE))


def test_a_release_candidate_with_an_sbom_ref_promotes() -> None:
    record = _finished(Workflow.RELEASE_CANDIDATE).with_sbom_ref("evals/reports/sbom/x.cdx.json")
    assert promote(record).state is RunState.PROMOTED


# --- image digests ------------------------------------------------------------------------


def test_image_digests_are_recorded_in_order_without_duplicates() -> None:
    promoted = promote(_finished(), image_digests=(DIGEST_B, DIGEST_A, DIGEST_B))
    assert promoted.artefact_digests == (DIGEST_B, DIGEST_A)


def test_existing_digests_are_kept_and_new_ones_appended() -> None:
    passed = _finished().with_artefact_digests((DIGEST_A,))
    promoted = promote(passed, image_digests=(DIGEST_B, DIGEST_A))
    assert promoted.artefact_digests == (DIGEST_A, DIGEST_B)


@pytest.mark.parametrize(
    "bad",
    ["registry.example/app:latest", "sha256:abc", "sha256:" + "G" * 64, "", "md5:" + "a" * 32],
)
def test_images_are_referenced_by_digest_never_by_tag(bad: str) -> None:
    with pytest.raises(PromotionError, match="digest"):
        promote(_finished(), image_digests=(bad,))


def test_with_artefact_digests_returns_a_new_record_and_validates() -> None:
    base = _finished()
    updated = base.with_artefact_digests((DIGEST_A,))
    assert base.artefact_digests == ()
    assert updated.artefact_digests == (DIGEST_A,)
    document = updated.to_document()
    assert document["artefact_digests"] == [DIGEST_A]


# --- the command line ---------------------------------------------------------------------


def _persist(repo: Path, record: PipelineRunRecord) -> Path:
    return write_record(record, repo, REPO)


def _document(repo: Path, run_id: str) -> dict[str, object]:
    loaded = json.loads(record_path(repo, run_id).read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _run(repo: Path, workflow: str, *extra: str) -> int:
    return promote_cli.main(["--workflow", workflow, "--repo-root", str(repo), *extra])


def test_cli_promotes_the_passed_records_of_the_named_workflow(tmp_path: Path) -> None:
    _persist(tmp_path, _finished(run_id="stage-1"))
    _persist(tmp_path, _finished(Workflow.PR, run_id="pr-1"))
    assert _run(tmp_path, "promote-stage", "--image-digest", DIGEST_A) == 0
    stage = _document(tmp_path, "stage-1")
    assert stage["state"] == "promoted"
    assert stage["artefact_digests"] == [DIGEST_A]
    assert _document(tmp_path, "pr-1")["state"] == "passed"


def test_cli_leaves_already_promoted_records_alone(tmp_path: Path) -> None:
    _persist(tmp_path, promote(_finished(run_id="stage-1")))
    assert _run(tmp_path, "promote-stage") == 0
    assert _document(tmp_path, "stage-1")["state"] == "promoted"


def test_cli_with_no_records_for_the_workflow_is_a_tool_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _run(tmp_path, "promote-stage") == 2
    assert "no run record" in capsys.readouterr().err


def test_cli_refuses_everything_when_any_record_failed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _persist(tmp_path, _finished(run_id="good"))
    _persist(tmp_path, _finished(results=(_gate("bad", Outcome.FAIL),), run_id="bad"))
    assert _run(tmp_path, "promote-stage") == 1
    assert "bad" in capsys.readouterr().err
    assert _document(tmp_path, "good")["state"] == "passed"


def test_cli_prod_like_refuses_without_a_verified_approver(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv(APPROVER_ENV, raising=False)
    _persist(tmp_path, _finished(Workflow.PROMOTE_PROD_LIKE, run_id="prod-1"))
    assert _run(tmp_path, "promote-prod-like") == 1
    assert "approver" in capsys.readouterr().err
    assert _document(tmp_path, "prod-1")["state"] == "passed"


def test_cli_prod_like_takes_the_approver_from_the_verified_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(APPROVER_ENV, "reviewer-1,reviewer-2")
    _persist(tmp_path, _finished(Workflow.PROMOTE_PROD_LIKE, run_id="prod-1"))
    assert _run(tmp_path, "promote-prod-like") == 0
    document = _document(tmp_path, "prod-1")
    assert document["state"] == "promoted"
    assert document["approver"] == "reviewer-1,reviewer-2"


def test_cli_never_accepts_an_approver_on_the_command_line(tmp_path: Path) -> None:
    _persist(tmp_path, _finished(Workflow.PROMOTE_PROD_LIKE, run_id="prod-1"))
    assert _run(tmp_path, "promote-prod-like", "--approver", "mallory") == 2
    assert _document(tmp_path, "prod-1")["state"] == "passed"


def test_cli_stage_promotion_records_no_approver_even_if_the_variable_is_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(APPROVER_ENV, "reviewer-1")
    _persist(tmp_path, _finished(run_id="stage-1"))
    assert _run(tmp_path, "promote-stage") == 0
    assert "approver" not in _document(tmp_path, "stage-1")


def test_cli_rejects_a_bad_digest_and_an_unknown_workflow(tmp_path: Path) -> None:
    _persist(tmp_path, _finished(run_id="stage-1"))
    assert _run(tmp_path, "promote-stage", "--image-digest", "app:latest") == 1
    assert _run(tmp_path, "pr") == 2
    assert _document(tmp_path, "stage-1")["state"] == "passed"


def test_cli_reports_an_unreadable_record_as_a_tool_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = tmp_path / "evals" / "reports" / "run-records" / "broken.json"
    bad.parent.mkdir(parents=True)
    bad.write_text("{not json", encoding="utf-8")
    assert _run(tmp_path, "promote-stage") == 2
    assert "broken.json" in capsys.readouterr().err


def test_cli_release_candidate_refuses_a_record_without_an_sbom_ref(tmp_path: Path) -> None:
    # The schema rejects such a record at write time, so craft the file by hand.
    record = _finished(Workflow.RELEASE_CANDIDATE, run_id="rc-1")
    target = record_path(tmp_path, "rc-1")
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps(record.to_document()), encoding="utf-8")
    assert _run(tmp_path, "release-candidate") == 1
