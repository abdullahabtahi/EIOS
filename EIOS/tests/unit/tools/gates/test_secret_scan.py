"""Secret scanner: shapes from tests/support/secret_shapes.py, tree, logs and history."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.support.repo_builder import build_repo
from tests.support.secret_shapes import all_shapes
from tools.common.findings import Finding
from tools.gates import secret_scan

SHAPES = all_shapes()
EXPECTED_RULE = {
    "cloud_access_key": "secret-cloud-access-key",
    "api_key": "secret-api-key",
    "vcs_token": "secret-vcs-token",
    "private_key_block": "secret-private-key",
}
FIXTURES = Path(__file__).resolve().parents[3] / "fixtures"
GIT = shutil.which("git")


def _rules(findings: list[Finding]) -> set[str]:
    return {f.rule_id for f in findings}


@pytest.mark.parametrize("shape", sorted(SHAPES))
def test_each_secret_shape_is_detected_with_its_rule(shape: str) -> None:
    findings = secret_scan.scan_text("config.txt", f"value = {SHAPES[shape]}\n")
    assert _rules(findings) == {EXPECTED_RULE[shape]}
    assert findings[0].file == "config.txt"
    assert findings[0].line == 1


@pytest.mark.parametrize("shape", sorted(SHAPES))
def test_findings_never_contain_the_secret_value(shape: str) -> None:
    findings = secret_scan.scan_text("a.txt", SHAPES[shape])
    for finding in findings:
        assert SHAPES[shape] not in json.dumps(finding.to_dict())
        assert "A1b2C3d4" not in finding.message


def test_line_numbers_are_one_based_and_exact() -> None:
    text = "ok\nstill ok\n" + SHAPES["vcs_token"] + "\n"
    assert [f.line for f in secret_scan.scan_text("x", text)] == [3]


def test_two_secrets_on_one_line_give_two_findings() -> None:
    text = f"{SHAPES['cloud_access_key']} {SHAPES['vcs_token']}"
    assert _rules(secret_scan.scan_text("x", text)) == {
        "secret-cloud-access-key",
        "secret-vcs-token",
    }


@pytest.mark.parametrize(
    "text", ["", "\n\n", "hello world", "AKIA short", "ghp_tooshort", "🔐 ünïcode ✓"]
)
def test_innocent_text_has_no_findings(text: str) -> None:
    assert secret_scan.scan_text("x", text) == []


def test_clean_tree_has_no_findings(tmp_path: Path) -> None:
    build_repo(tmp_path, {"a.py": "x = 1\n", "docs/n.md": "text\n"})
    assert secret_scan.scan_tree(tmp_path) == []


def test_tree_scan_reports_relative_posix_path(tmp_path: Path) -> None:
    build_repo(tmp_path, {"src/pkg/conf.txt": SHAPES["api_key"] + "\n"})
    [finding] = secret_scan.scan_tree(tmp_path)
    assert finding.file == "src/pkg/conf.txt"


@pytest.mark.parametrize(
    "ignored", [".venv/lib/x.txt", ".git/x.txt", "a/__pycache__/x.txt", "infra/.terraform/x.txt"]
)
def test_dependency_and_cache_directories_are_skipped(tmp_path: Path, ignored: str) -> None:
    build_repo(tmp_path, {ignored: SHAPES["cloud_access_key"]})
    assert secret_scan.scan_tree(tmp_path) == []


def test_captured_logs_under_evals_reports_are_scanned(tmp_path: Path) -> None:
    build_repo(tmp_path, {"evals/reports/run.log": f"token: {SHAPES['vcs_token']}\n"})
    [finding] = secret_scan.scan_tree(tmp_path)
    assert finding.file == "evals/reports/run.log"


def test_binary_files_are_skipped(tmp_path: Path) -> None:
    (tmp_path / "blob.bin").write_bytes(b"\x00\x01" + SHAPES["cloud_access_key"].encode())
    assert secret_scan.scan_tree(tmp_path) == []


def test_undecodable_bytes_do_not_crash_the_scan(tmp_path: Path) -> None:
    (tmp_path / "latin.txt").write_bytes(b"caf\xe9 " + SHAPES["vcs_token"].encode())
    assert _rules(secret_scan.scan_tree(tmp_path)) == {"secret-vcs-token"}


def test_symlinks_are_not_followed(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    build_repo(outside, {"s.txt": SHAPES["cloud_access_key"]})
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "link.txt").symlink_to(outside / "s.txt")
    (repo / "linkdir").symlink_to(outside, target_is_directory=True)
    assert secret_scan.scan_tree(repo) == []


def test_fixtures_tree_of_this_repository_is_clean() -> None:
    assert secret_scan.scan_tree(FIXTURES) == []


def test_main_exit_0_on_clean_tree(tmp_path: Path) -> None:
    build_repo(tmp_path, {"a.txt": "fine\n"})
    assert secret_scan.main(["--repo-root", str(tmp_path)]) == 0


def test_main_exit_1_reports_location_but_not_value(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    build_repo(tmp_path, {"cfg/a.txt": "k=" + SHAPES["cloud_access_key"] + "\n"})
    assert secret_scan.main(["--repo-root", str(tmp_path)]) == 1
    captured = capsys.readouterr()
    assert SHAPES["cloud_access_key"] not in captured.out + captured.err
    report = (tmp_path / "evals" / "reports" / "secret_scan.json").read_text(encoding="utf-8")
    assert SHAPES["cloud_access_key"] not in report
    assert json.loads(report)["findings"][0]["file"] == "cfg/a.txt"


def test_main_exit_2_for_missing_repo_root(tmp_path: Path) -> None:
    assert secret_scan.main(["--repo-root", str(tmp_path / "nope")]) == 2


def _git(repo: Path, *args: str) -> None:
    assert GIT is not None
    command = [GIT, "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
    command += ["-c", "commit.gpgsign=false", *args]
    subprocess.run(command, cwd=repo, check=True, capture_output=True)  # noqa: S603


@pytest.mark.skipif(GIT is None, reason="git is not installed")
def test_history_scan_finds_a_secret_deleted_from_the_working_tree(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q")
    build_repo(tmp_path, {"leak.txt": SHAPES["vcs_token"] + "\n"})
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "add")
    (tmp_path / "leak.txt").unlink()
    _git(tmp_path, "commit", "-q", "-am", "remove")
    assert secret_scan.scan_tree(tmp_path) == []
    findings = secret_scan.scan_history(tmp_path)
    assert _rules(findings) == {"secret-vcs-token"}
    assert findings[0].file == "leak.txt"
    assert "history" in findings[0].message
    assert SHAPES["vcs_token"] not in findings[0].message


def test_history_scan_without_a_git_directory_finds_nothing(tmp_path: Path) -> None:
    assert secret_scan.scan_history(tmp_path) == []


@pytest.mark.skipif(GIT is None, reason="git is not installed")
def test_main_includes_history_findings(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q")
    build_repo(tmp_path, {"leak.txt": SHAPES["api_key"] + "\n"})
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "add")
    (tmp_path / "leak.txt").write_text("clean\n", encoding="utf-8")
    assert secret_scan.main(["--repo-root", str(tmp_path)]) == 1
