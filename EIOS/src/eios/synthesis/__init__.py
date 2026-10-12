"""Executive Synthesis Engine (F05 / Slice S1).

Delivers cross-domain causal intelligence, SCM DAG refutation caching,
predictive forecasting with 100% additive attribution, parametric scenario
shock simulation, daily morning briefings, and governed recommendations with
Doubly Robust AIPW propensity score logging.
"""

from eios.synthesis.aipw import AIPWEstimator, compute_propensity_score
from eios.synthesis.attribution import DriverAttributionEngine
from eios.synthesis.briefing import MorningBriefingGenerator
from eios.synthesis.forecast import MultivariateRidgeForecaster
from eios.synthesis.recommendations import RecommendationComposer
from eios.synthesis.scenario import ScenarioSimulator
from eios.synthesis.scm import CausalDAG, SCMCache
from eios.synthesis.scm_runner import SCMRunner

BriefingGenerator = MorningBriefingGenerator
Forecaster = MultivariateRidgeForecaster


class SynthesisEngine:
    """High-level facade orchestrating synthesis components."""

    def __init__(self) -> None:
        self.forecaster = MultivariateRidgeForecaster()
        self.attribution_engine = DriverAttributionEngine()
        self.scenario_simulator = ScenarioSimulator()
        self.briefing_generator = MorningBriefingGenerator()
        self.recommendation_composer = RecommendationComposer()
        self.aipw_estimator = AIPWEstimator()


__all__ = [
    "SynthesisEngine",
    "SCMRunner",
    "SCMCache",
    "CausalDAG",
    "Forecaster",
    "MultivariateRidgeForecaster",
    "DriverAttributionEngine",
    "ScenarioSimulator",
    "BriefingGenerator",
    "MorningBriefingGenerator",
    "RecommendationComposer",
    "AIPWEstimator",
    "compute_propensity_score",
]
