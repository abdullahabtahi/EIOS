"""Revision id for a run: the git HEAD when a repository exists, otherwise a content hash."""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
from collections.abc import Iterator
from pathlib import Path

_EXCLUDED_DIRS = frozenset(
    {
        ".git",
        ".venv",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".terraform",
        ".next",
        "node_modules",
    }
)
_EXCLUDED_RELATIVE = (("evals", "reports"),)
_EXCLUDED_FILES = frozenset({".DS_Store", ".coverage"})
_EXCLUDED_PREFIXES = (".coverage.",)
_SHA = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")
_GIT_TIMEOUT_SECONDS = 10.0  # [ASSUMPTION]
_HASH_PREFIX = "sha256:"
_CHUNK = 1 << 20


def _is_excluded_dir(relative: Path) -> bool:
    if relative.name in _EXCLUDED_DIRS:
        return True
    return any(relative.parts == parts for parts in _EXCLUDED_RELATIVE)


def _is_excluded_file(name: str) -> bool:
    return name in _EXCLUDED_FILES or name.startswith(_EXCLUDED_PREFIXES)


def _tracked_files(root: Path) -> Iterator[Path]:
    """Yield relative paths of regular files, sorted, skipping caches, envs and reports."""
    for current, dirs, files in os.walk(root, followlinks=False):
        here = Path(current).relative_to(root)
        dirs[:] = sorted(d for d in dirs if not _is_excluded_dir(here / d))
        for name in sorted(files):
            path = Path(current) / name
            if _is_excluded_file(name) or path.is_symlink():
                continue
            yield here / name


def content_hash(repo_root: Path) -> str:
    """sha256 over (relative path, file bytes) of the tracked tree; deterministic."""
    digest = hashlib.sha256()
    for relative in _tracked_files(repo_root):
        digest.update(relative.as_posix().encode("utf-8") + b"\0")
        with (repo_root / relative).open("rb") as handle:
            while chunk := handle.read(_CHUNK):
                digest.update(chunk)
        digest.update(b"\0")
    return _HASH_PREFIX + digest.hexdigest()


def _git_head(repo_root: Path) -> str | None:
    git_dir = repo_root / ".git"
    if not git_dir.exists():
        return None
    env = {**os.environ, "GIT_DIR": str(git_dir), "GIT_WORK_TREE": str(repo_root)}
    try:
        completed = subprocess.run(  # noqa: S603 - fixed argv, no user input
            ["git", "rev-parse", "HEAD"],  # noqa: S607 - resolved through PATH on purpose
            cwd=repo_root,
            env=env,
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except OSError, subprocess.SubprocessError:
        return None
    revision = completed.stdout.strip()
    if completed.returncode == 0 and _SHA.fullmatch(revision):
        return revision
    return None


def compute_commit_ref(repo_root: Path) -> str:
    """The git revision when ``repo_root`` has a usable repository, else the content hash."""
    return _git_head(repo_root) or content_hash(repo_root)
