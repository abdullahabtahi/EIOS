"""Executive synthesis causal truth generator, placebo edge injector, and driver attribution (FR-046 to FR-051)."""

from __future__ import annotations

from typing import Any

from eios.foundry.rng import RNGManager
from eios.foundry.storage.eval_truth_store import EvalGroundTruthStore


class CausalTruthGenerator:
    """Generates structural causal equations, placebo refuter edges, and 100% driver attribution."""

    def __init__(
        self,
        rng: RNGManager,
        truth_store: EvalGroundTruthStore | None = None,
    ) -> None:
        self.rng = rng
        self.truth_store = truth_store
        self._gen = rng.get_generator("causal_truth")

    def generate_causal_dag(self) -> dict[str, Any]:
        """Generates ground truth structural causal model across 4 domains with planted placebo edge."""
        dag_payload: dict[str, Any] = {
            "domains": ["COMPETITIVE", "PARTNER", "CLIENT", "FINANCIAL"],
            "structural_equations": {
                "PARTNER": "Delta_P = 0.65 * Delta_C + epsilon_P",
                "CLIENT": "Delta_Q = -0.45 * Delta_P + epsilon_Q",
                "FINANCIAL": "Delta_F = 0.80 * Delta_Q + epsilon_F",
            },
            "edges": [
                {
                    "edge_id": "EDGE_COMPETITIVE_TO_PARTNER",
                    "source": "COMPETITIVE",
                    "target": "PARTNER",
                    "true_structural_coefficient": 0.65,
                    "is_placebo": False,
                },
                {
                    "edge_id": "EDGE_PARTNER_TO_CLIENT",
                    "source": "PARTNER",
                    "target": "CLIENT",
                    "true_structural_coefficient": -0.45,
                    "is_placebo": False,
                },
                {
                    "edge_id": "EDGE_CLIENT_TO_FINANCIAL",
                    "source": "CLIENT",
                    "target": "FINANCIAL",
                    "true_structural_coefficient": 0.80,
                    "is_placebo": False,
                },
                {
                    "edge_id": "PLACEBO_EDGE_MARKETING_TO_LTV",
                    "source": "OPERATIONAL",
                    "target": "FINANCIAL",
                    "true_structural_coefficient": 0.0,
                    "is_placebo": True,
                    "spurious_correlation": 0.38,
                    "placebo_refuter_expected_p_value": 0.45,
                    "description": "Statistically confounded observational correlation with zero true causal effect.",
                },
            ],
        }

        if self.truth_store:
            self.truth_store.write_truth("synthesis/causal_dag.json", dag_payload)

        return dag_payload

    def generate_forecast_driver_attribution(self) -> dict[str, Any]:
        """Generates ground truth driver attribution decomposing forecast variance to exactly 100.0%."""
        attribution_payload: dict[str, Any] = {
            "scenario": "Q3_LTV_FORECAST_MISS",
            "forecast_miss_drivers": {
                "competitive": 40.0,
                "partner": 35.0,
                "operational": 25.0,
            },
            "unit": "PERCENTAGE_SHARE",
            "total_explained": 100.0,
        }

        if self.truth_store:
            self.truth_store.write_truth("synthesis/driver_attribution.json", attribution_payload)

        return attribution_payload
