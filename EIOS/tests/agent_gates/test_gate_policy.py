"""Policy tests (FR-017, SC-004): gates are deterministic, every red line has a behavioural check."""

from pathlib import Path

import yaml

from eios.agent_gates.cases import load_attack_cases, load_golden_cases

EVALS = Path(__file__).resolve().parents[2] / "evals"


def test_every_red_line_has_a_behavioural_check_that_exists() -> None:
    mapping = yaml.safe_load((EVALS / "agent" / "redline_map.yaml").read_text(encoding="utf-8"))
    assert sorted(mapping) == [f"RL-{i}" for i in range(1, 8)]
    known = {c.scenario_id for c in load_golden_cases(EVALS / "golden" / "agent_cases")}
    known |= {a.case_id for a in load_attack_cases(EVALS / "golden" / "attacks")}
    named = {
        c
        for entry in mapping.values()
        for c in entry["cases"]
        if c not in {"pinned corpus", "generated corpus", "replay invariant"}
    }
    assert named <= known, sorted(named - known)


def test_no_registered_agent_gate_uses_a_model_to_judge() -> None:
    registry = yaml.safe_load((EVALS / "registry.yaml").read_text(encoding="utf-8"))
    agent_rows = [r for r in registry if str(r["id"]).startswith("agent-")]
    assert agent_rows
    assert not [r for r in agent_rows if any(w in r["command"] for w in ("judge", "llm", "gemini"))]
