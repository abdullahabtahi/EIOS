"""T026: the gate runner executes config gates in order and records every outcome."""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

import pytest

from tests.support.clock import FixedClock
from tests.support.repo_builder import build_repo
from tools.gates.gate_config import GateSpec
from tools.gates.run_record import GateResult, Outcome, RunState, Workflow, validate_document
from tools.gates.runner import RunOutcome, RunSettings, format_summary, run_gates

REPO = Path(__file__).resolve().parents[4]
SHA = "sha256:" + "c" * 64


def _gate(
    gate_id: str,
    *commands: tuple[str, ...],
    threshold: int | float | None = None,
) -> GateSpec:
    return GateSpec(
        id=gate_id,
        blocking=True,
        stage="pr",
        threshold=threshold,
        proof_fixture=f"tests/fixtures/faulty_changes/{gate_id}",
        command=commands,
    )


def _py(code: str, *args: str) -> tuple[str, ...]:
    return ("python", "-c", code, *args)


def _appender(gate_id: str) -> tuple[str, ...]:
    return _py(f"open('order.txt', 'a').write('{gate_id}\\n')")


def _settings(repo: Path, tool_root: Path = REPO, **kwargs: object) -> RunSettings:
    return RunSettings(repo_root=repo, tool_root=tool_root, commit_ref=SHA, **kwargs)  # type: ignore[arg-type]


def _fake_tool_root(path: Path, files: dict[str, str]) -> Path:
    root = build_repo(path, files)
    (root / "schemas").mkdir(exist_ok=True)
    shutil.copy(REPO / "schemas" / "pipeline-run-record.schema.json", root / "schemas")
    return root


def _log(repo: Path, gate_id: str) -> str:
    return (repo / "evals" / "reports" / "gates" / f"{gate_id}.log").read_text(encoding="utf-8")


def _outcomes(outcome: RunOutcome) -> dict[str, Outcome]:
    return {r.gate_id: r.outcome for r in outcome.record.gate_results}


def test_gates_run_in_config_order_and_all_pass(tmp_path: Path) -> None:
    repo = build_repo(tmp_path, {})
    gates = [_gate("alpha", _appender("alpha")), _gate("beta", _appender("beta"))]
    outcome = run_gates(gates, _settings(repo))
    assert (repo / "order.txt").read_text().split() == ["alpha", "beta"]
    assert [r.gate_id for r in outcome.record.gate_results] == ["alpha", "beta"]
    assert outcome.record.state is RunState.PASSED
    assert outcome.exit_code == 0


def test_each_outcome_lands_on_the_record_with_a_log_report_ref(tmp_path: Path) -> None:
    repo = build_repo(tmp_path, {})
    gates = [
        _gate("alpha", _py("print('out-text')")),
        _gate("beta", _py("import sys; print('err-text', file=sys.stderr); sys.exit(4)")),
    ]
    outcome = run_gates(gates, _settings(repo))
    by_id = {r.gate_id: r for r in outcome.record.gate_results}
    assert by_id["alpha"].report_ref == "evals/reports/gates/alpha.log"
    assert by_id["beta"].report_ref == "evals/reports/gates/beta.log"
    assert "out-text" in _log(repo, "alpha")
    assert "err-text" in _log(repo, "beta")
    assert by_id["beta"].outcome is Outcome.FAIL


def test_one_failing_gate_does_not_stop_the_others_but_fails_the_run(tmp_path: Path) -> None:
    repo = build_repo(tmp_path, {})
    gates = [
        _gate("alpha", _appender("alpha")),
        _gate("beta", _py("import sys; sys.exit(1)")),
        _gate("gamma", _appender("gamma")),
    ]
    outcome = run_gates(gates, _settings(repo))
    assert (repo / "order.txt").read_text().split() == ["alpha", "gamma"]
    assert _outcomes(outcome) == {
        "alpha": Outcome.PASS,
        "beta": Outcome.FAIL,
        "gamma": Outcome.PASS,
    }
    assert outcome.record.state is RunState.FAILED
    assert outcome.exit_code == 1


