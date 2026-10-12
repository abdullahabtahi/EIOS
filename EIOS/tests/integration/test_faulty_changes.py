"""T030 (SC-001): every gate passes on the clean skeleton and fails on its own faulty change.

Fixture convention (tests/fixtures/):
  clean_skeleton/                 a minimal project that passes every gate
  faulty_changes/<gate>/          the gate's ``proof_fixture`` overlay; copied over the skeleton,
                                  except ``NOTES.md`` and ``build.py``
  faulty_changes/<gate>/build.py  optional; ``build(dest: Path) -> None`` runs after the copy
The gate list is read from config/gates.yaml, so new rows are covered with no code change.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from tools.gates.gate_config import GateSpec, load_gates
from tools.gates.run_record import InvalidTransitionError, Outcome, RunState
from tools.gates.runner import RunOutcome, RunSettings, run_gates

REPO = Path(__file__).resolve().parents[2]
SKELETON = REPO / "tests" / "fixtures" / "clean_skeleton"
NOT_COPIED = frozenset({"NOTES.md", "build.py"})
NETWORK_GATES = frozenset({"vuln_scan"})
NETWORK_ENABLED = os.environ.get("EIOS_TEST_NETWORK") == "1"

GATES = load_gates(REPO / "config" / "gates.yaml")


def _copy_tree(source: Path, dest: Path, skip: frozenset[str] = frozenset()) -> None:
    for item in source.iterdir():
        if item.name in skip or item.name == "__pycache__":
            continue
        target = dest / item.name
        if item.is_dir():
            target.mkdir(exist_ok=True)
            _copy_tree(item, target)
        else:
            shutil.copy2(item, target)


def _load_builder(path: Path) -> Callable[[Path], None]:
    spec = importlib.util.spec_from_file_location(f"_overlay_build_{path.parent.name}", path)
    assert spec is not None and spec.loader is not None, f"cannot import {path}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    build: Callable[[Path], None] = module.build
    return build


def _materialise(dest: Path, overlay: Path | None) -> Path:
    assert SKELETON.is_dir(), f"missing clean skeleton: {SKELETON.relative_to(REPO)}"
    dest.mkdir(parents=True, exist_ok=True)
    _copy_tree(SKELETON, dest)
    if overlay is not None:
        assert overlay.is_dir(), f"missing overlay: {overlay.relative_to(REPO)}"
        _copy_tree(overlay, dest, skip=NOT_COPIED)
        if (overlay / "build.py").is_file():
            _load_builder(overlay / "build.py")(dest)
    return dest


def _run(repo: Path, gates: list[GateSpec] | tuple[GateSpec, ...]) -> RunOutcome:
    return run_gates(gates, RunSettings(repo_root=repo, tool_root=REPO))


@pytest.fixture(scope="module")
def clean_outcome(tmp_path_factory: pytest.TempPathFactory) -> RunOutcome:
    repo = _materialise(tmp_path_factory.mktemp("clean") / "repo", None)
    # vuln_scan needs the advisory database (network); it joins the clean run only when
    # network tests are enabled, and is always proven by its own requires_network case.
    gates = [g for g in GATES if NETWORK_ENABLED or g.id not in NETWORK_GATES]
    return _run(repo, gates)


def test_the_clean_skeleton_passes_every_gate(clean_outcome: RunOutcome) -> None:
    outcomes = {r.gate_id: r.outcome for r in clean_outcome.record.gate_results}
    failing = {gate_id: o for gate_id, o in outcomes.items() if o is not Outcome.PASS}
    assert not failing, f"clean skeleton fails gates: {failing}"
    assert clean_outcome.record.state is RunState.PASSED
    assert clean_outcome.exit_code == 0


def _params() -> list[object]:
    params: list[object] = []
    for gate in GATES:
        marks = [pytest.mark.requires_network] if gate.id in NETWORK_GATES else []
        params.append(pytest.param(gate, id=gate.id, marks=marks))
    return params


@pytest.mark.parametrize("gate", _params())
def test_the_proof_fixture_makes_exactly_its_gate_fail(gate: GateSpec, tmp_path: Path) -> None:
    repo = _materialise(tmp_path / "repo", REPO / gate.proof_fixture)
    outcome = _run(repo, [gate])
    (result,) = outcome.record.gate_results
    assert result.gate_id == gate.id
    assert result.outcome is Outcome.FAIL, f"{gate.id} did not fail on its faulty change"
    assert result.report_ref, "the failing gate must point at a report"
    assert (repo / result.report_ref).is_file()
    assert outcome.record.state is RunState.FAILED
    assert outcome.exit_code == 1
    with pytest.raises(InvalidTransitionError):
        outcome.record.promote()
