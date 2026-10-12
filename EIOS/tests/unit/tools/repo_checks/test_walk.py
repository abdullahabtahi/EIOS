"""The repository walk skips generated tool caches, so a cache can never fail a check."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.support.repo_builder import build_repo
from tools.repo_checks._walk import iter_files


@pytest.mark.parametrize(
    "cache", [".pytest_cache", ".mypy_cache", ".ruff_cache", ".venv", "__pycache__"]
)
def test_tool_cache_directories_are_not_walked(tmp_path: Path, cache: str) -> None:
    root = build_repo(tmp_path, {f"{cache}/v/nodeids": "x\n", "src/kept.py": "x = 1\n"})
    walked = [p.relative_to(root).as_posix() for p in iter_files(root)]
    assert walked == ["src/kept.py"]
