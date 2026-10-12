"""Build a throwaway repository tree under a temporary directory from a mapping."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path


def build_repo(root: Path, files: Mapping[str, str]) -> Path:
    """Write ``files`` (relative path -> text) beneath ``root`` and return ``root``.

    Rejects absolute paths and parent traversal so a fixture can never escape ``root``.
    """
    resolved_root = root.resolve()
    for relative, content in files.items():
        target = (resolved_root / relative).resolve()
        if not target.is_relative_to(resolved_root):
            raise ValueError(f"fixture path escapes the repo root: {relative!r}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return resolved_root
