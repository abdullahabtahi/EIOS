"""T023: the gate hook registry contract (evals/registry.yaml) and how the runner applies it."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from eios.common.errors import ConfigError, ToolError
from tests.support.repo_builder import build_repo
from tools.gates.registry import (
    TIERS_BY_WORKFLOW,
    SuiteEntry,
    Tier,
    load_registry,
    tier_runs_in,
)
from tools.gates.run_record import Outcome, RunState, Workflow
from tools.gates.runner import RunOutcome, RunSettings, run_suites

REPO = Path(__file__).resolve().parents[3]
SHA = "sha256:" + "b" * 64
HEADER = "# header comment only\n"


def _py(code: str) -> list[str]:
    return ["python", "-c", code]


def _touch(name: str) -> list[str]:
    return _py(f"import pathlib; pathlib.Path('{name}').write_text('ran')")


def _write_report(report: str) -> str:
    return (
        "import pathlib; p = pathlib.Path('" + report + "'); "
        "p.parent.mkdir(parents=True, exist_ok=True); p.write_text('{}')"
    )


def _suite(suite_id: str = "smoke-one", **overrides: Any) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "id": suite_id,
        "tier": "contract",
        "command": _py(_write_report(f"evals/reports/{suite_id}.json")),
        "owner_feature": "F01",
        "report": f"evals/reports/{suite_id}.json",
    }
    entry.update(overrides)
    return entry


def _repo(tmp_path: Path, entries: list[dict[str, Any]] | str) -> Path:
    text = entries if isinstance(entries, str) else yaml.safe_dump(entries)
    return build_repo(tmp_path, {"evals/registry.yaml": text})


def _run(
    repo: Path,
    workflow: Workflow = Workflow.PR,
    tiers: frozenset[Tier] | None = None,
) -> RunOutcome:
    settings = RunSettings(
        repo_root=repo,
        tool_root=REPO,
        workflow=workflow,
        commit_ref=SHA,
        sbom_ref="evals/reports/sbom/sbom.json" if workflow is Workflow.RELEASE_CANDIDATE else None,
    )
    return run_suites(load_registry(repo / "evals" / "registry.yaml"), settings, tiers)


def _outcomes(outcome: RunOutcome) -> dict[str, Outcome]:
    return {r.gate_id: r.outcome for r in outcome.record.gate_results}


# --- empty registry -----------------------------------------------------------------------


@pytest.mark.parametrize("text", ["[]\n", HEADER + "[]\n", HEADER])
def test_empty_registry_passes_with_the_expected_message(tmp_path: Path, text: str) -> None:
    repo = _repo(tmp_path, text)
    outcome = _run(repo)
    assert outcome.record.state is RunState.PASSED
    assert outcome.exit_code == 0
    assert any("no suites registered" in m for m in outcome.messages)
    assert outcome.record.gate_results == ()


def test_the_shipped_registry_is_an_empty_list_with_a_header() -> None:
    path = REPO / "evals" / "registry.yaml"
    suites = load_registry(path)
    assert len(suites) >= 1
    assert any(s.id == "redline-hallucination" for s in suites)
    assert path.read_text(encoding="utf-8").lstrip().startswith("#")


def test_a_missing_registry_file_is_an_error_not_an_empty_pass(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        load_registry(tmp_path / "evals" / "registry.yaml")


# --- suite results ------------------------------------------------------------------------


def test_a_passing_suite_that_writes_its_report_passes_with_the_report_ref(tmp_path: Path) -> None:
    outcome = _run(_repo(tmp_path, [_suite("ok-suite")]))
    assert outcome.record.state is RunState.PASSED
    (result,) = outcome.record.gate_results
    assert result.gate_id == "ok-suite"
    assert result.outcome is Outcome.PASS
    assert result.report_ref == "evals/reports/ok-suite.json"


def test_a_suite_exiting_non_zero_fails_the_gate_and_the_run(tmp_path: Path) -> None:
    outcome = _run(_repo(tmp_path, [_suite("bad-suite", command=_py("import sys; sys.exit(3)"))]))
    assert outcome.record.state is RunState.FAILED
    assert outcome.exit_code == 1
    assert _outcomes(outcome) == {"bad-suite": Outcome.FAIL}
    assert outcome.record.gate_results[0].report_ref == "evals/reports/bad-suite.json"


def test_a_missing_command_fails_and_is_never_skipped(tmp_path: Path) -> None:
    entry = _suite("ghost", command=["definitely-not-a-real-binary-xyz"])
    outcome = _run(_repo(tmp_path, [entry]))
    assert _outcomes(outcome) == {"ghost": Outcome.FAIL}
    assert outcome.record.state is RunState.FAILED


def test_a_command_that_is_not_executable_fails(tmp_path: Path) -> None:
    repo = build_repo(tmp_path, {"scripts/noexec.sh": "#!/bin/sh\nexit 0\n"})
    (repo / "scripts" / "noexec.sh").chmod(0o644)
    _repo(tmp_path, [_suite("noexec", command=["scripts/noexec.sh"])])
    outcome = _run(repo)
    assert _outcomes(outcome) == {"noexec": Outcome.FAIL}


def test_a_string_command_is_split_like_a_shell_would(tmp_path: Path) -> None:
    command = 'python -c "' + _write_report("evals/reports/stringy.json") + '"'
    outcome = _run(_repo(tmp_path, [_suite("stringy", command=command)]))
    assert _outcomes(outcome) == {"stringy": Outcome.PASS}


def test_a_suite_that_does_not_produce_its_report_fails(tmp_path: Path) -> None:
    outcome = _run(_repo(tmp_path, [_suite("silent", command=_py("pass"))]))
    assert _outcomes(outcome) == {"silent": Outcome.FAIL}
    assert outcome.record.state is RunState.FAILED


def test_a_stale_report_from_an_earlier_run_does_not_count(tmp_path: Path) -> None:
    repo = build_repo(tmp_path, {"evals/reports/silent.json": "{}"})
    _repo(tmp_path, [_suite("silent", command=_py("pass"))])
    assert _outcomes(_run(repo)) == {"silent": Outcome.FAIL}


def test_suites_run_in_registry_order_and_one_failure_does_not_stop_the_rest(
    tmp_path: Path,
) -> None:
    entries = [
        _suite("first-suite", command=_py("import sys; sys.exit(1)")),
        _suite("second-suite"),
        _suite("third-suite", command=_py("import sys; sys.exit(2)")),
    ]
    outcome = _run(_repo(tmp_path, entries))
    assert [r.gate_id for r in outcome.record.gate_results] == [
        "first-suite",
        "second-suite",
        "third-suite",
    ]
    assert _outcomes(outcome) == {
        "first-suite": Outcome.FAIL,
        "second-suite": Outcome.PASS,
        "third-suite": Outcome.FAIL,
    }
    assert outcome.record.state is RunState.FAILED


def test_the_record_is_written_under_run_records(tmp_path: Path) -> None:
    repo = _repo(tmp_path, [_suite("ok-suite")])
    outcome = _run(repo)
    assert outcome.record_path is not None
    assert outcome.record_path.parent == repo / "evals" / "reports" / "run-records"
    assert outcome.record_path.is_file()


# --- validation before execution ----------------------------------------------------------

_BAD_ENTRIES: list[tuple[str, dict[str, Any]]] = [
    ("unknown-tier", {"tier": "smoke"}),
    ("upper-case-id", {"id": "Bad-Id"}),
    ("snake-case-id", {"id": "bad_id"}),
    ("leading-dash-id", {"id": "-bad"}),
    ("trailing-dash-id", {"id": "bad-"}),
    ("empty-id", {"id": ""}),
    ("owner-too-short", {"owner_feature": "F1"}),
    ("owner-lower-case", {"owner_feature": "f01"}),
    ("owner-too-long", {"owner_feature": "F001"}),
    ("report-outside-evals-reports", {"report": "reports/x.json"}),
    ("report-other-evals-dir", {"report": "evals/other/x.json"}),
    ("report-traversal", {"report": "evals/reports/../x.json"}),
    ("report-absolute", {"report": "/evals/reports/x.json"}),
    ("report-is-directory", {"report": "evals/reports/"}),
    ("empty-command-string", {"command": ""}),
    ("blank-command-string", {"command": "   "}),
    ("empty-command-list", {"command": []}),
    ("blank-command-token", {"command": ["python", ""]}),
    ("unknown-field", {"surprise": True}),
]


@pytest.mark.parametrize(
    "overrides", [o for _, o in _BAD_ENTRIES], ids=[i for i, _ in _BAD_ENTRIES]
)
def test_a_malformed_entry_fails_before_any_suite_runs(
    tmp_path: Path, overrides: dict[str, Any]
) -> None:
    good = _suite("good-suite", command=_touch("good-ran.txt"))
    bad = _suite("bad-suite", **overrides)
    repo = _repo(tmp_path, [good, bad])
    with pytest.raises(ConfigError):
        _run(repo)
    assert not (repo / "good-ran.txt").exists()


@pytest.mark.parametrize("missing", ["id", "tier", "command", "owner_feature", "report"])
def test_every_field_is_required(tmp_path: Path, missing: str) -> None:
    entry = _suite("good-suite")
    del entry[missing]
    with pytest.raises(ConfigError):
        _run(_repo(tmp_path, [entry]))


def test_duplicate_ids_fail_before_any_suite_runs(tmp_path: Path) -> None:
    repo = _repo(
        tmp_path,
        [_suite("same-id", command=_touch("ran-1.txt")), _suite("same-id", tier="red_line")],
    )
    with pytest.raises(ConfigError, match="same-id"):
        _run(repo)
    assert not (repo / "ran-1.txt").exists()


@pytest.mark.parametrize("text", ["id: not-a-list\n", "- just a string\n", "- [1, 2]\n", ": : :\n"])
def test_a_registry_that_is_not_a_list_of_mappings_is_rejected(tmp_path: Path, text: str) -> None:
    with pytest.raises(ConfigError):
        load_registry(_repo(tmp_path, text) / "evals" / "registry.yaml")


def test_config_errors_name_the_file_and_the_entry_path(tmp_path: Path) -> None:
    repo = _repo(tmp_path, [_suite("good-suite"), _suite("bad-suite", tier="nope")])
    with pytest.raises(ConfigError) as excinfo:
        load_registry(repo / "evals" / "registry.yaml")
    assert excinfo.value.file.endswith("registry.yaml")
    assert "[1]" in excinfo.value.path


def test_a_valid_entry_is_loaded_as_a_frozen_model(tmp_path: Path) -> None:
    repo = _repo(tmp_path, [_suite("ok-suite", command="python -m foo --bar")])
    (entry,) = load_registry(repo / "evals" / "registry.yaml")
    assert isinstance(entry, SuiteEntry)
    assert entry.tier is Tier.CONTRACT
    assert entry.command == ("python", "-m", "foo", "--bar")
    with pytest.raises(Exception, match="frozen"):
        entry.id = "other"


# --- tier by workflow matrix --------------------------------------------------------------

_MATRIX: dict[Workflow, set[Tier]] = {
    Workflow.PR: {Tier.CONTRACT, Tier.EVAL_SMOKE, Tier.RED_LINE},
    Workflow.PROMOTE_STAGE: {Tier.CONTRACT, Tier.EVAL_SMOKE, Tier.RED_LINE, Tier.VALIDATION},
    Workflow.PROMOTE_PROD_LIKE: {Tier.CONTRACT, Tier.EVAL_SMOKE, Tier.RED_LINE, Tier.VALIDATION},
    Workflow.RELEASE_CANDIDATE: set(Tier),
}


@pytest.mark.parametrize("workflow", list(Workflow))
@pytest.mark.parametrize("tier", list(Tier))
def test_tier_by_workflow_matrix(workflow: Workflow, tier: Tier) -> None:
    assert tier_runs_in(tier, workflow) is (tier in _MATRIX[workflow])


def test_sealed_runs_only_under_the_release_candidate_workflow() -> None:
    allowed = [w for w in Workflow if tier_runs_in(Tier.SEALED, w)]
    assert allowed == [Workflow.RELEASE_CANDIDATE]
    assert not tier_runs_in(Tier.VALIDATION, Workflow.PR)
    assert set(TIERS_BY_WORKFLOW) == set(Workflow)


def test_the_five_tiers_are_exactly_the_contract_tiers() -> None:
    assert {t.value for t in Tier} == {
        "contract",
        "eval_smoke",
        "red_line",
        "validation",
        "sealed",
    }


def test_a_sealed_suite_is_not_executed_by_the_pr_workflow(tmp_path: Path) -> None:
    entries = [
        _suite("sealed-one", tier="sealed", command=_touch("sealed-ran.txt")),
        _suite("valid-one", tier="validation", command=_touch("validation-ran.txt")),
        _suite("smoke-one"),
    ]
    repo = _repo(tmp_path, entries)
    outcome = _run(repo, Workflow.PR)
    assert not (repo / "sealed-ran.txt").exists()
    assert not (repo / "validation-ran.txt").exists()
    results = {r.gate_id: r for r in outcome.record.gate_results}
    assert results["smoke-one"].outcome is Outcome.PASS
    for skipped in ("sealed-one", "valid-one"):
        assert results[skipped].outcome is Outcome.SKIPPED_WITH_REASON
        assert results[skipped].reason
    assert outcome.record.state is RunState.PASSED


def test_a_sealed_suite_runs_under_the_release_candidate_workflow(tmp_path: Path) -> None:
    repo = _repo(tmp_path, [_suite("sealed-one", tier="sealed")])
    outcome = _run(repo, Workflow.RELEASE_CANDIDATE)
    assert _outcomes(outcome) == {"sealed-one": Outcome.PASS}
    assert outcome.record.sbom_ref == "evals/reports/sbom/sbom.json"


def test_an_explicit_tier_that_the_workflow_forbids_is_refused(tmp_path: Path) -> None:
    repo = _repo(tmp_path, [_suite("sealed-one", tier="sealed", command=_touch("sealed-ran.txt"))])
    with pytest.raises(ToolError, match="sealed"):
        _run(repo, Workflow.PR, tiers=frozenset({Tier.SEALED}))
    assert not (repo / "sealed-ran.txt").exists()


def test_restricting_to_one_tier_runs_only_that_tier(tmp_path: Path) -> None:
    entries = [
        _suite("contract-one"),
        _suite("smoke-one", tier="eval_smoke", command=_touch("smoke-ran.txt")),
    ]
    repo = _repo(tmp_path, entries)
    outcome = _run(repo, tiers=frozenset({Tier.CONTRACT}))
    assert _outcomes(outcome) == {"contract-one": Outcome.PASS}
    assert not (repo / "smoke-ran.txt").exists()


def test_an_empty_tier_reports_no_suites_registered(tmp_path: Path) -> None:
    repo = _repo(tmp_path, [_suite("contract-one")])
    outcome = _run(repo, tiers=frozenset({Tier.RED_LINE}))
    assert outcome.exit_code == 0
    assert any("no suites registered" in m for m in outcome.messages)
