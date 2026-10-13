"""Overlay builder: plants a Terraform plan file at test time; nothing forbidden is stored in the repo."""

from __future__ import annotations

from pathlib import Path


def build(dest: Path) -> None:
    plan = dest / "infra" / "tfplan"
    plan.parent.mkdir(parents=True, exist_ok=True)
    plan.write_bytes(b"terraform plan snapshot placeholder\n")
