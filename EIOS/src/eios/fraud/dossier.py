"""Investigation Dossier Synthesis & Evidence Assembler (US6 / Module B).

Authoritative References:
- docs/brief/fraud [BRIEF fraud]
- specs/009-partner-fraud/spec.md (US6, FR-010, FR-014, FR-016, FR-017)
- .specify/memory/constitution.md (Principles I, II, IV, VIII)
"""

import uuid
from datetime import UTC, datetime

from eios.fraud.models import (
    BonusAbuseProfile,
    FraudTypology,
    PartnerFraudCase,
    RecyclingCluster,
    RingAttribution,
    TradingPairCorrelation,
    TrafficAnomalySignal,
)
from eios.fraud.sanitizer import FraudComplianceSanitizer


class FraudDossierAssembler:
    """Compiles multi-source evidence across data products into an executive case dossier."""

    def __init__(self, sanitizer: FraudComplianceSanitizer | None = None) -> None:
        self.sanitizer = sanitizer or FraudComplianceSanitizer()

    def assemble_dossier(
        self,
        partner_id: str,
        trading_pairs: list[TradingPairCorrelation] | None = None,
        ring_attribution: RingAttribution | None = None,
        bonus_profile: BonusAbuseProfile | None = None,
        recycling_cluster: RecyclingCluster | None = None,
        traffic_signal: TrafficAnomalySignal | None = None,
        is_replay_fallback: bool = False,
    ) -> PartnerFraudCase:
        """Deterministically assemble evidence into a PartnerFraudCase."""
        trading_pairs = trading_pairs or []
        evidence_refs: list[str] = []
        implicated_accounts: set[str] = set()

        total_exposure = 0.0
        primary_typology = FraudTypology.OPPOSITE_TRADING_SYNDICATE

        # 1. Trading pair evidence
        partner_pairs = [
            p for p in trading_pairs if p.partner_a == partner_id or p.partner_b == partner_id
        ]
        if partner_pairs:
            for p in partner_pairs:
                evidence_refs.append(f"trading_activity/{p.pair_id}")
                implicated_accounts.add(p.account_a)
                implicated_accounts.add(p.account_b)
                total_exposure += p.total_commission_extracted_usd
            if any(p.directional_type.value == "MIRROR" for p in partner_pairs):
                primary_typology = FraudTypology.MIRROR_TRADING_RING
            else:
                primary_typology = FraudTypology.OPPOSITE_TRADING_SYNDICATE

        # 2. Ring attribution evidence
        master_id = None
        if ring_attribution:
            master_id = ring_attribution.master_partner_id
            evidence_refs.append(f"partner_network/{ring_attribution.ring_id}")
            if ring_attribution.flagged_abuse_commission_usd > 0:
                total_exposure = max(total_exposure, ring_attribution.flagged_abuse_commission_usd)
            if ring_attribution.hierarchy_depth > 1:
                primary_typology = FraudTypology.MULTI_TIER_COMMISSION_FRAUD

        # 3. Bonus abuse evidence
        if bonus_profile and bonus_profile.status == "HIGH_BONUS_ABUSE_RISK":
            evidence_refs.append(f"bonus_ledger/{partner_id}_lifecycle")
            total_exposure += bonus_profile.cpa_bounty_collected_usd
            if not partner_pairs:
                primary_typology = FraudTypology.BONUS_CPA_HARVESTING

        # 4. Recycling cluster evidence
        if recycling_cluster:
            evidence_refs.append(f"identity_cluster/{recycling_cluster.identity_cluster_key}")
            for acc in recycling_cluster.linked_client_ids:
                implicated_accounts.add(acc)
            total_exposure += recycling_cluster.total_promotions_harvested_usd
            if not partner_pairs and (
                not bonus_profile or bonus_profile.status != "HIGH_BONUS_ABUSE_RISK"
            ):
                primary_typology = FraudTypology.CLIENT_RECYCLING

        # 5. Traffic anomaly evidence
        if traffic_signal and traffic_signal.anomaly_flag:
            evidence_refs.append(f"clickstream/{partner_id}_funnel")
            if not partner_pairs and not bonus_profile:
                primary_typology = FraudTypology.BOT_TRAFFIC_FUNNEL

        # Calculate composite fraud risk score (deterministic Python)
        risk_components: list[float] = []
        if partner_pairs:
            risk_components.append(max(p.collusion_confidence for p in partner_pairs))
        if ring_attribution:
            risk_components.append(ring_attribution.ring_risk_score)
        if bonus_profile:
            risk_components.append(bonus_profile.abuse_probability)
        if recycling_cluster:
            risk_components.append(recycling_cluster.syndicate_risk_score)
        if traffic_signal:
            risk_components.append(traffic_signal.bot_traffic_probability)

        fraud_risk_score = round(max(risk_components, default=0.10), 4)

        # Confidence level
        if fraud_risk_score >= 0.85:
            confidence_level = "CRITICAL"
            recommended_action = "SuspendPartner"
        elif fraud_risk_score >= 0.65:
            confidence_level = "HIGH"
            recommended_action = "ClawbackCommission"
        elif fraud_risk_score >= 0.40:
            confidence_level = "MEDIUM"
            recommended_action = "AdjustPartnerTier"
        else:
            confidence_level = "LOW"
            recommended_action = "ReviewAudit"

        # Build narrative summary
        replay_prefix = "[REPLAY] " if is_replay_fallback else ""
        raw_summary = (
            f"{replay_prefix}Compliance investigation case for partner {partner_id}. "
            f"Primary identified typology: {primary_typology.value}. "
            f"Observed {len(partner_pairs)} correlated trading pairs and {len(implicated_accounts)} implicated accounts. "
            f"Total financial exposure quantified at ${total_exposure:,.2f} USD with {confidence_level} confidence. "
            f"Root master partner attribution: {master_id or 'SELF'}."
        )

        sanitized_summary = self.sanitizer.sanitize(raw_summary)

        case_id = f"CASE-FRAUD-{uuid.uuid4().hex[:8].upper()}"

        return PartnerFraudCase(
            case_id=case_id,
            partner_id=partner_id,
            master_partner_id=master_id,
            primary_typology=primary_typology,
            fraud_risk_score=fraud_risk_score,
            total_exposure_usd=round(total_exposure, 2),
            confidence_level=confidence_level,
            implicated_accounts=sorted(list(implicated_accounts)),
            evidence_refs=evidence_refs,
            narrative_summary=sanitized_summary,
            recommended_action=recommended_action,
            created_at=datetime.now(UTC),
            status="OPEN",
        )
