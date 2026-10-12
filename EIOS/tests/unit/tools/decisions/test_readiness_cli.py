"""``python -m tools.readiness <feature>``: exit codes 0/1/2 and the report it writes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.support.readiness_repo import ReadinessScenario, readiness_tree
from tests.support.repo_builder import build_repo
from tools.readiness.__main__ import main

_BLOCKED = ReadinessScenario(
    depends_on_spikes=("S-02",),
    depends_on_adrs=("ADR-003",),
    spike_states={"S-02": "open"},
    adr_statuses={"ADR-003": "Proposed"},
)
_READY = ReadinessScenario(
    depends_on_spikes=("S-02",),
    depends_on_adrs=("ADR-003",),
    spike_states={"S-02": "closed"},
    adr_statuses={"ADR-003": "Accepted"},
)


def _report(root: Path) -> dict[str, object]:
    data = json.loads((root / "evals" / "reports" / "readiness.json").read_text("utf-8"))
    assert isinstance(data, dict)
    return data


def test_ready_exits_zero_and_reports(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = build_repo(tmp_path, readiness_tree(_READY))
    assert main(["F03", "--repo-root", str(root)]) == 0
    assert "F03 is ready" in capsys.readouterr().out
    report = _report(root)
    assert report["exit_code"] == 0 and report["finding_count"] == 0
    assert report["feature"] == "F03" and report["ready"] is True


def test_blocked_exits_one_and_lists_every_unmet(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = build_repo(tmp_path, readiness_tree(_BLOCKED))
    assert main(["--repo-root", str(root), "F03"]) == 1
    out = capsys.readouterr().out
    assert "F03 is blocked" in out and "S-02" in out and "ADR-003" in out
    report = _report(root)
    assert report["exit_code"] == 1 and report["finding_count"] == 2 and report["ready"] is False


def test_flipping_the_fixture_flips_the_exit_code(tmp_path: Path) -> None:
    root = build_repo(tmp_path, readiness_tree(_BLOCKED))
    assert main(["F03", "--repo-root", str(root)]) == 1
    build_repo(tmp_path, readiness_tree(_READY))
    assert main(["F03", "--repo-root", str(root)]) == 0
    assert _report(root)["exit_code"] == 0


def test_schema_violation_exits_two(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    files = readiness_tree(_READY)
    files["specs/003-ontology-metrics/dependencies.yaml"] = "feature: F03\n"
    root = build_repo(tmp_path, files)
    assert main(["F03", "--repo-root", str(root)]) == 2
    assert "dependencies.yaml" in capsys.readouterr().err


def test_undeclared_feature_exits_two(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = build_repo(tmp_path, readiness_tree(_READY))
    assert main(["F11", "--repo-root", str(root)]) == 2
    assert "F11" in capsys.readouterr().err


@pytest.mark.parametrize("extra", [[], ["F03", "F04"], ["F3"], ["feature-three"]])
def test_bad_feature_argument_exits_two(tmp_path: Path, extra: list[str]) -> None:
    root = build_repo(tmp_path, readiness_tree(_READY))
    assert main([*extra, "--repo-root", str(root)]) == 2
