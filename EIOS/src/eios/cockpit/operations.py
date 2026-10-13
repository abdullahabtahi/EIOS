"""Data Platform & Operations Board Service: Data Quality, SLA Monitors, Lineage, and Identity Conflicts.

Strict institutional light mode COP invariants and Principle IV governed data products.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from eios.ontology.metrics.registry import MetricRegistry


class DataProductHealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    BREACHED = "BREACHED"


class DataProductSLAStatus(BaseModel):
    """Operational health record displayed on the Data Platform & Operations Board."""

    product_name: str = Field(
        ..., description="e.g. 'transactions_aml', 'client_360', 'partner_aggregates'"
    )
    contract_schema_version: str = Field(..., description="Schema contract version, e.g. 'v1.2.0'")
    row_count: int = Field(..., ge=0, description="Total row count ingested")
    null_check_pass_rate: float = Field(..., ge=0.0, le=1.0, description="DQ null validation score")
    last_ingestion_timestamp: datetime = Field(..., description="Latest record timestamp")
    freshness_sla_seconds: int = Field(
        ..., ge=0, description="Configured freshness SLA window in seconds"
    )
    status: DataProductHealthStatus = Field(..., description="Current operational health status")
    is_degraded: bool = Field(
        ..., description="True if contract breach or freshness delay is active"
    )

    def to_contract_dict(self) -> dict[str, Any]:
        """Serialize according to contracts/data-product-sla-status.schema.json."""
        return {
            "product_name": self.product_name,
            "contract_schema_version": self.contract_schema_version,
            "row_count": self.row_count,
            "null_check_pass_rate": round(self.null_check_pass_rate, 4),
            "last_ingestion_timestamp": self.last_ingestion_timestamp.isoformat(),
            "freshness_sla_seconds": self.freshness_sla_seconds,
            "status": self.status.value,
            "is_degraded": self.is_degraded,
        }


class DataPlatformOperationsService:
    """Service providing real-time data quality monitoring, freshness SLAs, and semantic metric lineage."""

    def __init__(self, metric_registry: MetricRegistry | None = None) -> None:
        self.metric_registry = metric_registry
        now = datetime.now(UTC)

        # Baseline active data products
        self._products: dict[str, DataProductSLAStatus] = {
            "client_transactions": DataProductSLAStatus(
                product_name="client_transactions",
                contract_schema_version="v2.1.0",
                row_count=1854200,
                null_check_pass_rate=0.9998,
                last_ingestion_timestamp=now - timedelta(seconds=90),
                freshness_sla_seconds=300,  # 5 min SLA
                status=DataProductHealthStatus.HEALTHY,
                is_degraded=False,
            ),
            "partner_aggregates": DataProductSLAStatus(
                product_name="partner_aggregates",
                contract_schema_version="v1.4.0",
                row_count=342100,
                null_check_pass_rate=0.9992,
                last_ingestion_timestamp=now - timedelta(seconds=1200),
                freshness_sla_seconds=3600,  # 1 hour SLA
                status=DataProductHealthStatus.HEALTHY,
                is_degraded=False,
            ),
            "transactions_aml": DataProductSLAStatus(
                product_name="transactions_aml",
                contract_schema_version="v3.0.1",
                row_count=9821000,
                null_check_pass_rate=0.9999,
                last_ingestion_timestamp=now - timedelta(seconds=60),
                freshness_sla_seconds=180,  # 3 min SLA
                status=DataProductHealthStatus.HEALTHY,
                is_degraded=False,
            ),
            "identity_clusters": DataProductSLAStatus(
                product_name="identity_clusters",
                contract_schema_version="v1.1.0",
                row_count=521000,
                null_check_pass_rate=0.9985,
                last_ingestion_timestamp=now - timedelta(seconds=450),
                freshness_sla_seconds=1800,  # 30 min SLA
                status=DataProductHealthStatus.HEALTHY,
                is_degraded=False,
            ),
        }

        # Baseline identity cluster conflicts
        self._identity_conflicts: list[dict[str, Any]] = [
            {
                "conflict_id": "conf_fp_8401",
                "entity_a": "client_usr_84920",
                "entity_b": "client_usr_99214",
                "conflict_type": "DEVICE_FINGERPRINT_COLLISION",
                "device_fingerprint": "fp_mac_hash_77a9b02",
                "partner_a": "AP-1029",
                "partner_b": "AP-4882",
                "confidence_score": 0.94,
                "status": "UNRESOLVED",
                "resolution_options": ["MERGE_PSEUDONYMIZED", "MANUAL_SPLIT", "REJECT_LINK"],
            },
            {
                "conflict_id": "conf_alias_3310",
                "entity_a": "client_usr_11029",
                "entity_b": "client_usr_11030",
                "conflict_type": "IP_SUBNET_GEO_ANOMALY",
                "device_fingerprint": "fp_subnet_c_192_88",
                "partner_a": "AP-2041",
                "partner_b": "AP-2041",
                "confidence_score": 0.88,
                "status": "UNRESOLVED",
                "resolution_options": ["MERGE_PSEUDONYMIZED", "MANUAL_SPLIT", "REJECT_LINK"],
            },
        ]

    def evaluate_product_health(
        self, product: DataProductSLAStatus, as_of: datetime | None = None
    ) -> DataProductSLAStatus:
        """Evaluates freshness and null rates against configured SLA thresholds."""
        ref_time = as_of or datetime.now(UTC)
        elapsed = (ref_time - product.last_ingestion_timestamp).total_seconds()

        # Thresholds: > 2x SLA => BREACHED; > 1x SLA or null rate < 0.995 => DEGRADED
        if elapsed > 2 * product.freshness_sla_seconds:
            status = DataProductHealthStatus.BREACHED
            is_degraded = True
        elif elapsed > product.freshness_sla_seconds or product.null_check_pass_rate < 0.995:
            status = DataProductHealthStatus.DEGRADED
            is_degraded = True
        else:
            status = DataProductHealthStatus.HEALTHY
            is_degraded = False

        return DataProductSLAStatus(
            product_name=product.product_name,
            contract_schema_version=product.contract_schema_version,
            row_count=product.row_count,
            null_check_pass_rate=product.null_check_pass_rate,
            last_ingestion_timestamp=product.last_ingestion_timestamp,
            freshness_sla_seconds=product.freshness_sla_seconds,
            status=status,
            is_degraded=is_degraded,
        )

    def get_data_products(self, as_of: datetime | None = None) -> list[DataProductSLAStatus]:
        """Returns all registered data products with evaluated operational health statuses."""
        return [self.evaluate_product_health(p, as_of=as_of) for p in self._products.values()]

    def simulate_sla_delay(self, product_name: str, delay_seconds: int) -> None:
        """Simulate an ingestion lag / pipeline delay for testing."""
        if product_name in self._products:
            prod = self._products[product_name]
            now = datetime.now(UTC)
            self._products[product_name] = DataProductSLAStatus(
                product_name=prod.product_name,
                contract_schema_version=prod.contract_schema_version,
                row_count=prod.row_count,
                null_check_pass_rate=prod.null_check_pass_rate,
                last_ingestion_timestamp=now - timedelta(seconds=delay_seconds),
                freshness_sla_seconds=prod.freshness_sla_seconds,
                status=prod.status,
                is_degraded=prod.is_degraded,
            )

    def get_contract_breach_alerts(self, as_of: datetime | None = None) -> list[dict[str, Any]]:
        """Returns real-time contract breach and SLA delay alerts."""
        alerts: list[dict[str, Any]] = []
        for p in self.get_data_products(as_of=as_of):
            if p.status == DataProductHealthStatus.BREACHED:
                alerts.append(
                    {
                        "alert_id": f"alt_sla_breach_{p.product_name}",
                        "severity": "CRITICAL",
                        "product_name": p.product_name,
                        "type": "SLA_BREACH",
                        "message": f"Ingestion lag exceeded 2x SLA threshold ({p.freshness_sla_seconds}s). Downstream synthesis halted.",
                        "detected_at": datetime.now(UTC).isoformat(),
                    }
                )
            elif p.status == DataProductHealthStatus.DEGRADED:
                alerts.append(
                    {
                        "alert_id": f"alt_sla_degraded_{p.product_name}",
                        "severity": "WARNING",
                        "product_name": p.product_name,
                        "type": "SLA_DEGRADED",
                        "message": f"Product is lagging SLA threshold ({p.freshness_sla_seconds}s) or null-check rate dropped.",
                        "detected_at": datetime.now(UTC).isoformat(),
                    }
                )
        return alerts

    def get_identity_cluster_conflicts(self) -> list[dict[str, Any]]:
        """Returns unresolved identity cluster conflicts across cross-account entity resolution."""
        return list(self._identity_conflicts)

    def resolve_identity_conflict(self, conflict_id: str, action: str) -> dict[str, Any]:
        """Execute conflict resolution (MERGE_PSEUDONYMIZED, MANUAL_SPLIT, REJECT_LINK)."""
        valid_actions = {"MERGE_PSEUDONYMIZED", "MANUAL_SPLIT", "REJECT_LINK"}
        if action not in valid_actions:
            raise ValueError(
                f"Invalid resolution action: '{action}'. Must be one of {valid_actions}"
            )

        for conf in self._identity_conflicts:
            if conf["conflict_id"] == conflict_id:
                conf["status"] = "RESOLVED"
                conf["resolution_action"] = action
                conf["resolved_at"] = datetime.now(UTC).isoformat()
                return conf

        raise KeyError(f"Identity conflict '{conflict_id}' not found.")

    def get_metric_lineage(self, metric_id: str) -> dict[str, Any]:
        """Builds an end-to-end data lineage DAG topology for the specified governed metric."""
        # Find metric in registry if available
        metric_def = None
        if self.metric_registry:
            try:
                metric_def = self.metric_registry.get(metric_id)
            except Exception:
                metric_def = None

        source_products = (
            metric_def.source_products
            if metric_def
            else ["client_transactions", "partner_aggregates"]
        )
        formula = metric_def.formula if metric_def else "SUM(net_deposit_volume_usd)"

        nodes = [
            {
                "id": "source_kafka_stream",
                "type": "INGESTION_SOURCE",
                "label": "Kafka Trade Events",
                "system": "Confluent/Kafka",
            },
            {
                "id": "source_bigquery_lakehouse",
                "type": "DATA_LAKE",
                "label": "BigQuery Lakehouse",
                "system": "GCP BigQuery",
            },
            {
                "id": "dbt_stg_trades",
                "type": "TRANSFORMATION",
                "label": "dbt_stg_trades",
                "system": "dbt Cloud",
            },
            {
                "id": "dbt_fct_metrics",
                "type": "TRANSFORMATION",
                "label": "dbt_fct_metrics",
                "system": "dbt Cloud",
            },
        ]

        # Add data product nodes
        for sp in source_products:
            nodes.append(
                {"id": f"dp_{sp}", "type": "DATA_PRODUCT", "label": sp, "system": "FEIOS HotState"}
            )

        # Add metric node
        nodes.append(
            {
                "id": f"metric_{metric_id}",
                "type": "GOVERNED_METRIC",
                "label": metric_id,
                "formula": formula,
                "system": "FEIOS MetricEngine",
            }
        )

        # Add consumers
        nodes.extend(
            [
                {
                    "id": "consumer_omcp",
                    "type": "AGENT_TOOL",
                    "label": "OMCP Tool Server",
                    "system": "OMCP",
                },
                {
                    "id": "consumer_cockpit",
                    "type": "COCKPIT_WORKSTATION",
                    "label": "Executive Cockpit",
                    "system": "FEIOS UI",
                },
            ]
        )

        edges = [
            {"from": "source_kafka_stream", "to": "dbt_stg_trades"},
            {"from": "source_bigquery_lakehouse", "to": "dbt_stg_trades"},
            {"from": "dbt_stg_trades", "to": "dbt_fct_metrics"},
        ]

        for sp in source_products:
            edges.append({"from": "dbt_fct_metrics", "to": f"dp_{sp}"})
            edges.append({"from": f"dp_{sp}", "to": f"metric_{metric_id}"})

        edges.append({"from": f"metric_{metric_id}", "to": "consumer_omcp"})
        edges.append({"from": "consumer_omcp", "to": "consumer_cockpit"})

        return {
            "metric_id": metric_id,
            "formula": formula,
            "nodes": nodes,
            "edges": edges,
            "lineage_depth": 5,
        }

    def get_board_summary(self, as_of: datetime | None = None) -> dict[str, Any]:
        """Provides an aggregated summary for the Data Platform & Operations Board."""
        products = self.get_data_products(as_of=as_of)
        alerts = self.get_contract_breach_alerts(as_of=as_of)
        conflicts = self.get_identity_cluster_conflicts()

        total = len(products)
        healthy = sum(1 for p in products if p.status == DataProductHealthStatus.HEALTHY)
        degraded = sum(1 for p in products if p.status == DataProductHealthStatus.DEGRADED)
        breached = sum(1 for p in products if p.status == DataProductHealthStatus.BREACHED)

        compliance_rate = (healthy / total) if total > 0 else 1.0

        return {
            "total_products": total,
            "healthy_products": healthy,
            "degraded_products": degraded,
            "breached_products": breached,
            "sla_compliance_rate_pct": round(compliance_rate * 100.0, 1),
            "active_alerts_count": len(alerts),
            "unresolved_conflicts_count": sum(1 for c in conflicts if c["status"] == "UNRESOLVED"),
            "products": [p.to_contract_dict() for p in products],
            "alerts": alerts,
        }
