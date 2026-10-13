"""run_gate, local and evals.cli: exit codes, status lines and the records they write."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from evals import cli as evals_cli
from tests.support.repo_builder import build_repo
from tools.gates import local, run_gate

REPO = Path(__file__).resolve().parents[4]
SHA = "sha256:" + "e" * 64


def _tool_root(tmp_path: Path, gates: list[dict[str, object]], quarantine: str = "[]\n") -> Path:
    root = build_repo(
        tmp_path / "tool_root",
        {
            "config/gates.yaml": yaml.safe_dump({"gates": gates}),
            "config/quarantine.yaml": quarantine,
        },
    )
    (root / "schemas").mkdir()
    shutil.copy(REPO / "schemas" / "pipeline-run-record.schema.json", root / "schemas")
    return root


def _row(gate_id: str, code: str, stage: str = "pr") -> dict[str, object]:
    return {
        "id": gate_id,
        "blocking": True,
        "stage": stage,
        "proof_fixture": f"tests/fixtures/faulty_changes/{gate_id}",
        "command": ["python -c " + repr(code)],
    }


def _records(repo: Path) -> list[Path]:
    return sorted((repo / "evals" / "reports" / "run-records").glob("*.json"))


# --- run_gate -----------------------------------------------------------------------------


def test_run_gate_runs_one_gate_and_prints_its_status(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _tool_root(tmp_path, [_row("alpha", "pass"), _row("beta", "raise SystemExit(1)")])
    repo = build_repo(tmp_path / "target", {"keep.txt": ""})
    argv = ["alpha", "--repo-root", str(repo), "--tool-root", str(root)]
    assert run_gate.main(argv) == 0
    assert "PASS alpha" in capsys.readouterr().out
    (record_path,) = _records(repo)
    results = json.loads(record_path.read_text())["gate_results"]
    assert [r["gate_id"] for r in results] == ["alpha"]


def test_run_gate_exits_one_when_the_gate_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _tool_root(tmp_path, [_row("beta", "raise SystemExit(1)")])
    repo = build_repo(tmp_path / "target", {"keep.txt": ""})
    assert run_gate.main(["beta", "--repo-root", str(repo), "--tool-root", str(root)]) == 1
    assert "FAIL beta" in capsys.readouterr().out


def test_run_gate_with_an_unknown_gate_id_is_a_tool_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _tool_root(tmp_path, [_row("alpha", "pass")])
    repo = build_repo(tmp_path / "target", {"keep.txt": ""})
    assert run_gate.main(["nope", "--repo-root", str(repo), "--tool-root", str(root)]) == 2
    assert "nope" in capsys.readouterr().err


def test_run_gate_honours_quarantine(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    quarantine = yaml.safe_dump(
        [{"gate_id": "beta", "owner": "o", "expires": "2999-01-01", "reason": "flaky"}]
    )
    root = _tool_root(tmp_path, [_row("beta", "raise SystemExit(1)")], quarantine)
    repo = build_repo(tmp_path / "target", {"keep.txt": ""})
    assert run_gate.main(["beta", "--repo-root", str(repo), "--tool-root", str(root)]) == 0
    out = capsys.readouterr().out
    assert "SKIP beta" in out
    assert "quarantined gates: 1" in out


# --- local --------------------------------------------------------------------------------


def test_local_runs_pr_gates_in_order_with_one_status_line_each(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    gates = [
        _row("alpha", "pass"),
        _row("promo", "raise SystemExit(1)", "promote"),
        _row("beta", "pass"),
    ]
    root = _tool_root(tmp_path, gates)
    repo = build_repo(tmp_path / "target", {"keep.txt": ""})
    assert local.main(["--repo-root", str(repo), "--tool-root", str(root)]) == 0
    out = capsys.readouterr().out
    assert out.index("PASS alpha") < out.index("PASS beta")
    assert "promo" not in out
    assert "quarantined gates: 0" in out
    (record_path,) = _records(repo)
    document = json.loads(record_path.read_text())
    assert document["workflow"] == "pr"
    assert [r["gate_id"] for r in document["gate_results"]] == ["alpha", "beta"]


def test_local_exits_one_after_running_every_gate_when_any_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _tool_root(tmp_path, [_row("alpha", "raise SystemExit(1)"), _row("beta", "pass")])
    repo = build_repo(tmp_path / "target", {"keep.txt": ""})
    assert local.main(["--repo-root", str(repo), "--tool-root", str(root)]) == 1
    out = capsys.readouterr().out
    assert "FAIL alpha" in out
    assert "PASS beta" in out


def test_local_gate_ids_reads_the_given_tool_root(tmp_path: Path) -> None:
    root = _tool_root(tmp_path, [_row("alpha", "pass"), _row("promo", "pass", "promote")])
    assert local.local_gate_ids(root) == ("alpha",)


# --- evals.cli ----------------------------------------------------------------------------


def _suite_yaml(
    suite_id: str, tier: str, code: str, report: str | None = None
) -> dict[str, object]:
    return {
        "id": suite_id,
        "tier": tier,
        "command": ["python", "-c", code],
        "owner_feature": "F01",
        "report": report or f"evals/reports/{suite_id}.json",
    }


_WRITES = "import pathlib; pathlib.Path('evals/reports/{name}.json').write_text('{{}}')"


def test_evals_cli_with_an_empty_registry_prints_the_message_and_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = build_repo(tmp_path, {"evals/registry.yaml": "# empty\n[]\n"})
    assert evals_cli.main(["run", "--tier", "contract", "--repo-root", str(repo)]) == 0
    assert "no suites registered" in capsys.readouterr().out


def test_evals_cli_runs_one_tier_and_defaults_to_the_pr_workflow(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    suites = [
        _suite_yaml("good-one", "contract", _WRITES.format(name="good-one")),
        _suite_yaml("other-one", "red_line", "raise SystemExit(1)"),
    ]
    repo = build_repo(tmp_path, {"evals/registry.yaml": yaml.safe_dump(suites)})
    assert evals_cli.main(["run", "--tier", "contract", "--repo-root", str(repo)]) == 0
    assert "PASS good-one" in capsys.readouterr().out
    (record_path,) = _records(repo)
    document = json.loads(record_path.read_text())
    assert document["workflow"] == "pr"
    assert [r["gate_id"] for r in document["gate_results"]] == ["good-one"]


def test_evals_cli_id_prefix_runs_only_matching_suites(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    suites = [
        _suite_yaml("resilience-restart", "validation", _WRITES.format(name="resilience-restart")),
        _suite_yaml("quality-drift", "validation", "raise SystemExit(1)"),
    ]
    repo = build_repo(tmp_path, {"evals/registry.yaml": yaml.safe_dump(suites)})
    argv = ["run", "--tier", "validation", "--workflow", "promote-stage"]
    argv += ["--id-prefix", "resilience-", "--repo-root", str(repo)]
    assert evals_cli.main(argv) == 0
    out = capsys.readouterr().out
    assert "PASS resilience-restart" in out
    assert "quality-drift" not in out


def test_evals_cli_id_prefix_with_no_match_passes_with_the_no_suites_message(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    suites = [_suite_yaml("quality-drift", "validation", "raise SystemExit(1)")]
    repo = build_repo(tmp_path, {"evals/registry.yaml": yaml.safe_dump(suites)})
    argv = ["run", "--tier", "validation", "--workflow", "promote-stage"]
    argv += ["--id-prefix", "resilience-", "--repo-root", str(repo)]
    assert evals_cli.main(argv) == 0
    assert "no suites registered" in capsys.readouterr().out


def test_evals_cli_exits_one_for_a_failing_suite(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    suites = [_suite_yaml("bad-one", "contract", "raise SystemExit(2)")]
    repo = build_repo(tmp_path, {"evals/registry.yaml": yaml.safe_dump(suites)})
    assert evals_cli.main(["run", "--tier", "contract", "--repo-root", str(repo)]) == 1
    assert "FAIL bad-one" in capsys.readouterr().out


def test_evals_cli_exits_one_for_a_missing_report(tmp_path: Path) -> None:
    suites = [_suite_yaml("silent-one", "contract", "pass")]
    repo = build_repo(tmp_path, {"evals/registry.yaml": yaml.safe_dump(suites)})
    assert evals_cli.main(["run", "--tier", "contract", "--repo-root", str(repo)]) == 1


def test_evals_cli_exits_two_for_a_missing_or_malformed_registry(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    empty = build_repo(tmp_path / "none", {})
    assert evals_cli.main(["run", "--tier", "contract", "--repo-root", str(empty)]) == 2
    bad = build_repo(tmp_path / "bad", {"evals/registry.yaml": "- {id: Bad}\n"})
    assert evals_cli.main(["run", "--tier", "contract", "--repo-root", str(bad)]) == 2
    assert "registry.yaml" in capsys.readouterr().err


def test_evals_cli_refuses_a_sealed_tier_under_the_pr_workflow(tmp_path: Path) -> None:
    suites = [_suite_yaml("sealed-one", "sealed", "raise SystemExit(0)")]
    repo = build_repo(tmp_path, {"evals/registry.yaml": yaml.safe_dump(suites)})
    assert evals_cli.main(["run", "--tier", "sealed", "--repo-root", str(repo)]) == 2


def test_evals_cli_rejects_an_unknown_tier(tmp_path: Path) -> None:
    repo = build_repo(tmp_path, {"evals/registry.yaml": "[]\n"})
    assert evals_cli.main(["run", "--tier", "bogus", "--repo-root", str(repo)]) == 2


def test_evals_cli_accepts_a_workflow_option(tmp_path: Path) -> None:
    suites = [_suite_yaml("valid-one", "validation", _WRITES.format(name="valid-one"))]
    repo = build_repo(tmp_path, {"evals/registry.yaml": yaml.safe_dump(suites)})
    argv = ["run", "--tier", "validation", "--workflow", "promote-stage", "--repo-root", str(repo)]
    assert evals_cli.main(argv) == 0
    assert json.loads(_records(repo)[0].read_text())["workflow"] == "promote-stage"


def test_evals_cli_records_the_sbom_ref_for_a_release_candidate(tmp_path: Path) -> None:
    repo = build_repo(tmp_path, {"evals/registry.yaml": "[]\n"})
    ref = "evals/reports/sbom/sbom-1.cdx.json"
    argv = ["run", "--tier", "sealed", "--workflow", "release-candidate", "--sbom-ref", ref]
    assert evals_cli.main([*argv, "--repo-root", str(repo)]) == 0
    assert json.loads(_records(repo)[0].read_text())["sbom_ref"] == ref


def test_evals_cli_release_candidate_without_an_sbom_ref_is_a_tool_error(tmp_path: Path) -> None:
    repo = build_repo(tmp_path, {"evals/registry.yaml": "[]\n"})
    argv = ["run", "--tier", "sealed", "--workflow", "release-candidate"]
    assert evals_cli.main([*argv, "--repo-root", str(repo)]) == 2


def test_evals_cli_generate_sbom_records_the_generated_reference(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = build_repo(tmp_path, {"evals/registry.yaml": "[]\n"})
    sbom = repo / "evals" / "reports" / "sbom" / "sbom-1.cdx.json"
    monkeypatch.setattr(evals_cli, "generate_sbom", lambda root: sbom)
    argv = ["run", "--tier", "sealed", "--workflow", "release-candidate", "--generate-sbom"]
    assert evals_cli.main([*argv, "--repo-root", str(repo)]) == 0
    assert json.loads(_records(repo)[0].read_text())["sbom_ref"] == (
        "evals/reports/sbom/sbom-1.cdx.json"
    )


def test_evals_cli_generate_sbom_without_a_lockfile_is_a_tool_error(tmp_path: Path) -> None:
    repo = build_repo(tmp_path, {"evals/registry.yaml": "[]\n"})
    argv = ["run", "--tier", "sealed", "--workflow", "release-candidate", "--generate-sbom"]
    assert evals_cli.main([*argv, "--repo-root", str(repo)]) == 2


def test_evals_cli_refuses_both_an_sbom_ref_and_generate_sbom(tmp_path: Path) -> None:
    repo = build_repo(tmp_path, {"evals/registry.yaml": "[]\n"})
    argv = ["run", "--tier", "sealed", "--sbom-ref", "x", "--generate-sbom"]
    assert evals_cli.main([*argv, "--repo-root", str(repo)]) == 2


# --- invocation as in `make check` and CI (no PYTHONPATH, `uv run python -m ...`) ----------


@pytest.mark.parametrize("module", ["tools.gates.local", "tools.gates.run_gate", "evals.cli"])
def test_entry_points_import_without_pythonpath(module: str) -> None:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("PYTHONPATH", "COV_CORE"))}
    completed = subprocess.run(  # noqa: S603
        [sys.executable, "-m", module, "--help"],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "usage" in completed.stdout.lower()


# --- direct invocation (`uv run python -m tools.<name>`) ----------------------------------


@pytest.mark.parametrize("module", ["tools.repo_checks", "tools.gates.vuln_scan"])
def test_tools_run_directly_without_the_project_installed(module: str) -> None:
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    code = f"import runpy; runpy.run_module({module!r}, run_name='not_main')"
    done = subprocess.run(  # noqa: S603
        [sys.executable, "-c", code], cwd=REPO, env=env, capture_output=True, text=True, check=False
    )
    assert done.returncode == 0, done.stderr
