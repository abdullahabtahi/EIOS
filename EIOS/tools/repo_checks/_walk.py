"""Repository file walking shared by the checks; never leaves the repo root."""

from __future__ import annotations

import os
from collections.abc import Iterator, Sequence
from pathlib import Path

# Directory names skipped wherever they appear.
SKIP_DIR_NAMES = frozenset(
    {
        ".venv",
        ".git",
        "node_modules",
        "__pycache__",
        ".terraform",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
    }
)
# Repo-relative POSIX paths that are generated output and always skipped.
SKIP_PATHS = ("evals/reports",)


def relative_posix(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def is_under(relative: str, prefixes: Sequence[str]) -> bool:
    """True when ``relative`` equals a prefix or sits beneath it (prefixes are POSIX paths)."""
    return any(
        relative == prefix.strip("/") or relative.startswith(prefix.strip("/") + "/")
        for prefix in prefixes
    )


def _keep_dir(root: Path, directory: Path, excluded: Sequence[str]) -> bool:
    if directory.name in SKIP_DIR_NAMES or directory.is_symlink():
        return False
    return not is_under(relative_posix(root, directory), excluded)


def _keep_file(root: Path, file: Path, suffixes: frozenset[str] | None) -> bool:
    if file.is_symlink() or not file.is_file():
        return False
    if suffixes is not None and file.suffix not in suffixes:
        return False
    return file.resolve().is_relative_to(root)


def iter_files(
    repo_root: Path,
    *,
    start: str = "",
    suffixes: frozenset[str] | None = None,
    exclude: Sequence[str] = (),
) -> Iterator[Path]:
    """Yield regular files under ``repo_root/start`` in sorted order.

    Symlinks are never followed or yielded, vendored and generated trees are pruned, and
    every yielded path resolves inside ``repo_root``. ``suffixes=None`` yields every file.
    """
    root = repo_root.resolve()
    top = root / start if start else root
    if not top.is_dir() or not top.resolve().is_relative_to(root):
        return
    excluded = (*SKIP_PATHS, *exclude)
    for current, dirnames, filenames in os.walk(top, followlinks=False):
        here = Path(current)
        dirnames[:] = sorted(d for d in dirnames if _keep_dir(root, here / d, excluded))
        for name in sorted(filenames):
            file = here / name
            if _keep_file(root, file, suffixes) and not is_under(
                relative_posix(root, file), excluded
            ):
                yield file
