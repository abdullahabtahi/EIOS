"""Parametric scenario shock simulation engine with mitigation ranking (T021, US3).

Traverses the structural causal graph in topological order to propagate exogenous
shocks, compute empirical confidence intervals, and evaluate ranked defensive actions.
"""

import time
import warnings

from eios.synthesis.exceptions import ExtrapolationWarning
from eios.synthesis.models import (
    MitigationOption,
    ScenarioShockSpec,
    ScenarioSimulationResult,
)
from eios.synthesis.scm import CausalDAG


class ScenarioSimulator:
    """Simulates exogenous shock propagation over a CausalDAG."""

    def __init__(self, dag: CausalDAG | None = None) -> None:
        if dag is None:
            from eios.synthesis.scm_runner import SCMRunner

            self.dag = SCMRunner.build_default_dag().dag
        else:
            self.dag = dag

    def _propagate_topological(self, direct_shocks: dict[str, float]) -> dict[str, float]:
        """Traverse SCM DAG in topological order and accumulate structural shock effects."""
        deltas: dict[str, float] = dict(direct_shocks)
        topological_nodes = self.dag.topological_order()

        for node in topological_nodes:
            parents = self.dag.predecessors(node)
            if not parents:
                continue

            incoming_sum = 0.0
            has_incoming = False
            for p in parents:
                if p in deltas:
                    has_incoming = True
                    edge = self.dag._edges.get((p, node))
                    w = edge.weight if edge else 1.0
                    incoming_sum += deltas[p] * w

            if has_incoming:
                current_val = deltas.get(node, 0.0) if node in direct_shocks else 0.0
                deltas[node] = round(current_val + incoming_sum, 4)

        return deltas

    def simulate(self, shock_spec: ScenarioShockSpec) -> ScenarioSimulationResult:
        """Simulate shock propagation and generate ranked mitigation actions."""
        start_time = time.perf_counter()

        # Check for extreme shock magnitude triggering extrapolation warning
        is_extreme = False
        for metric, shock_val in shock_spec.shocks.items():
            if abs(shock_val) > 3.0:
                is_extreme = True
                warnings.warn(
                    f"Extreme outlier shock detected for '{metric}' (magnitude={shock_val}). "
                    "Linear causal extrapolation bounds may widen significantly.",
                    category=ExtrapolationWarning,
                    stacklevel=2,
                )

        # Topological propagation
        deltas = self._propagate_topological(shock_spec.shocks)

        # Compute confidence intervals
        confidence_intervals: dict[str, tuple[float, float]] = {}
        error_factor = 0.50 if is_extreme else 0.15

        for metric, delta in deltas.items():
            half_width = max(abs(delta) * error_factor, 0.01)
            ci_lower = round(delta - half_width, 4)
            ci_upper = round(delta + half_width, 4)
            confidence_intervals[metric] = (ci_lower, ci_upper)

        # Rank mitigation options if adverse impact is detected
        mitigations = self._evaluate_mitigations(deltas)

        # Compile modeling assumptions
        assumptions = [
            "Linear structural causal additive model",
            "Invariant market baseline elasticity",
        ]
        for a in shock_spec.assumptions:
            if a not in assumptions:
                assumptions.append(a)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return ScenarioSimulationResult(
            scenario_name=shock_spec.scenario_name,
            propagated_deltas=deltas,
            confidence_intervals=confidence_intervals,
            mitigation_options=mitigations,
            assumptions_applied=assumptions,
            execution_time_ms=round(elapsed_ms, 2),
        )

    def _evaluate_mitigations(self, deltas: dict[str, float]) -> list[MitigationOption]:
        """Rank defensive strategic actions responding to adverse simulated outcomes."""
        options: list[MitigationOption] = []

        loss_usd = abs(deltas.get("net_deposit_volume_usd", 0.0))
        churn_increase = deltas.get("partner_churn_rate", 0.0)

        if loss_usd > 0 or churn_increase > 0:
            # Option 1: AdjustPartnerTier
            cost_1 = 1500.0
            recov_1 = max(loss_usd * 0.45, 4500.0)
            options.append(
                MitigationOption(
                    action_type="AdjustPartnerTier",
                    target_cohort="tier_1_emea_partners",
                    estimated_cost_usd=cost_1,
                    estimated_revenue_recovered_usd=round(recov_1, 2),
                    roi_ratio=round(recov_1 / cost_1, 2),
                    confidence=0.88,
                )
            )

            # Option 2: LaunchRetentionCampaign
            cost_2 = 2500.0
            recov_2 = max(loss_usd * 0.65, 7500.0)
            options.append(
                MitigationOption(
                    action_type="LaunchRetentionCampaign",
                    target_cohort="at_risk_active_partners",
                    estimated_cost_usd=cost_2,
                    estimated_revenue_recovered_usd=round(recov_2, 2),
                    roi_ratio=round(recov_2 / cost_2, 2),
                    confidence=0.82,
                )
            )

            # Option 3: ReviewSpreadPricing
            cost_3 = 800.0
            recov_3 = max(loss_usd * 0.20, 2000.0)
            options.append(
                MitigationOption(
                    action_type="ReviewSpreadPricing",
                    target_cohort="high_margin_vip_clients",
                    estimated_cost_usd=cost_3,
                    estimated_revenue_recovered_usd=round(recov_3, 2),
                    roi_ratio=round(recov_3 / cost_3, 2),
                    confidence=0.79,
                )
            )

        # Sort by ROI descending
        options.sort(key=lambda o: o.roi_ratio, reverse=True)
        return options
