"""EIOS Partner Churn Radar Package (Slice S2 / Module C).

Delivers predictive partner disengagement intelligence:
- Discrete-Time Hazard Model across five signal families
- Seasonality-aware change-point detection (zero false alarms)
- Value-at-Risk prioritization and ranking
- Regional and segment systemic cohort anomaly detection
- Governed Action Intent playbooks and Doubly Robust AIPW flywheel
- GenAI unstructured pattern discovery via LLM gateway
"""

from eios.churn.change_point import SeasonalityChangePointDetector
from eios.churn.cohort_detector import CohortRiskDetector
from eios.churn.explainer import ChurnSignalExplainer
from eios.churn.features import PartnerFeatureExtractor
from eios.churn.flywheel import AIPWCausalEstimator, PlaybookRecalibrator
from eios.churn.hazard_model import DiscreteTimeHazardModel
from eios.churn.models import (
    ActionIntentProposal,
    ChurnExplanationRecord,
    CohortAlertsResponse,
    CohortAnomalyAlert,
    DecisionOutcomeRecord,
    DisengagementTheme,
    HazardScore,
    InterventionWindow,
    PartnerSignalsResponse,
    RiskTier,
    SignalContribution,
    SignalFamily,
)
from eios.churn.narrative import ChurnNarrativeGenerator
from eios.churn.pattern_discovery import PatternDiscoverySpecialist
from eios.churn.pipeline import ChurnRadarPipeline
from eios.churn.sanitizer import PIISanitizer

__all__ = [
    "AIPWCausalEstimator",
    "ActionIntentProposal",
    "ChurnExplanationRecord",
    "ChurnNarrativeGenerator",
    "ChurnRadarPipeline",
    "ChurnSignalExplainer",
    "CohortAlertsResponse",
    "CohortAnomalyAlert",
    "CohortRiskDetector",
    "DecisionOutcomeRecord",
    "DiscreteTimeHazardModel",
    "DisengagementTheme",
    "HazardScore",
    "InterventionWindow",
    "PartnerFeatureExtractor",
    "PartnerSignalsResponse",
    "PatternDiscoverySpecialist",
    "PIISanitizer",
    "PlaybookRecalibrator",
    "RiskTier",
    "SeasonalityChangePointDetector",
    "SignalContribution",
    "SignalFamily",
]
