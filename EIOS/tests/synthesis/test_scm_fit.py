"""The data-fitted causal model recovers the planted coefficients and rejects the planted control (spec 034)."""

import numpy as np
import pytest

from eios.foundry.scenarios.executive_world import (
    CALENDAR,
    CHURN,
    FTD,
    PAYOUT,
    REVENUE,
    SERIES,
    SPREAD,
    ExecutiveWorldConfig,
    build_executive_world,
    calendar_regressors,
)
from eios.synthesis.scm_fit import CandidateEdge, EmpiricalSCMFitter

CHAIN = (
    CandidateEdge(PAYOUT, CHURN, "payout moves churn"),
    CandidateEdge(CHURN, FTD, "churn moves first deposits"),
    CandidateEdge(FTD, REVENUE, "first deposits move revenue", adjust=CALENDAR),
)
ADJUSTED_CONTROL = CandidateEdge(SPREAD, CHURN, "control", adjust=(PAYOUT,), control=True)
NAIVE_CONTROL = CandidateEdge(SPREAD, CHURN, "control, no adjustment", control=True)
TRUTH = (0.90, -28000.0, 240.0)
SEEDS = range(7, 17)


def _fit(seed: int, candidates):
    world = build_executive_world(ExecutiveWorldConfig(seed=seed))
    data = {name: world.days[name].to_numpy() for name in SERIES} | calendar_regressors(
        len(world.days)
    )
    return EmpiricalSCMFitter(candidates, "test").fit(data)


@pytest.mark.parametrize("seed", SEEDS)
def test_chain_is_recovered_and_the_adjusted_control_is_rejected(seed):
    fit = _fit(seed, (*CHAIN, ADJUSTED_CONTROL))
    chain = fit.edges[:3]
    assert all(e.passed for e in chain), [e.report.failure_reason for e in chain]
    for edge, truth in zip(chain, TRUTH, strict=True):
        assert abs(edge.weight - truth) <= 0.30 * abs(
            truth
        )  # [ASSUMPTION] tolerance for a noisy two-year fit
        assert edge.ci_lower < edge.weight < edge.ci_upper
        assert edge.confidence >= 0.80
    assert fit.controls_rejected
    assert fit.manifest.active_edge_count == 3
    assert fit.manifest.rejected_placebo_count == 1


def test_a_control_is_judged_on_data_not_forced():
    """Anti-circularity: with no adjustment the spread edge passes the gate, so the verdict is not hard-wired."""
    fit = _fit(7, (*CHAIN, NAIVE_CONTROL))
    assert (
        not fit.controls_rejected
    )  # the refuters cannot see confounding; the adjustment set is what does


def test_fit_is_deterministic():
    a, b = _fit(7, CHAIN), _fit(7, CHAIN)
    assert [e.weight for e in a.edges] == [e.weight for e in b.edges]
    assert a.manifest.dataset_hash == b.manifest.dataset_hash


def test_too_little_history_is_refused():
    with pytest.raises(ValueError, match="at least"):
        EmpiricalSCMFitter(CHAIN, "t").fit({k: np.arange(10.0) for k in SERIES})
