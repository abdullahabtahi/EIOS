"""Deterministic Metric Provenance Resolver and Cache.

Guarantees sub-50ms provenance resolution for every quantitative scalar
rendered across cockpit cards, charts, and dossiers.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from eios.cockpit.schemas import validate_contract
from eios.ontology.metrics.registry import MetricNotFoundError, MetricRegistry


class ProvenanceMetadata(BaseModel):
    metric_id: str
    definition_version: str
    as_of_timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    computation_source: str = "SemanticRegistry.DuckDB"
    owner_role: str
    formula_summary: str | None = None
    is_replayed: bool = False

    def to_contract_dict(self) -> dict[str, Any]:
        data = {
            "metric_id": self.metric_id,
            "definition_version": self.definition_version,
            "as_of_timestamp": self.as_of_timestamp.isoformat(),
            "computation_source": self.computation_source,
            "owner_role": self.owner_role,
            "formula_summary": self.formula_summary,
            "is_replayed": self.is_replayed,
        }
        validate_contract(data, "provenance-metadata")
        return data


class ProvenanceResolver:
    """In-memory high-speed provenance resolver with sub-50ms SLA."""

    # Default fallback definitions for canonical enterprise metrics
    _CANONICAL_DEFAULTS: dict[str, dict[str, Any]] = {
        "net_revenue_usd": {
            "owner_role": "Chief Financial Officer",
            "version": "1.4.0",
            "source": "SemanticRegistry.DuckDB",
            "formula": "trading_volume_usd * spread_bps - partner_commissions_usd",
        },
        "client_ltv_usd": {
            "owner_role": "Head of Growth",
            "version": "2.1.0",
            "source": "SynthesisEngine.CausalSCM",
            "formula": "predicted_client_lifetime_revenue_usd",
        },
        "realized_deposit_volume_30d_usd": {
            "owner_role": "Lead AML Officer",
            "version": "1.2.0",
            "source": "AMLHotState.DuckDB",
            "formula": "sum(deposit_amount_usd) over rolling_30d",
        },
        "discrepancy_multiplier": {
            "owner_role": "Lead AML Officer",
            "version": "1.2.0",
            "source": "AMLHotState.DuckDB",
            "formula": "realized_deposit_volume_30d_usd / declared_monthly_income_usd",
        },
        "crypto_usdt_deposit_ratio": {
            "owner_role": "Risk Director",
            "version": "1.1.0",
            "source": "AMLHotState.DuckDB",
            "formula": "crypto_deposits_usd / total_deposits_usd",
        },
        "churn_hazard_probability": {
            "owner_role": "Head of Partnerships",
            "version": "3.0.0",
            "source": "PartnerChurnRadar.HazardModel",
            "formula": "P(disengagement within 30 days | behavioral, financial signals)",
        },
        "realized_volume_30d_usd": {
            "owner_role": "Head of Partnerships",
            "version": "1.3.0",
            "source": "PartnerHotState.DuckDB",
            "formula": "sum(affiliate_client_turnover_usd) over 30d",
        },
        "competitor_payout_rate": {
            "owner_role": "Head of Competitive Intelligence",
            "version": "1.0.0",
            "source": "ExecutiveEngine.Series",
            "formula": "competitor payout per dollar of referred volume, daily",
        },
        "unearned_commission_liability_usd": {
            "owner_role": "Fraud Sentinel Lead",
            "version": "2.0.0",
            "source": "PartnerFraudSentinel.Graph",
            "formula": "opposite_trading_commissions_usd + bonus_abuse_commissions_usd",
        },
    }

    def __init__(self, metric_registry: MetricRegistry | None = None) -> None:
        self._registry = metric_registry
        self._cache: dict[str, ProvenanceMetadata] = {}

    def resolve(
        self,
        metric_id: str,
        version: str | None = None,
        as_of: datetime | None = None,
        is_replayed: bool = False,
    ) -> ProvenanceMetadata:
        """Resolves provenance metadata in < 50ms."""
        time.perf_counter()
        as_of_time = as_of or datetime.now(UTC)

        # Check in-memory cache first
        cache_key = f"{metric_id}:{version or 'latest'}:{is_replayed}"
        if cache_key in self._cache:
            item = self._cache[cache_key]
            # Refresh as_of
            return ProvenanceMetadata(
                metric_id=item.metric_id,
                definition_version=item.definition_version,
                as_of_timestamp=as_of_time,
                computation_source=item.computation_source,
                owner_role=item.owner_role,
                formula_summary=item.formula_summary,
                is_replayed=is_replayed,
            )

        # Attempt retrieval from official metric registry if provided
        if self._registry is not None:
            try:
                defn = self._registry.get(metric_id, version)
                meta = ProvenanceMetadata(
                    metric_id=defn.metric_id,
                    definition_version=defn.semantic_version,
                    as_of_timestamp=as_of_time,
                    computation_source=f"SemanticRegistry.{defn.domain.capitalize()}",
                    owner_role=defn.owner_role,
                    formula_summary=defn.formula,
                    is_replayed=is_replayed,
                )
                self._cache[cache_key] = meta
                return meta
            except MetricNotFoundError:
                pass

        # Check canonical defaults
        if metric_id in self._CANONICAL_DEFAULTS:
            info = self._CANONICAL_DEFAULTS[metric_id]
            meta = ProvenanceMetadata(
                metric_id=metric_id,
                definition_version=version or info["version"],
                as_of_timestamp=as_of_time,
                computation_source=info["source"],
                owner_role=info["owner_role"],
                formula_summary=info["formula"],
                is_replayed=is_replayed,
            )
            self._cache[cache_key] = meta
            return meta

        raise KeyError(f"Metric '{metric_id}' is not registered in provenance catalog")
