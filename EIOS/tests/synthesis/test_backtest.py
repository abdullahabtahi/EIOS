"""The forecast is judged on past origins it did not see: skill against persistence and out-of-sample coverage (spec 034)."""

import numpy as np
import pytest

from eios.foundry.scenarios.executive_world import (
    PAYOUT,
    REVENUE,
    ExecutiveWorldConfig,
    build_executive_world,
)
from eios.synthesis.backtest import MIN_ORIGINS, forecast_with_interval, rolling_backtest

SEEDS = range(7, 17)


def _series(seed: int):
    days = build_executive_world(ExecutiveWorldConfig(seed=seed)).days
    return days[REVENUE].to_numpy(), {PAYOUT: days[PAYOUT].to_numpy()}


@pytest.mark.parametrize("seed", SEEDS)
def test_forecast_beats_persistence_on_every_seed(seed):
    y, leads = _series(seed)
    assert rolling_backtest(y, leads).mase < 1.0


def test_interval_covers_close_to_its_nominal_rate():
    coverage = [rolling_backtest(*_series(s)).coverage_out_of_sample for s in SEEDS]
    assert (
        0.80 <= float(np.mean(coverage)) <= 1.0
    )  # [ASSUMPTION] a 90% interval, held-out origins, ten seeds


def test_forecast_interval_brackets_the_point_and_is_reproducible():
    y, leads = _series(7)
    a, b = forecast_with_interval(y, leads), forecast_with_interval(y, leads)
    assert a.low < a.point < a.high
    assert (a.point, a.low, a.high) == (b.point, b.low, b.high)
    assert len(a.path) == a.horizon == 28


def test_too_few_origins_is_refused():
    y, leads = _series(7)
    with pytest.raises(ValueError, match=str(MIN_ORIGINS)):
        rolling_backtest(y[:230], {k: v[:230] for k, v in leads.items()})
