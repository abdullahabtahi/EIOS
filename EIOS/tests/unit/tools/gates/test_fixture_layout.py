"""T032-T041: the skeleton and one overlay per gate exist and follow the overlay convention."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.gates.gate_config import GateSpec, load_gates
from tools.gates.registry import Tier, load_registry

REPO = Path(__file__).resolve().parents[4]
SKELETON = REPO / "tests" / "fixtures" / "clean_skeleton"
GATES = load_gates(REPO / "config" / "gates.yaml")
SUITE_TIER = {"contract": Tier.CONTRACT, "eval_smoke": Tier.EVAL_SMOKE, "red_line": Tier.RED_LINE}


def test_the_skeleton_has_every_part_the_gates_need() -> None:
    for relative in (
        "pyproject.toml",
        "uv.lock",
        "evals/registry.yaml",
        "infra/main.tf",
        "src/skeleton/calc.py",
        "tests/test_calc.py",
    ):
        assert (SKELETON / relative).is_file(), relative


def test_the_skeleton_registry_is_empty() -> None:
    assert load_registry(SKELETON / "evals" / "registry.yaml") == ()


@pytest.mark.parametrize("gate", GATES, ids=lambda g: g.id)
def test_every_gate_has_an_overlay_with_notes(gate: GateSpec) -> None:
    overlay = REPO / gate.proof_fixture
    assert overlay.is_dir(), f"missing overlay {overlay}"
    assert (overlay / "NOTES.md").is_file()
    payload = [p for p in overlay.rglob("*") if p.is_file() and p.name != "NOTES.md"]
    assert payload, "an overlay must change something"


@pytest.mark.parametrize(("gate_id", "tier"), sorted(SUITE_TIER.items()))
def test_suite_overlays_register_exactly_one_failing_suite_of_their_tier(
    gate_id: str, tier: Tier
) -> None:
    overlay = REPO / "tests" / "fixtures" / "faulty_changes" / gate_id
    (entry,) = load_registry(overlay / "evals" / "registry.yaml")
    assert entry.tier is tier
    script = overlay / entry.command[1]
    assert entry.command[0] == "python"
    assert script.is_file(), f"suite script missing: {script}"


def test_the_secret_overlay_is_built_at_test_time_only() -> None:
    overlay = REPO / "tests" / "fixtures" / "faulty_changes" / "secret_scan"
    stored = {p.name for p in overlay.rglob("*") if p.is_file() and p.suffix != ".pyc"}
    assert stored == {"NOTES.md", "build.py"}
