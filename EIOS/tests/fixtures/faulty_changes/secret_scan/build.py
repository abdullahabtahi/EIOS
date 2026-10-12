"""Overlay builder: plants a secret-shaped string at test time; no literal is stored."""

from __future__ import annotations

from pathlib import Path

from tests.support.secret_shapes import cloud_access_key


def build(dest: Path) -> None:
    target = dest / "config" / "credentials.txt"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"access_key = {cloud_access_key()}\n", encoding="utf-8")
