"""Additive Driver Attribution Engine with Hare-Niemeyer rounding (T017, US2).

Decomposes forecast variances into constituent driver contributions along SCM DAG
paths, strictly guaranteeing that percentage shares sum to 100.0% +- 0.001%.
"""

from collections.abc import Sequence

from eios.synthesis.models import DriverAttribution
from eios.synthesis.scm import CausalDAG


class DriverAttributionEngine:
    """Path-based structural driver attribution engine."""

    def __init__(self, dag: CausalDAG) -> None:
        self.dag = dag

    def attribute_drivers(
        self,
        outcome_metric: str,
        driver_deltas: dict[str, float],
    ) -> list[DriverAttribution]:
        """Decompose outcome variance across candidate driver deltas.

        Strict invariant: Sum of percentage shares equals 100.0% exactly.
        """
        k_drivers = len(driver_deltas)
        if k_drivers == 0:
            return []

        # 1. Calculate path impacts along active SCM edges
        raw_impacts: dict[str, float] = {}
        for driver, delta in driver_deltas.items():
            if self.dag.has_path(driver, outcome_metric):
                path_w = self.dag.path_weight(driver, outcome_metric)
                impact = delta * path_w
            else:
                impact = 0.0
            raw_impacts[driver] = impact

        total_abs_impact = sum(abs(v) for v in raw_impacts.values())

        # 2. Handle zero-delta fallback: balanced uniform distribution
        if total_abs_impact < 1e-12:
            equal_pct = 100.0 / float(k_drivers)
            result = []
            accumulated = 0.0
            driver_keys = list(driver_deltas.keys())
            for idx, driver in enumerate(driver_keys):
                if idx == k_drivers - 1:
                    pct = round(100.0 - accumulated, 4)
                else:
                    pct = round(equal_pct, 4)
                    accumulated += pct

                result.append(
                    DriverAttribution(
                        driver_metric=driver,
                        absolute_impact=0.0,
                        percentage=pct,
                        direction="POSITIVE",
                    )
                )
            return result

        # 3. Compute fractional percentage shares
        exact_shares: dict[str, float] = {}
        for driver, impact in raw_impacts.items():
            exact_shares[driver] = (abs(impact) / total_abs_impact) * 100.0

        # 4. Hare-Niemeyer (Largest Remainder) Rounding to 2 decimal places
        # Scale to integer basis points of 100% (10,000 units = 100.00%)
        scaled = {d: s * 100.0 for d, s in exact_shares.items()}
        floored = {d: int(val) for d, val in scaled.items()}
        remainders = {d: scaled[d] - floored[d] for d in scaled}

        diff = 10000 - sum(floored.values())
        # Sort keys by largest remainder descending
        sorted_by_remainder = sorted(remainders.keys(), key=lambda d: remainders[d], reverse=True)

        for i in range(diff):
            floored[sorted_by_remainder[i % len(sorted_by_remainder)]] += 1

        final_pcts = {d: floored[d] / 100.0 for d in floored}

        # 5. Build DriverAttribution models
        attributions: list[DriverAttribution] = []
        for driver in driver_deltas.keys():
            impact = raw_impacts[driver]
            pct = final_pcts[driver]
            direction = "POSITIVE" if impact >= 0 else "NEGATIVE"

            attributions.append(
                DriverAttribution(
                    driver_metric=driver,
                    absolute_impact=round(impact, 4),
                    percentage=round(pct, 2),
                    direction=direction,
                )
            )

        return attributions

    def rank_top_drivers(
        self,
        attributions: Sequence[DriverAttribution],
        top_k: int = 3,
    ) -> list[DriverAttribution]:
        """Rank driver attributions by magnitude of impact."""
        return sorted(attributions, key=lambda a: a.percentage, reverse=True)[:top_k]
