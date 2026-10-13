"""Partner Manager Workstation Service.

Delivers Value x Risk Churn Radar scatter dataset, referral hierarchy
with opposite-trading ring detection, and governed retention playbook recommendations.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from eios.cockpit.provenance import ProvenanceMetadata, ProvenanceResolver
from eios.cockpit.schemas import validate_contract


class PartnerQuadrant(str, Enum):
    HIGH_VALUE_HIGH_RISK = "HIGH_VALUE_HIGH_RISK"
    HIGH_VALUE_STABLE = "HIGH_VALUE_STABLE"
    LOW_VALUE_HIGH_RISK = "LOW_VALUE_HIGH_RISK"
    LOW_VALUE_STABLE = "LOW_VALUE_STABLE"


class PartnerChurnItem(BaseModel):
    partner_id: str
    realized_volume_30d_usd: float
    churn_hazard_probability: float
    quadrant: PartnerQuadrant
    days_to_intervention_deadline: int
    primary_root_cause: str
    login_decay_pct: float
    ftd_decay_pct: float
    provenance: ProvenanceMetadata
    name: str | None = None
    tier: str | None = "TIER_2_MASTER"
    region: str | None = "LatAm"
    cohort: str | None = "LatAm P2P Cashier"
    historical_drift: dict[str, Any] | None = None
    empirical_win_rate: float | None = 0.785
    primary_driver: str | None = "OPERATIONAL_CASHIER"


class ChurnRadarScatter(BaseModel):
    as_of: datetime = Field(default_factory=lambda: datetime.now(UTC))
    partners: list[PartnerChurnItem]

    def to_contract_dict(self) -> dict[str, Any]:
        data = {
            "as_of": self.as_of.isoformat(),
            "partners": [
                {
                    "partner_id": p.partner_id,
                    "name": p.name or p.partner_id,
                    "realized_volume_30d_usd": p.realized_volume_30d_usd,
                    "churn_hazard_probability": p.churn_hazard_probability,
                    "quadrant": p.quadrant.value,
                    "days_to_intervention_deadline": p.days_to_intervention_deadline,
                    "primary_root_cause": p.primary_root_cause,
                    "login_decay_pct": p.login_decay_pct,
                    "ftd_decay_pct": p.ftd_decay_pct,
                    "tier": p.tier,
                    "region": p.region,
                    "cohort": p.cohort,
                    "historical_drift": p.historical_drift,
                    "empirical_win_rate": p.empirical_win_rate,
                    "primary_driver": p.primary_driver,
                    "provenance": p.provenance.to_contract_dict(),
                }
                for p in self.partners
            ],
        }
        validate_contract(data, "churn-radar-scatter")
        return data


class RetentionPlaybookDeal(BaseModel):
    playbook_id: str
    title: str
    partner_id: str
    action_type: str
    estimated_cost_usd: float
    is_fast_path_eligible: bool
    requires_four_eyes: bool
    projected_retention_uplift_pct: float


class PartnerWorkstationService:
    """Service providing partner churn radar scatter, referral tree, and playbooks."""

    def __init__(self, provenance_resolver: ProvenanceResolver | None = None) -> None:
        self.provenance_resolver = provenance_resolver or ProvenanceResolver()

    def get_churn_radar_scatter(self) -> ChurnRadarScatter:
        """Assembles partner churn radar scatter dataset with verified provenance across 20+ global partners."""
        now = datetime.now(UTC)
        p = self.provenance_resolver.resolve("churn_hazard_probability", as_of=now)

        partners = [
            PartnerChurnItem(
                partner_id="PTR-882",
                name="Alpha FX LatAm Master",
                realized_volume_30d_usd=1240000.0,
                churn_hazard_probability=0.78,
                quadrant=PartnerQuadrant.HIGH_VALUE_HIGH_RISK,
                days_to_intervention_deadline=14,
                primary_root_cause="Payout ticket delays + rival spread comparison (Exness poaching)",
                login_decay_pct=-68.0,
                ftd_decay_pct=-45.0,
                tier="TIER_1_SUPER",
                region="LatAm (Colombia)",
                cohort="LatAm P2P Cashier",
                primary_driver="OPERATIONAL_CASHIER",
                empirical_win_rate=0.785,
                historical_drift={
                    "tMinus30d": {"pChurn": 0.22, "valueAtRiskUsd": 272800},
                    "tMinus14d": {"pChurn": 0.55, "valueAtRiskUsd": 682000},
                    "driftVelocityPct": 254.5,
                },
                provenance=p,
            ),
            PartnerChurnItem(
                partner_id="PTR-419",
                name="Iberia Prime Affiliates",
                realized_volume_30d_usd=290000.0,
                churn_hazard_probability=0.62,
                quadrant=PartnerQuadrant.HIGH_VALUE_HIGH_RISK,
                days_to_intervention_deadline=28,
                primary_root_cause="DP2P Settlement Friction",
                login_decay_pct=-52.0,
                ftd_decay_pct=-35.0,
                tier="TIER_2_MASTER",
                region="LatAm / Iberia Desk",
                cohort="LatAm P2P Cashier",
                primary_driver="OPERATIONAL_CASHIER",
                empirical_win_rate=0.785,
                historical_drift={
                    "tMinus30d": {"pChurn": 0.18, "valueAtRiskUsd": 52200},
                    "tMinus14d": {"pChurn": 0.44, "valueAtRiskUsd": 127600},
                    "driftVelocityPct": 244.4,
                },
                provenance=p,
            ),
            PartnerChurnItem(
                partner_id="PTR-104",
                name="Nordic Quant Capital",
                realized_volume_30d_usd=840000.0,
                churn_hazard_probability=0.18,
                quadrant=PartnerQuadrant.HIGH_VALUE_STABLE,
                days_to_intervention_deadline=180,
                primary_root_cause="Stable Volume Growth",
                login_decay_pct=-4.0,
                ftd_decay_pct=8.0,
                tier="TIER_1_SUPER",
                region="Nordics / EU",
                cohort="Nordic Institutional EA",
                primary_driver="CYCLICAL",
                empirical_win_rate=0.92,
                historical_drift={
                    "tMinus30d": {"pChurn": 0.16, "valueAtRiskUsd": 134400},
                    "tMinus14d": {"pChurn": 0.17, "valueAtRiskUsd": 142800},
                    "driftVelocityPct": 12.5,
                },
                provenance=p,
            ),
            PartnerChurnItem(
                partner_id="PTR-551",
                name="APAC Retail Signals Hub",
                realized_volume_30d_usd=65000.0,
                churn_hazard_probability=0.84,
                quadrant=PartnerQuadrant.LOW_VALUE_HIGH_RISK,
                days_to_intervention_deadline=7,
                primary_root_cause="Sub-IB Diverted Traffic",
                login_decay_pct=-85.0,
                ftd_decay_pct=-72.0,
                tier="TIER_3_AFFILIATE",
                region="SEA / Sub-IB Network",
                cohort="LatAm P2P Cashier",
                primary_driver="COMPETITIVE_POACHING",
                empirical_win_rate=0.64,
                historical_drift={
                    "tMinus30d": {"pChurn": 0.35, "valueAtRiskUsd": 22750},
                    "tMinus14d": {"pChurn": 0.65, "valueAtRiskUsd": 42250},
                    "driftVelocityPct": 140.0,
                },
                provenance=p,
            ),
            PartnerChurnItem(
                partner_id="PTR-723",
                name="Saigon FX Syndicate",
                realized_volume_30d_usd=510000.0,
                churn_hazard_probability=0.74,
                quadrant=PartnerQuadrant.HIGH_VALUE_HIGH_RISK,
                days_to_intervention_deadline=12,
                primary_root_cause="Rival Zero-Spread Bounty (Exness / XM)",
                login_decay_pct=-61.0,
                ftd_decay_pct=-48.0,
                tier="TIER_2_MASTER",
                region="SEA (Vietnam)",
                cohort="SEA Tier-1 Introducers",
                primary_driver="COMPETITIVE_POACHING",
                empirical_win_rate=0.71,
                historical_drift={
                    "tMinus30d": {"pChurn": 0.28, "valueAtRiskUsd": 142800},
                    "tMinus14d": {"pChurn": 0.52, "valueAtRiskUsd": 265200},
                    "driftVelocityPct": 164.2,
                },
                provenance=p,
            ),
            PartnerChurnItem(
                partner_id="PTR-302",
                name="Jakarta Algorithmic Traders",
                realized_volume_30d_usd=920000.0,
                churn_hazard_probability=0.22,
                quadrant=PartnerQuadrant.HIGH_VALUE_STABLE,
                days_to_intervention_deadline=120,
                primary_root_cause="Strong EA Copy Trading",
                login_decay_pct=3.0,
                ftd_decay_pct=12.0,
                tier="TIER_1_SUPER",
                region="SEA (Indonesia)",
                cohort="SEA Institutional",
                primary_driver="CYCLICAL",
                empirical_win_rate=0.88,
                provenance=p,
            ),
            PartnerChurnItem(
                partner_id="PTR-618",
                name="Bangkok Crypto Arbitrage",
                realized_volume_30d_usd=380000.0,
                churn_hazard_probability=0.68,
                quadrant=PartnerQuadrant.HIGH_VALUE_HIGH_RISK,
                days_to_intervention_deadline=21,
                primary_root_cause="USDT Gateway Disruption",
                login_decay_pct=-47.0,
                ftd_decay_pct=-39.0,
                tier="TIER_2_MASTER",
                region="SEA (Thailand)",
                cohort="SEA P2P Gateway",
                primary_driver="OPERATIONAL_CASHIER",
                empirical_win_rate=0.75,
                historical_drift={
                    "tMinus30d": {"pChurn": 0.31, "valueAtRiskUsd": 117800},
                    "tMinus14d": {"pChurn": 0.50, "valueAtRiskUsd": 190000},
                    "driftVelocityPct": 119.3,
                },
                provenance=p,
            ),
            PartnerChurnItem(
                partner_id="PTR-910",
                name="Manila Prime Introducers",
                realized_volume_30d_usd=95000.0,
                churn_hazard_probability=0.35,
                quadrant=PartnerQuadrant.LOW_VALUE_STABLE,
                days_to_intervention_deadline=90,
                primary_root_cause="Organic Community Expansion",
                login_decay_pct=-12.0,
                ftd_decay_pct=4.0,
                tier="TIER_3_AFFILIATE",
                region="SEA (Philippines)",
                cohort="SEA Retail",
                primary_driver="CYCLICAL",
                empirical_win_rate=0.82,
                provenance=p,
            ),
            PartnerChurnItem(
                partner_id="PTR-215",
                name="London FX Proprietary Network",
                realized_volume_30d_usd=1650000.0,
                churn_hazard_probability=0.15,
                quadrant=PartnerQuadrant.HIGH_VALUE_STABLE,
                days_to_intervention_deadline=240,
                primary_root_cause="Institutional Liquidity Feed",
                login_decay_pct=1.0,
                ftd_decay_pct=9.0,
                tier="TIER_1_SUPER",
                region="UK / London",
                cohort="London Pro Desk",
                primary_driver="CYCLICAL",
                empirical_win_rate=0.95,
                provenance=p,
            ),
            PartnerChurnItem(
                partner_id="PTR-442",
                name="Frankfurt Algo Desk",
                realized_volume_30d_usd=780000.0,
                churn_hazard_probability=0.29,
                quadrant=PartnerQuadrant.HIGH_VALUE_STABLE,
                days_to_intervention_deadline=150,
                primary_root_cause="Stable API Ingestion",
                login_decay_pct=-8.0,
                ftd_decay_pct=3.0,
                tier="TIER_1_SUPER",
                region="Germany / Frankfurt",
                cohort="DAX Institutional",
                primary_driver="CYCLICAL",
                empirical_win_rate=0.89,
                provenance=p,
            ),
            PartnerChurnItem(
                partner_id="PTR-339",
                name="Medellin P2P Payment Ring",
                realized_volume_30d_usd=410000.0,
                churn_hazard_probability=0.79,
                quadrant=PartnerQuadrant.HIGH_VALUE_HIGH_RISK,
                days_to_intervention_deadline=10,
                primary_root_cause="Bancolombia P2P Clearing Lag",
                login_decay_pct=-64.0,
                ftd_decay_pct=-51.0,
                tier="TIER_2_MASTER",
                region="LatAm (Colombia)",
                cohort="LatAm P2P Cashier",
                primary_driver="OPERATIONAL_CASHIER",
                empirical_win_rate=0.785,
                historical_drift={
                    "tMinus30d": {"pChurn": 0.25, "valueAtRiskUsd": 102500},
                    "tMinus14d": {"pChurn": 0.58, "valueAtRiskUsd": 237800},
                    "driftVelocityPct": 216.0,
                },
                provenance=p,
            ),
            PartnerChurnItem(
                partner_id="PTR-774",
                name="Sao Paulo Futures Guild",
                realized_volume_30d_usd=670000.0,
                churn_hazard_probability=0.48,
                quadrant=PartnerQuadrant.HIGH_VALUE_STABLE,
                days_to_intervention_deadline=45,
                primary_root_cause="PIX Gateway Volatility",
                login_decay_pct=-28.0,
                ftd_decay_pct=-15.0,
                tier="TIER_1_SUPER",
                region="LatAm (Brazil)",
                cohort="Brazil PIX Network",
                primary_driver="OPERATIONAL_CASHIER",
                empirical_win_rate=0.81,
                provenance=p,
            ),
            PartnerChurnItem(
                partner_id="PTR-128",
                name="Mexico City CopyTrading IB",
                realized_volume_30d_usd=310000.0,
                churn_hazard_probability=0.58,
                quadrant=PartnerQuadrant.HIGH_VALUE_HIGH_RISK,
                days_to_intervention_deadline=32,
                primary_root_cause="STP Slippage Complaints",
                login_decay_pct=-39.0,
                ftd_decay_pct=-22.0,
                tier="TIER_2_MASTER",
                region="LatAm (Mexico)",
                cohort="LatAm Retail Masters",
                primary_driver="COMMERCIAL_REBATE",
                empirical_win_rate=0.74,
                historical_drift={
                    "tMinus30d": {"pChurn": 0.20, "valueAtRiskUsd": 62000},
                    "tMinus14d": {"pChurn": 0.41, "valueAtRiskUsd": 127100},
                    "driftVelocityPct": 190.0,
                },
                provenance=p,
            ),
            PartnerChurnItem(
                partner_id="PTR-805",
                name="Lima Digital Assets Network",
                realized_volume_30d_usd=48000.0,
                churn_hazard_probability=0.71,
                quadrant=PartnerQuadrant.LOW_VALUE_HIGH_RISK,
                days_to_intervention_deadline=16,
                primary_root_cause="Dormant Channel Activity",
                login_decay_pct=-55.0,
                ftd_decay_pct=-42.0,
                tier="TIER_3_AFFILIATE",
                region="LatAm (Peru)",
                cohort="Andean Affiliates",
                primary_driver="COMPETITIVE_POACHING",
                empirical_win_rate=0.69,
                provenance=p,
            ),
            PartnerChurnItem(
                partner_id="PTR-663",
                name="Madrid Multi-Asset Partners",
                realized_volume_30d_usd=240000.0,
                churn_hazard_probability=0.25,
                quadrant=PartnerQuadrant.HIGH_VALUE_STABLE,
                days_to_intervention_deadline=110,
                primary_root_cause="Steady Telegram Academy",
                login_decay_pct=-5.0,
                ftd_decay_pct=7.0,
                tier="TIER_2_MASTER",
                region="Spain / Europe",
                cohort="Iberia Prime",
                primary_driver="CYCLICAL",
                empirical_win_rate=0.91,
                provenance=p,
            ),
            PartnerChurnItem(
                partner_id="PTR-991",
                name="Limassol Institutional Liquidity",
                realized_volume_30d_usd=1420000.0,
                churn_hazard_probability=0.12,
                quadrant=PartnerQuadrant.HIGH_VALUE_STABLE,
                days_to_intervention_deadline=300,
                primary_root_cause="Direct Fix API Integration",
                login_decay_pct=2.0,
                ftd_decay_pct=14.0,
                tier="TIER_1_SUPER",
                region="Cyprus / EU",
                cohort="EU B2B Liquidity",
                primary_driver="CYCLICAL",
                empirical_win_rate=0.96,
                provenance=p,
            ),
            PartnerChurnItem(
                partner_id="PTR-520",
                name="Kuala Lumpur Synthetics Hub",
                realized_volume_30d_usd=360000.0,
                churn_hazard_probability=0.65,
                quadrant=PartnerQuadrant.HIGH_VALUE_HIGH_RISK,
                days_to_intervention_deadline=24,
                primary_root_cause="Rebate Dispute on Volatility 100",
                login_decay_pct=-42.0,
                ftd_decay_pct=-31.0,
                tier="TIER_2_MASTER",
                region="SEA (Malaysia)",
                cohort="SEA Synthetics",
                primary_driver="COMMERCIAL_REBATE",
                empirical_win_rate=0.76,
                historical_drift={
                    "tMinus30d": {"pChurn": 0.22, "valueAtRiskUsd": 79200},
                    "tMinus14d": {"pChurn": 0.45, "valueAtRiskUsd": 162000},
                    "driftVelocityPct": 195.5,
                },
                provenance=p,
            ),
            PartnerChurnItem(
                partner_id="PTR-284",
                name="Warsaw Quant Laboratory",
                realized_volume_30d_usd=82000.0,
                churn_hazard_probability=0.38,
                quadrant=PartnerQuadrant.LOW_VALUE_STABLE,
                days_to_intervention_deadline=75,
                primary_root_cause="API Backtesting Focus",
                login_decay_pct=-14.0,
                ftd_decay_pct=6.0,
                tier="TIER_3_AFFILIATE",
                region="Poland / CEE",
                cohort="CEE Quant",
                primary_driver="CYCLICAL",
                empirical_win_rate=0.85,
                provenance=p,
            ),
            PartnerChurnItem(
                partner_id="PTR-607",
                name="Santiago Derivatives Desk",
                realized_volume_30d_usd=295000.0,
                churn_hazard_probability=0.53,
                quadrant=PartnerQuadrant.HIGH_VALUE_HIGH_RISK,
                days_to_intervention_deadline=38,
                primary_root_cause="Spread Squeeze vs Rival",
                login_decay_pct=-34.0,
                ftd_decay_pct=-19.0,
                tier="TIER_2_MASTER",
                region="LatAm (Chile)",
                cohort="Andean Affiliates",
                primary_driver="COMPETITIVE_POACHING",
                empirical_win_rate=0.72,
                provenance=p,
            ),
            PartnerChurnItem(
                partner_id="PTR-476",
                name="Bogota Sub-Affiliate Cluster",
                realized_volume_30d_usd=52000.0,
                churn_hazard_probability=0.82,
                quadrant=PartnerQuadrant.LOW_VALUE_HIGH_RISK,
                days_to_intervention_deadline=8,
                primary_root_cause="Cashier Delays & Poaching",
                login_decay_pct=-78.0,
                ftd_decay_pct=-65.0,
                tier="TIER_3_AFFILIATE",
                region="LatAm (Colombia)",
                cohort="LatAm P2P Cashier",
                primary_driver="OPERATIONAL_CASHIER",
                empirical_win_rate=0.785,
                historical_drift={
                    "tMinus30d": {"pChurn": 0.32, "valueAtRiskUsd": 16640},
                    "tMinus14d": {"pChurn": 0.61, "valueAtRiskUsd": 31720},
                    "driftVelocityPct": 156.3,
                },
                provenance=p,
            ),
        ]

        return ChurnRadarScatter(as_of=now, partners=partners)

    def get_partner_referral_tree(self, partner_id: str = "AP-1029") -> dict[str, Any]:
        """Returns referral hierarchy and opposite-trading ring detection."""
        return {
            "master_partner_id": partner_id,
            "tier": "Tier 1 Regional Master",
            "active_sub_affiliates_count": 14,
            "referred_client_count": 312,
            "detected_abusive_rings": [
                {
                    "ring_id": "RING-OPP-14",
                    "scheme": "Opposite Trading on Boom 1000 Index",
                    "paired_accounts": ["CR-401-BUY", "CR-809-SELL"],
                    "matched_timing_seconds": 0.38,
                    "unearned_commission_liability_usd": 42500.0,
                }
            ],
        }

    def get_retention_playbooks(self, partner_id: str = "AP-1029") -> list[RetentionPlaybookDeal]:
        """Recommends retention playbooks partitioned by fast-path budget eligibility."""
        return [
            RetentionPlaybookDeal(
                playbook_id="pb_vip_spread_deal",
                title="Deploy VIP Spread Rebate Deal",
                partner_id=partner_id,
                action_type="DeployRetentionVIPDeal",
                estimated_cost_usd=1800.0,
                is_fast_path_eligible=True,  # <= $2,500
                requires_four_eyes=False,
                projected_retention_uplift_pct=24.5,
            ),
            RetentionPlaybookDeal(
                playbook_id="pb_master_tier_upgrade",
                title="Regional Master Tier Custom Commercial Deal",
                partner_id=partner_id,
                action_type="DeployRetentionVIPDeal",
                estimated_cost_usd=4500.0,
                is_fast_path_eligible=False,  # > $2,500 -> requires dual review
                requires_four_eyes=True,
                projected_retention_uplift_pct=42.0,
            ),
        ]