def test_a_missing_gate_command_is_a_failure_not_a_skip(tmp_path: Path) -> None:
    repo = build_repo(tmp_path, {})
    outcome = run_gates([_gate("ghost", ("definitely-not-a-real-binary-xyz",))], _settings(repo))
    assert _outcomes(outcome) == {"ghost": Outcome.FAIL}
    assert "definitely-not-a-real-binary-xyz" in _log(repo, "ghost")
    assert outcome.exit_code == 1


def test_a_non_executable_gate_command_is_a_failure(tmp_path: Path) -> None:
    repo = build_repo(tmp_path, {"run.sh": "#!/bin/sh\nexit 0\n"})
    (repo / "run.sh").chmod(0o644)
    outcome = run_gates([_gate("noexec", ("./run.sh",))], _settings(repo))
    assert _outcomes(outcome) == {"noexec": Outcome.FAIL}


def test_every_command_of_a_gate_must_exit_zero(tmp_path: Path) -> None:
    repo = build_repo(tmp_path, {})
    gate = _gate("multi", _appender("first"), _py("import sys; sys.exit(1)"), _appender("third"))
    outcome = run_gates([gate], _settings(repo))
    assert _outcomes(outcome) == {"multi": Outcome.FAIL}
    assert (repo / "order.txt").read_text().split() == ["first", "third"]
    only_last_fails = _gate("tail", _appender("a"), _py("import sys; sys.exit(9)"))
    assert _outcomes(run_gates([only_last_fails], _settings(repo))) == {"tail": Outcome.FAIL}


def test_threshold_is_substituted_into_commands(tmp_path: Path) -> None:
    repo = build_repo(tmp_path, {})
    check = "import sys; sys.exit(0 if sys.argv[1] == '80' else 1)"
    outcome = run_gates([_gate("cov", _py(check, "{threshold}"), threshold=80)], _settings(repo))
    assert _outcomes(outcome) == {"cov": Outcome.PASS}


def test_a_leading_python_token_means_the_running_interpreter(tmp_path: Path) -> None:
    repo = build_repo(tmp_path, {})
    run_gates([_gate("which", _py("import sys; print(sys.executable)"))], _settings(repo))
    assert sys.executable in _log(repo, "which")


def test_commands_run_from_the_target_repo_root(tmp_path: Path) -> None:
    repo = build_repo(tmp_path / "target", {"keep.txt": ""})
    run_gates([_gate("cwd", _py("import os; print(os.getcwd())"))], _settings(repo))
    assert str(repo.resolve()) in _log(repo, "cwd")


def test_pythonpath_is_the_tool_root_src_and_tool_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PYTHONPATH", "/some/outer/path")
    repo = build_repo(tmp_path / "target", {"keep.txt": ""})
    tool_root = _fake_tool_root(tmp_path / "tools_home", {"src/placeholder.txt": "x"})
    run_gates(
        [_gate("path", _py("import os; print(os.environ['PYTHONPATH'])"))],
        _settings(repo, tool_root),
    )
    assert f"{tool_root}/src{os.pathsep}{tool_root}" in _log(repo, "path")
    assert "/some/outer/path" not in _log(repo, "path")


def test_modules_resolve_from_the_tool_root_not_the_target(tmp_path: Path) -> None:
    repo = build_repo(tmp_path / "target", {"keep.txt": ""})
    tool_root = _fake_tool_root(
        tmp_path / "tools_home", {"marker_mod.py": "VALUE = 'from-tool-root'\n"}
    )
    gate = _gate("imp", _py("import marker_mod; print(marker_mod.VALUE)"))
    outcome = run_gates([gate], _settings(repo, tool_root))
    assert _outcomes(outcome) == {"imp": Outcome.PASS}
    assert "from-tool-root" in _log(repo, "imp")


