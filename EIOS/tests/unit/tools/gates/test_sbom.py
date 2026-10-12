"""T031 (FR-011): every build run writes an SBOM listing every locked dependency."""

from __future__ import annotations

import json
import shutil
import tomllib
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from eios.common.errors import ToolError
from tools.gates import sbom

REPO_ROOT = Path(__file__).resolve().parents[4]
SCHEMA = REPO_ROOT / "schemas" / "pipeline-run-record.schema.json"

pytestmark = pytest.mark.skipif(shutil.which("uv") is None, reason="uv is not installed")


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A throwaway project carrying copies of the real manifest and lockfile."""
    for name in ("pyproject.toml", "uv.lock"):
        shutil.copy(REPO_ROOT / name, tmp_path / name)
    return tmp_path


def _locked_dependency_names(lock: Path) -> set[str]:
    data = tomllib.loads(lock.read_text(encoding="utf-8"))
    return {
        pkg["name"]
        for pkg in data["package"]
        if "virtual" not in pkg.get("source", {})  # the project itself is not a dependency
    }


def test_sbom_is_written_under_reports_sbom(project: Path) -> None:
    path = sbom.generate_sbom(project)
    assert path.is_file()
    assert path.parent == project / "evals" / "reports" / "sbom"


def test_sbom_is_cyclonedx_json(project: Path) -> None:
    document = json.loads(sbom.generate_sbom(project).read_text(encoding="utf-8"))
    assert document["bomFormat"] == "CycloneDX"
    assert document["specVersion"].startswith("1.")


def test_sbom_lists_every_locked_dependency(project: Path) -> None:
    document = json.loads(sbom.generate_sbom(project).read_text(encoding="utf-8"))
    listed = {component["name"] for component in document["components"]}
    locked = _locked_dependency_names(project / "uv.lock")
    assert len(locked) > 10  # guards against a vacuous comparison
    assert listed == locked


def test_sbom_components_carry_exact_locked_versions(project: Path) -> None:
    document = json.loads(sbom.generate_sbom(project).read_text(encoding="utf-8"))
    lock = tomllib.loads((project / "uv.lock").read_text(encoding="utf-8"))
    versions = {pkg["name"]: pkg.get("version") for pkg in lock["package"]}
    for component in document["components"]:
        assert component["version"] == versions[component["name"]]


def test_sbom_ref_is_a_relative_posix_path_to_the_file(project: Path) -> None:
    path = sbom.generate_sbom(project)
    ref = sbom.sbom_ref(project, path)
    assert ref.startswith("evals/reports/sbom/")
    assert "\\" not in ref
    assert (project / ref).is_file()


def test_sbom_file_name_is_stable_for_one_lockfile(project: Path) -> None:
    assert sbom.generate_sbom(project) == sbom.generate_sbom(project)


def test_sbom_file_name_changes_when_the_lockfile_changes(project: Path) -> None:
    first = sbom.generate_sbom(project)
    lock = project / "uv.lock"
    lock.write_text(lock.read_text(encoding="utf-8") + "\n# changed\n", encoding="utf-8")
    assert sbom.generate_sbom(project) != first


def test_missing_lockfile_is_a_tool_error(project: Path) -> None:
    (project / "uv.lock").unlink()
    with pytest.raises(ToolError, match=r"uv\.lock"):
        sbom.generate_sbom(project)


def test_missing_manifest_is_a_tool_error(project: Path) -> None:
    (project / "pyproject.toml").unlink()
    with pytest.raises(ToolError):
        sbom.generate_sbom(project)


def test_missing_uv_is_a_tool_error(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("tools.gates._exec.find_executable", lambda _name: None)
    with pytest.raises(ToolError, match="uv"):
        sbom.generate_sbom(project)


def test_generation_does_not_modify_the_lockfile(project: Path) -> None:
    before = (project / "uv.lock").read_bytes()
    sbom.generate_sbom(project)
    assert (project / "uv.lock").read_bytes() == before


def _release_candidate_record() -> dict[str, object]:
    return {
        "run_id": "run-1",
        "commit_ref": "sha256:abc",
        "workflow": "release-candidate",
        "state": "passed",
        "gate_results": [{"gate_id": "lint", "outcome": "pass"}],
        "correlation_id": "corr-1",
        "started_at": "2026-10-01T00:00:00Z",
    }


def test_release_candidate_record_without_sbom_ref_is_rejected() -> None:
    validator = Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")))
    errors = list(validator.iter_errors(_release_candidate_record()))
    assert any("sbom_ref" in error.message for error in errors)


def test_release_candidate_record_with_generated_sbom_ref_is_accepted(project: Path) -> None:
    ref = sbom.sbom_ref(project, sbom.generate_sbom(project))
    record = {**_release_candidate_record(), "sbom_ref": ref}
    validator = Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")))
    assert list(validator.iter_errors(record)) == []


def test_cli_writes_sbom_and_prints_its_reference(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert sbom.main(["--repo-root", str(project)]) == 0
    printed = capsys.readouterr().out.strip()
    assert printed.startswith("evals/reports/sbom/")
    assert (project / printed).is_file()


def test_cli_without_lockfile_exits_2(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (project / "uv.lock").unlink()
    assert sbom.main(["--repo-root", str(project)]) == 2
    assert "uv.lock" in capsys.readouterr().err
