"""Unit and property tests for Causal DAG engine (T007, US1)."""

import pytest

from eios.synthesis.exceptions import CausalCycleError
from eios.synthesis.models import CausalEdge
from eios.synthesis.scm import CausalDAG


def test_causal_dag_creation_and_topological_sort():
    """Verify DAG creation and valid topological ordering."""
    edges = [
        CausalEdge(
            source_metric="competitor_payout_rate",
            target_metric="partner_churn_rate",
            weight=0.45,
            ci_lower=0.38,
            ci_upper=0.52,
            confidence=0.92,
            rationale="Competitor higher payout increases partner churn",
        ),
        CausalEdge(
            source_metric="partner_churn_rate",
            target_metric="ftd_count_28d",
            weight=-340.0,
            ci_lower=-410.0,
            ci_upper=-270.0,
            confidence=0.89,
            rationale="Partner churn reduces client referral volume",
        ),
        CausalEdge(
            source_metric="ftd_count_28d",
            target_metric="net_deposit_volume_usd",
            weight=45.0,
            ci_lower=38.5,
            ci_upper=51.5,
            confidence=0.95,
            rationale="FTD growth drives net deposit inflows",
        ),
    ]

    dag = CausalDAG(edges=edges)
    order = dag.topological_order()

    assert order == [
        "competitor_payout_rate",
        "partner_churn_rate",
        "ftd_count_28d",
        "net_deposit_volume_usd",
    ]
    assert dag.edge_count == 3
    assert dag.node_count == 4


def test_causal_dag_rejects_directed_cycle():
    """Verify that introducing a cycle raises CausalCycleError immediately."""
    edges = [
        CausalEdge(
            source_metric="node_a",
            target_metric="node_b",
            weight=1.0,
            ci_lower=0.5,
            ci_upper=1.5,
            confidence=0.9,
            rationale="A to B",
        ),
        CausalEdge(
            source_metric="node_b",
            target_metric="node_c",
            weight=1.0,
            ci_lower=0.5,
            ci_upper=1.5,
            confidence=0.9,
            rationale="B to C",
        ),
        CausalEdge(
            source_metric="node_c",
            target_metric="node_a",
            weight=1.0,
            ci_lower=0.5,
            ci_upper=1.5,
            confidence=0.9,
            rationale="C to A (Cycle!)",
        ),
    ]

    with pytest.raises(CausalCycleError, match="Directed cycle detected in causal graph"):
        CausalDAG(edges=edges)


def test_causal_dag_path_reachability_and_weights():
    """Verify directed path discovery and multiplicative path weights."""
    edges = [
        CausalEdge(
            source_metric="X",
            target_metric="Y",
            weight=2.0,
            ci_lower=1.8,
            ci_upper=2.2,
            confidence=0.95,
            rationale="X to Y",
        ),
        CausalEdge(
            source_metric="Y",
            target_metric="Z",
            weight=3.0,
            ci_lower=2.7,
            ci_upper=3.3,
            confidence=0.95,
            rationale="Y to Z",
        ),
    ]
    dag = CausalDAG(edges=edges)

    assert dag.has_path("X", "Z")
    assert not dag.has_path("Z", "X")
    assert dag.path_weight("X", "Z") == pytest.approx(6.0, rel=1e-3)
