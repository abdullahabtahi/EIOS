"""Assemble a throwaway repository for the cost_check tests from tests/fixtures/cost_model/."""

from __future__ import annotations

import shutil
from pathlib import Path

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "cost_model"

CSV_TARGET = "docs/cost_model.csv"
LINKAGE_TARGET = "config/cost_linkage.yaml"
DEV_GATEWAY_TARGET = "config/llm_gateway.dev.yaml"


def _swap(dest: Path, source: Path, target: str) -> None:
    if not source.is_file():
        raise FileNotFoundError(f"missing cost_model fixture: {source}")
    shutil.copyfile(source, dest / target)


def materialise(
    dest: Path,
    *,
    csv: str | None = None,
    gateway: str | None = None,
    linkage: str | None = None,
) -> Path:
    """Copy the clean tree to ``dest``, then replace the cost model, dev gateway or linkage."""
    shutil.copytree(FIXTURES / "clean", dest, dirs_exist_ok=True)
    if csv is not None:
        _swap(dest, FIXTURES / "csv" / f"{csv}.csv", CSV_TARGET)
    if gateway is not None:
        _swap(dest, FIXTURES / "gateways" / f"{gateway}.yaml", DEV_GATEWAY_TARGET)
    if linkage is not None:
        _swap(dest, FIXTURES / "linkage" / f"{linkage}.yaml", LINKAGE_TARGET)
    return dest