def test_outer_coverage_and_pytest_variables_do_not_leak(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("COV_CORE_SOURCE", "x")
    monkeypatch.setenv("COVERAGE_PROCESS_START", "y")
    monkeypatch.setenv("PYTEST_ADDOPTS", "--foo")
    monkeypatch.setenv("KEEP_ME", "1")
    repo = build_repo(tmp_path, {})
    code = (
        "import os; prefixes = ('COV_CORE', 'COVERAGE', 'PYTEST_');"
        "bad = [k for k in os.environ if k.startswith(prefixes)];"
        "print('LEAKED', bad); print('KEEP', os.environ.get('KEEP_ME'))"
    )
    run_gates([_gate("env", _py(code))], _settings(repo))
    log = _log(repo, "env")
    assert "LEAKED []" in log
    assert "KEEP 1" in log
    assert os.environ["COV_CORE_SOURCE"] == "x"  # the caller's environment is untouched


def test_a_gate_that_exceeds_the_timeout_fails(tmp_path: Path) -> None:
    repo = build_repo(tmp_path, {})
    outcome = run_gates(
        [_gate("slow", _py("import time; time.sleep(30)"))],
        _settings(repo, timeout_seconds=0.5),
    )
    assert _outcomes(outcome) == {"slow": Outcome.FAIL}
    assert "timed out" in _log(repo, "slow")


def test_the_record_is_persisted_and_schema_valid(tmp_path: Path) -> None:
    repo = build_repo(tmp_path, {})
    clock = FixedClock()
    outcome = run_gates([_gate("alpha", _py("pass"))], _settings(repo, clock=clock))
    assert outcome.record_path is not None
    assert outcome.record_path.parent == repo / "evals" / "reports" / "run-records"
    document = json.loads(outcome.record_path.read_text(encoding="utf-8"))
    validate_document(document, REPO)
    assert document["workflow"] == "pr"
    assert document["state"] == "passed"
    assert document["commit_ref"] == SHA
    assert document["correlation_id"]
    assert document["finished_at"].startswith("2026-01-01T12:00:00")


def test_commit_ref_defaults_to_a_content_hash_of_the_target(tmp_path: Path) -> None:
    repo = build_repo(tmp_path, {"a.txt": "x"})
    settings = RunSettings(repo_root=repo, tool_root=REPO)
    outcome = run_gates([_gate("alpha", _py("pass"))], settings)
    assert outcome.record.commit_ref.startswith("sha256:")


def test_the_workflow_is_recorded(tmp_path: Path) -> None:
    repo = build_repo(tmp_path, {})
    outcome = run_gates(
        [_gate("alpha", _py("pass"))], _settings(repo, workflow=Workflow.PROMOTE_STAGE)
    )
    assert outcome.record.workflow is Workflow.PROMOTE_STAGE


def test_the_run_record_for_a_failed_run_can_never_be_promoted(tmp_path: Path) -> None:
    repo = build_repo(tmp_path, {})
    outcome = run_gates([_gate("bad", _py("import sys; sys.exit(1)"))], _settings(repo))
    from tools.gates.run_record import InvalidTransitionError

    with pytest.raises(InvalidTransitionError):
        outcome.record.promote()


def test_on_result_is_called_once_per_gate_in_order(tmp_path: Path) -> None:
    repo = build_repo(tmp_path, {})
    seen: list[GateResult] = []
    gates = [_gate("alpha", _py("pass")), _gate("beta", _py("import sys; sys.exit(1)"))]
    run_gates(gates, _settings(repo), on_result=seen.append)
    assert [(r.gate_id, r.outcome) for r in seen] == [
        ("alpha", Outcome.PASS),
        ("beta", Outcome.FAIL),
    ]


def test_summary_has_one_status_line_per_gate_and_the_quarantine_count(tmp_path: Path) -> None:
    repo = build_repo(tmp_path, {})
    gates = [_gate("alpha", _py("pass")), _gate("beta", _py("import sys; sys.exit(1)"))]
    lines = format_summary(run_gates(gates, _settings(repo)))
    assert "PASS alpha" in lines[0]
    assert lines[1].startswith("FAIL beta")
    assert "evals/reports/gates/beta.log" in lines[1]
    assert any("quarantined gates: 0" in ln for ln in lines)
    assert any("failed" in ln for ln in lines[-2:])


def test_skipping_is_only_possible_as_skipped_with_reason() -> None:
    with pytest.raises(ValueError, match="reason"):
        GateResult(gate_id="x", outcome=Outcome.SKIPPED_WITH_REASON, reason="")
    ok = GateResult(gate_id="x", outcome=Outcome.SKIPPED_WITH_REASON, reason="because")
    assert ok.reason == "because"


def test_an_empty_gate_list_passes_with_no_results(tmp_path: Path) -> None:
    outcome = run_gates([], _settings(build_repo(tmp_path, {})))
    assert outcome.record.state is RunState.PASSED
    assert outcome.record.gate_results == ()
