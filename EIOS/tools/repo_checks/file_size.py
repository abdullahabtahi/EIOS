"""Flag source files longer than the line ceiling."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from eios.common.errors import ToolError
from tools.common.findings import Finding
from tools.repo_checks._walk import iter_files, relative_posix

RULE_ID = "repo.file_size"
DEFAULT_CEILING = 800  # [TARGET]
SOURCE_SUFFIXES = frozenset({".py", ".yaml", ".yml", ".toml", ".tf", ".sh", ".ts", ".tsx", ".js"})


def _line_count(path: Path) -> int:
    try:
        return len(path.read_text(encoding="utf-8").splitlines())
    except (OSError, UnicodeDecodeError) as exc:
        raise ToolError(f"cannot read {path}: {exc}") from exc


def check_file_size(
    repo_root: Path, *, ceiling: int = DEFAULT_CEILING, exclude: Sequence[str] = ()
) -> tuple[Finding, ...]:
    """Return one finding per source file with more than ``ceiling`` lines."""
    if ceiling < 1:
        raise ToolError(f"file size ceiling must be a positive integer, got {ceiling}")
    root = repo_root.resolve()
    findings: list[Finding] = []
    for path in iter_files(root, suffixes=SOURCE_SUFFIXES, exclude=exclude):
        count = _line_count(path)
        if count > ceiling:
            message = f"file has {count} lines, over the {ceiling}-line ceiling; split it"
            findings.append(Finding(relative_posix(root, path), ceiling + 1, RULE_ID, message))
    return tuple(sorted(findings, key=lambda f: (f.file, f.line)))
