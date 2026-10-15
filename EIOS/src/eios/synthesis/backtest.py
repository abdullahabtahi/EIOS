"""Rolling-origin backtest and empirical prediction interval for the ridge forecaster (spec 034).

The forecaster's own interval assumes normal residuals. Here the interval comes from what the model actually did:
refit at many past origins, forecast the same horizon each time, and keep the errors. The reported interval is the
empirical error quantiles around the new point forecast; its coverage is checked on origins held out from the
calibration. Skill is the model's mean absolute error against a persistence forecast (the last value, carried).
Leading indicators are standardised so the ridge penalty treats a rate and a dollar amount alike.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from eios.synthesis.forecast import MultivariateRidgeForecaster

DEFAULT_HORIZON = 28
DEFAULT_LAGS = (
    1,
    7,
    28,
    91,
)  # [ASSUMPTION] a week, a month and a quarter back: the quarterly lag is what beats persistence
FIRST_ORIGIN = 180
MIN_ORIGINS = 12  # [ASSUMPTION] fewer past origins cannot calibrate a 90% interval


@dataclass(frozen=True)
class Backtest:
    horizon: int
    origins: int
    mae: float
    persistence_mae: float
    nominal: float
    error_low: float  # the nominal-interval quantiles of (actual - forecast), all origins
    error_high: float
    coverage_out_of_sample: (
        float  # share of held-out origins inside the interval calibrated before them
    )

    @property
    def mase(self) -> float:
        """Model error over persistence error; below 1 beats carrying the last value forward."""
        return self.mae / self.persistence_mae if self.persistence_mae > 0 else float("inf")


@dataclass(frozen=True)
class IntervalForecast:
    horizon: int
    path: tuple[float, ...]
    point: float  # the value `horizon` steps ahead
    low: float
    high: float
    backtest: Backtest


def _zscore(
    series: Mapping[str, np.ndarray], upto: int
) -> tuple[dict[str, np.ndarray], dict[str, tuple[float, float]]]:
    stats = {k: (float(v[:upto].mean()), float(v[:upto].std()) or 1.0) for k, v in series.items()}
    return {k: (v - stats[k][0]) / stats[k][1] for k, v in series.items()}, stats


def _mean_reverting(z: np.ndarray, horizon: int) -> np.ndarray:
    """The indicator's next `horizon` values: today's z-score decaying toward its mean at its own fitted AR(1) rate."""
    phi = float(np.clip(np.corrcoef(z[:-1], z[1:])[0, 1], 0.0, 0.999)) if len(z) > 3 else 0.0
    return np.asarray(z[-1] * phi ** np.arange(1, horizon + 1))


def _forecast_path(
    y: np.ndarray, leads: Mapping[str, np.ndarray], origin: int, horizon: int, lags: Sequence[int]
) -> np.ndarray:
    z, _ = _zscore({k: v[:origin] for k, v in leads.items()}, origin)
    model = MultivariateRidgeForecaster(lags=lags).fit(y[:origin], leading_indicators=z)
    held = {k: _mean_reverting(v, horizon) for k, v in z.items()}
    return np.asarray(model.forecast(horizon=horizon, leading_future=held).forecast_points)


def rolling_backtest(
    y: Sequence[float],
    leads: Mapping[str, Sequence[float]],
    horizon: int = DEFAULT_HORIZON,
    first_origin: int = FIRST_ORIGIN,
    stride: int = 7,
    nominal: float = 0.90,
    lags: Sequence[int] = DEFAULT_LAGS,
) -> Backtest:
    arr = np.asarray(y, dtype=float)
    lead = {k: np.asarray(v, dtype=float) for k, v in leads.items()}
    origins = list(range(first_origin, len(arr) - horizon + 1, stride))
    if len(origins) < MIN_ORIGINS:
        raise ValueError(f"need at least {MIN_ORIGINS} past origins, have {len(origins)}")
    errors, naive = [], []
    for o in origins:
        path = _forecast_path(arr, lead, o, horizon, lags)
        actual = arr[o + horizon - 1]
        errors.append(actual - path[-1])
        naive.append(actual - arr[o - 1])
    err = np.asarray(errors)
    tail = (1.0 - nominal) / 2.0
    split = int(len(err) * 0.7)
    lo, hi = np.quantile(err[:split], [tail, 1.0 - tail])
    held_out = err[split:]
    return Backtest(
        horizon=horizon,
        origins=len(origins),
        mae=float(np.mean(np.abs(err))),
        persistence_mae=float(np.mean(np.abs(naive))),
        nominal=nominal,
        error_low=float(np.quantile(err, tail)),
        error_high=float(np.quantile(err, 1.0 - tail)),
        coverage_out_of_sample=float(np.mean((held_out >= lo) & (held_out <= hi))),
    )


def forecast_with_interval(
    y: Sequence[float],
    leads: Mapping[str, Sequence[float]],
    horizon: int = DEFAULT_HORIZON,
    lags: Sequence[int] = DEFAULT_LAGS,
    **backtest_args: float,
) -> IntervalForecast:
    arr = np.asarray(y, dtype=float)
    lead = {k: np.asarray(v, dtype=float) for k, v in leads.items()}
    bt = rolling_backtest(arr, lead, horizon=horizon, lags=lags, **backtest_args)  # type: ignore[arg-type]
    path = _forecast_path(arr, lead, len(arr), horizon, lags)
    point = float(path[-1])
    return IntervalForecast(
        horizon=horizon,
        path=tuple(float(v) for v in path),
        point=point,
        low=point + bt.error_low,
        high=point + bt.error_high,
        backtest=bt,
    )
