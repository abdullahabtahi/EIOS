"""Synthesis Baseline: Seasonal-Naive Forecast & Equal Driver Attribution (T036).

Baseline to beat:
- Forecast: Seasonal-naive y_{t-28}
- Driver attribution: Equal split (33.3% / 33.3% / 33.3%)
Candidate model commitment:
- Forecast: MASE < 1.0 on holdout
- Attribution: Counterfactual decomposition sum = 100.0%, rank agreement with generator ground truth.
"""

from collections.abc import Sequence

from eios.evals.metrics import compute_mase


class SeasonalNaiveSynthesisBaseline:
    """Seasonal-naive forecaster and equal-split counterfactual driver attribution."""

    def __init__(self, seasonal_lag: int = 28) -> None:
        self.seasonal_lag = seasonal_lag

    def forecast(self, history: Sequence[float], horizon: int = 7) -> list[float]:
        """Forecast horizon steps ahead using value from history at lag t - seasonal_lag."""
        n = len(history)
        predictions: list[float] = []
        for h in range(horizon):
            target_idx = (n + h) - self.seasonal_lag
            if 0 <= target_idx < n:
                pred = history[target_idx]
            elif n > 0:
                pred = history[-1]
            else:
                pred = 0.0
            predictions.append(float(pred))
        return predictions

    def attribute_drivers(self, driver_names: Sequence[str]) -> dict[str, float]:
        """Equal-split attribution assigning identical percentage to each candidate driver."""
        k = len(driver_names)
        if k == 0:
            return {}
        equal_weight = 100.0 / float(k)
        return {d: equal_weight for d in driver_names}


def evaluate_synthesis_baseline(
    actual: Sequence[float],
    predicted: Sequence[float],
    drivers: Sequence[str] = ("driver_a", "driver_b", "driver_c"),
) -> dict[str, float]:
    mase = compute_mase(actual, predicted, seasonality=1)
    baseline = SeasonalNaiveSynthesisBaseline()
    attribution = baseline.attribute_drivers(drivers)
    equal_sum = sum(attribution.values())

    return {
        "mase": mase,
        "attribution_equal_split_sum": float(equal_sum),
    }
