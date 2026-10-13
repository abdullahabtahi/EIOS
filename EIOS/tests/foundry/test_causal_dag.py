"""Tests for structural causal DAG equations and placebo refuter edges (SC-005, FR-046, FR-048)."""

from pathlib import Path

from eios.foundry.generators.causal_truth import CausalTruthGenerator
from eios.foundry.rng import DeterministicRNG
from eios.foundry.storage.eval_truth_store import EvalGroundTruthStore


def test_causal_dag_structural_equations_and_placebo_edge(tmp_path: Path):
    """Verifies 4-domain causal chain, edge coefficients, and at least 1 placebo edge with gamma=0.0."""
    rng = DeterministicRNG(master_seed=42)
    truth_store = EvalGroundTruthStore(base_dir=tmp_path / "eval-truth")
    causal_gen = CausalTruthGenerator(rng=rng, truth_store=truth_store)

    dag_truth = causal_gen.generate_causal_dag()

    # Verify 4 domains present
    domains = dag_truth["domains"]
    assert set(domains) == {"COMPETITIVE", "PARTNER", "CLIENT", "FINANCIAL"}

    # Verify structural chain
    edges = dag_truth["edges"]
    edge_map = {f"{e['source']}->{e['target']}": e for e in edges}

    assert "COMPETITIVE->PARTNER" in edge_map
    assert "PARTNER->CLIENT" in edge_map
    assert "CLIENT->FINANCIAL" in edge_map

    for _e_name, edge in edge_map.items():
        if not edge.get("is_placebo"):
            assert edge["true_structural_coefficient"] != 0.0

    # Placebo edge verification
    placebo_edges = [e for e in edges if e.get("is_placebo")]
    assert len(placebo_edges) >= 1, "Must contain at least 1 placebo edge"

    placebo = placebo_edges[0]
    assert placebo["true_structural_coefficient"] == 0.0
    assert placebo["placebo_refuter_expected_p_value"] > 0.05
    assert placebo["spurious_correlation"] != 0.0
