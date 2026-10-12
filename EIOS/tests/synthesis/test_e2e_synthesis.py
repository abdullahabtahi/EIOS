"""End-to-End full lifecycle integration test for Executive Synthesis Engine (T035).

Executes complete synthesis journey across all 6 user stories:
1. Multi-domain historical data ingestion & SCM DAG fitting/refutation caching (US1).
2. Multivariate forecasting & exact 100.0% driver attribution (US2).
3. Parametric scenario shock propagation & mitigation option ranking (US3).
4. Proactive morning briefing generation audited by Metric Auditor Gate (US4).
5. Governed recommendation card & signed ActionIntent token proposal (US5).
6. Doubly Robust AIPW treatment effect estimation on observational decision logs (US5).
"""

from eios.ontology.auditor.gate import MetricAuditorGate
from eios.ontology.metrics.catalog import create_default_registry
from eios.ontology.metrics.engine import MetricEngine
from eios.synthesis.aipw import AIPWEstimator
from eios.synthesis.attribution import DriverAttributionEngine
from eios.synthesis.briefing import MorningBriefingGenerator
from eios.synthesis.forecast import MultivariateRidgeForecaster
from eios.synthesis.models import ScenarioShockSpec
from eios.synthesis.recommendations import RecommendationComposer
from eios.synthesis.scenario import ScenarioSimulator
from eios.synthesis.scm import SCMCache
from eios.synthesis.scm_runner import SCMRunner


def test_full_synthesis_engine_e2e(  # noqa: PLR0915
    synthetic_timeseries_data, seeded_hot_state, tmp_path
):
    """Execute complete end-to-end synthesis lifecycle validating all architectural invariants."""
    # -------------------------------------------------------------
    # Step 1: US1 SCM Fitting, Refutation Battery, and Cache Serialization
    # -------------------------------------------------------------
    cache_path = tmp_path / "synthesis_scm_cache.json"
    runner = SCMRunner(model_version="v1.2.0-e2e")
    manifest = runner.fit_and_cache(
        data=synthetic_timeseries_data,
        cache_path=cache_path,
        n_bootstrap=50,
    )
    assert manifest.active_edge_count >= 3
    assert manifest.rejected_placebo_count >= 1

    scm_cache = SCMCache.load_from_file(cache_path)
    is_valid, reason = scm_cache.verify_causal_assertion(
        "competitor_payout_rate", "net_deposit_volume_usd"
    )
    assert is_valid is True
    assert "verified" in reason.lower()

    # -------------------------------------------------------------
    # Step 2: US2 Multivariate Forecasting & 100% Driver Attribution
    # -------------------------------------------------------------
    forecaster = MultivariateRidgeForecaster(alpha=1.0)
    target_ts = synthetic_timeseries_data["net_deposit_volume_usd"]
    leading_indicators = {
        "competitor_payout_rate": synthetic_timeseries_data["competitor_payout_rate"],
        "partner_churn_rate": synthetic_timeseries_data["partner_churn_rate"],
    }
    forecaster.fit(target_ts, leading_indicators=leading_indicators)
    forecast_res = forecaster.forecast(
        horizon=28,
        metric_id="net_deposit_volume_usd",
    )
    assert len(forecast_res.forecast_points) == 28
    assert forecast_res.baseline_mase < 1.0

    attrib_engine = DriverAttributionEngine(dag=scm_cache.dag)
    attrib_list = attrib_engine.attribute_drivers(
        outcome_metric="net_deposit_volume_usd",
        driver_deltas={
            "competitor_payout_rate": 0.05,
            "partner_churn_rate": 0.02,
            "ftd_count_28d": 150.0,
        },
    )
    total_pct = sum(a.percentage for a in attrib_list)
    assert abs(total_pct - 100.0) < 0.001

    # -------------------------------------------------------------
    # Step 3: US3 Parametric Scenario Shock Simulation
    # -------------------------------------------------------------
    simulator = ScenarioSimulator(dag=scm_cache.dag)
    shock_spec = ScenarioShockSpec(
        scenario_name="e2e_payout_shock",
        shocks={"competitor_payout_rate": 0.08},
    )
    sim_result = simulator.simulate(shock_spec)
    assert "partner_churn_rate" in sim_result.propagated_deltas
    assert sim_result.propagated_deltas["partner_churn_rate"] > 0
    assert len(sim_result.mitigation_options) >= 1

    # -------------------------------------------------------------
    # Step 4: US4 Executive Morning Briefing & Metric Auditor Gate
    # -------------------------------------------------------------
    registry = create_default_registry()
    metric_engine = MetricEngine(hot_state=seeded_hot_state, registry=registry)
    briefing_gen = MorningBriefingGenerator(
        metric_engine=metric_engine, cache_dir=tmp_path / "briefings"
    )
    briefing, tool_outputs = briefing_gen.generate_briefing_with_tool_evidence(
        briefing_date="2026-10-06"
    )
    assert len(briefing.insights) >= 3
    assert len(briefing.risks) >= 2
    assert len(briefing.opportunities) >= 1

    auditor = MetricAuditorGate()
    full_narrative = " ".join(
        item.summary for item in briefing.insights + briefing.risks + briefing.opportunities
    )
    audit_res = auditor.audit(response_text=full_narrative, tool_outputs=tool_outputs)
    assert audit_res.passed is True
    assert len(audit_res.untraceable_numbers) == 0

    # -------------------------------------------------------------
    # Step 5: US5 Governed Recommendation Composer & Action Intent
    # -------------------------------------------------------------
    composer = RecommendationComposer()
    rec_card = composer.compose_recommendation(
        action_type="AdjustPartnerTier",
        target_entity_id="P-101",
        impact_estimate=(12000.0, 24000.0),
        impact_unit="USD",
        pros=["Arrests partner attrition", "Restores referral flow"],
        cons=["Requires operational margin review", "Contract adjustment SLA 7 days"],
        confidence=0.89,
        evidence_citations=["partner_churn_rate", "net_deposit_volume_usd"],
        causal_context={"partner_churn_rate": 0.19, "tenure_months": 24.0},
    )
    assert 0.01 <= rec_card.propensity_score <= 0.99

    token = composer.propose_action_intent(
        card=rec_card,
        parameters={"partner_id": "P-101", "target_tier": "TIER_1"},
    )
    assert token.signature is not None
    assert token.status.value == "PENDING"
    assert len(token.approvals) == 0  # No autonomous execution

    # -------------------------------------------------------------
    # Step 6: US5 Doubly Robust AIPW Flywheel
    # -------------------------------------------------------------
    import numpy as np

    aipw = AIPWEstimator()
    rng = np.random.default_rng(seed=42)
    covariates = rng.normal(0.0, 1.0, (120, 2))
    treatment = (rng.uniform(0.0, 1.0, 120) < 0.5).astype(int)
    outcomes = 10.0 * treatment + covariates[:, 0] * 3.0 + rng.normal(0.0, 0.5, 120)
    ate_est = aipw.fit_estimate(covariates=covariates, treatment=treatment, outcomes=outcomes)
    assert abs(ate_est - 10.0) < 2.0
