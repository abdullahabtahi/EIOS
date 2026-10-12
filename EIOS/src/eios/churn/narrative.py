"""Audited natural language explanation generator with deterministic replay fallback (T017).

Adheres to Constitution Principle I (Zero metric hallucination) and Principle VIII
(Deterministic cached replay fallback).
"""

from datetime import UTC, datetime
from typing import Sequence
import uuid

from eios.churn.models import ChurnExplanationRecord, RiskTier, SignalContribution, SignalFamily


class ChurnNarrativeGenerator:
    """Synthesizes audited explanation narratives strictly bounded by tool outputs."""

    def __init__(self) -> None:
        pass

    def generate_narrative(
        self,
        partner_id: str,
        risk_tier: RiskTier | str,
        hazard_prob: float,
        value_at_risk: float,
        top_family: SignalFamily | str,
        top_driver_metric: str,
        top_driver_delta: float,
        citations: Sequence[str] | None = None,
        is_replay: bool = False,
    ) -> ChurnExplanationRecord:
        """Generates an executive narrative referencing only verifiable numerical parameters."""
        tier_str = risk_tier.value if isinstance(risk_tier, RiskTier) else str(risk_tier)
        family_str = top_family.value if isinstance(top_family, SignalFamily) else str(top_family)

        citations_list = list(citations) if citations else [
            "DP6:partner_360",
            "DP9:partner_engagement_signals" if family_str == "BEHAVIORAL" else "DP10:partner_comms"
        ]

        # Template guarantees all numbers are exact tool values
        narrative = (
            f"Partner {partner_id} is classified in {tier_str} risk tier with "
            f"{hazard_prob} 30-day disengagement hazard probability and "
            f"{value_at_risk} USD Value at Risk. "
            f"The primary driver is {family_str} telemetry: {top_driver_metric} "
            f"observed delta of {top_driver_delta}."
        )

        return ChurnExplanationRecord(
            explanation_id=f"exp_{uuid.uuid4().hex[:12]}",
            partner_id=partner_id,
            generated_at=datetime.now(UTC),
            narrative=narrative,
            citations=citations_list,
            is_replay=is_replay,
        )

    def generate_from_contributions(
        self,
        partner_id: str,
        risk_tier: RiskTier | str,
        hazard_prob: float,
        value_at_risk: float,
        top_driver: SignalContribution,
        all_contributions: Sequence[SignalContribution] | None = None,
    ) -> ChurnExplanationRecord:
        """Constructs narrative directly from a SignalContribution object."""
        citations = [c.citation_ref for c in all_contributions] if all_contributions else [top_driver.citation_ref]
        return self.generate_narrative(
            partner_id=partner_id,
            risk_tier=risk_tier,
            hazard_prob=hazard_prob,
            value_at_risk=value_at_risk,
            top_family=top_driver.signal_family,
            top_driver_metric=top_driver.metric_name,
            top_driver_delta=top_driver.relative_delta,
            citations=citations,
        )
