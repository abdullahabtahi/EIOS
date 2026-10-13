"""Shared fixtures for the agent gate tests."""

import json
from pathlib import Path

import pytest

RECORDED = Path(__file__).resolve().parents[2] / "evals" / "recorded"


@pytest.fixture(scope="session")
def recorded_dir() -> Path:
    return RECORDED


def load_recorded(subdir: str) -> list[dict[str, object]]:
    """Load every Turn Record JSON file under `evals/recorded/<subdir>`."""
    out: list[dict[str, object]] = []
    for path in sorted((RECORDED / subdir).glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        out.extend(data if isinstance(data, list) else [data])
    return out
