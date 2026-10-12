"""Materialise the adr_check fixture tree and apply small mutations for each failure class."""

from __future__ import annotations

import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "decisions" / "adr_check" / "valid"
INDEX = "docs/spikes_and_adrs.md"
ADR_DIR = "docs/adr"


def materialise(dest: Path) -> Path:
    """Copy the valid fixture tree into ``dest`` and return it."""
    shutil.copytree(FIXTURE, dest, dirs_exist_ok=True)
    return dest


def write(root: Path, relative: str, text: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def replace(root: Path, relative: str, old: str, new: str) -> None:
    """Replace ``old`` with ``new`` in a fixture file; fails loudly when ``old`` is absent."""
    path = root / relative
    text = path.read_text(encoding="utf-8")
    assert old in text, f"{old!r} not found in {relative}"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def remove(root: Path, relative: str) -> None:
    (root / relative).unlink()
