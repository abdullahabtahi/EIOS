"""T028: a source file over the 800-line ceiling [TARGET] is flagged with its path."""

from __future__ import annotations

from pathlib import Path

import pytest

from eios.common.errors import ToolError
from tests.support.repo_builder import build_repo
from tools.repo_checks.file_size import DEFAULT_CEILING, RULE_ID, check_file_size


def _lines(count: int, *, trailing_newline: bool = True) -> str:
    body = "\n".join("x = 1" for _ in range(count))
    return body + ("\n" if trailing_newline else "")


def test_default_ceiling_is_800() -> None:
    assert DEFAULT_CEILING == 800


def test_file_over_ceiling_is_flagged_with_its_path(tmp_path: Path) -> None:
    root = build_repo(tmp_path, {"src/eios/big.py": _lines(801)})
    findings = check_file_size(root)
    assert len(findings) == 1
    assert findings[0].file == "src/eios/big.py"
    assert findings[0].rule_id == RULE_ID
    assert "801" in findings[0].message
    assert "800" in findings[0].message


def test_file_at_the_ceiling_is_not_flagged(tmp_path: Path) -> None:
    root = build_repo(tmp_path, {"a.py": _lines(800)})
    assert check_file_size(root) == ()


def test_last_line_without_trailing_newline_is_counted(tmp_path: Path) -> None:
    root = build_repo(tmp_path, {"a.py": _lines(801, trailing_newline=False)})
    assert [f.file for f in check_file_size(root)] == ["a.py"]


def test_ceiling_can_be_overridden(tmp_path: Path) -> None:
    root = build_repo(tmp_path, {"a.py": _lines(11), "b.py": _lines(10)})
    assert [f.file for f in check_file_size(root, ceiling=10)] == ["a.py"]


@pytest.mark.parametrize("ceiling", [0, -5])
def test_non_positive_ceiling_is_a_tool_error(tmp_path: Path, ceiling: int) -> None:
    with pytest.raises(ToolError):
        check_file_size(tmp_path, ceiling=ceiling)


def test_yaml_and_other_source_suffixes_are_checked(tmp_path: Path) -> None:
    root = build_repo(
        tmp_path,
        {
            "config/big.yaml": _lines(20),
            "infra/main.tf": _lines(20),
            "scripts/run.sh": _lines(20),
            "pyproject.toml": _lines(20),
        },
    )
    flagged = {f.file for f in check_file_size(root, ceiling=10)}
    assert flagged == {"config/big.yaml", "infra/main.tf", "scripts/run.sh", "pyproject.toml"}


def test_non_source_files_are_not_checked(tmp_path: Path) -> None:
    root = build_repo(
        tmp_path,
        {"docs/long.md": _lines(50), "uv.lock": _lines(50), "data.bin": _lines(50)},
    )
    assert check_file_size(root, ceiling=10) == ()


@pytest.mark.parametrize(
    "skipped",
    [
        ".venv/lib/x.py",
        ".git/hooks/x.py",
        "node_modules/pkg/x.py",
        "pkg/__pycache__/x.py",
        "evals/reports/x.yaml",
        ".terraform/x.py",
        ".mypy_cache/x.py",
        ".ruff_cache/x.py",
    ],
)
def test_vendored_and_generated_trees_are_skipped(tmp_path: Path, skipped: str) -> None:
    root = build_repo(tmp_path, {skipped: _lines(50)})
    assert check_file_size(root, ceiling=10) == ()


def test_exclude_paths_are_skipped(tmp_path: Path) -> None:
    root = build_repo(tmp_path, {"FEIOS/a.py": _lines(50), "src/b.py": _lines(50)})
    findings = check_file_size(root, ceiling=10, exclude=("FEIOS",))
    assert [f.file for f in findings] == ["src/b.py"]


def test_findings_are_sorted_by_path(tmp_path: Path) -> None:
    root = build_repo(tmp_path, {"z.py": _lines(20), "a/b.py": _lines(20), "a.py": _lines(20)})
    assert [f.file for f in check_file_size(root, ceiling=10)] == ["a.py", "a/b.py", "z.py"]


def test_symlink_pointing_outside_the_repo_is_never_read(tmp_path: Path) -> None:
    outside = build_repo(tmp_path / "outside", {"huge.py": _lines(50)})
    root = build_repo(tmp_path / "repo", {"ok.py": "x = 1\n"})
    (root / "link.py").symlink_to(outside / "huge.py")
    assert check_file_size(root, ceiling=10) == ()


def test_empty_repo_has_nothing_to_flag(tmp_path: Path) -> None:
    assert check_file_size(tmp_path) == ()
