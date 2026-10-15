"""The operations read model over the real ingestion pipeline, the profiled products, the probes and the drill (spec 035).

Same public methods as `DataPlatformOperationsService`, plus what the engine plane can honestly add: the quarantined
records with a real redrive, the measured red lines, the error budgets read from the SLO engine, and the restore drill.
"""

from __future__ import annotations

import base64
import json
from datetime import UTC, datetime
from typing import Any

from eios.cockpit.operations import DataProductHealthStatus, DataProductSLAStatus
from eios.contracts.base import DataProductEnum, DataProductEvent
from eios.dataplane.aml_engine import AmlSnapshot
from eios.dataplane.ops_drill import DrillResult, run_restore_drill
from eios.dataplane.ops_probes import ProbeReport, RedLine, run_probes
from eios.dataplane.ops_products import BREACH_BUDGET, ProductProfile, profile
from eios.dataplane.ops_replay import PRODUCT, TENANT, ReplayOutcome, replay_transactions
from eios.dataplane.partner_service import EnginePartnerService
from eios.foundry.scenarios.executive_world import ExecutiveWorld
from eios.ingestion.dlq import ContractBreachRecord
from eios.observability.slo_catalog import DEFAULT_SLO_CATALOG
from eios.observability.slo_engine import ErrorBudgetHealth
from eios.ontology.omcp.port.readmodels import ReadModels

STATUS_FOR_BUDGET = {
    ErrorBudgetHealth.HEALTHY: "HEALTHY",
    ErrorBudgetHealth.WARNING: "DEGRADED",
    ErrorBudgetHealth.FEATURE_FREEZE: "BREACHED",
}


class RedriveRejectedError(ValueError):
    """The repaired payload still breaks its contract; the record stays quarantined."""

    def __init__(self, dlq_id: str, errors: list[str]) -> None:
        super().__init__(f"{dlq_id} still breaks its contract: {'; '.join(errors)}")
        self.errors = errors


class UnknownRecordError(KeyError):
    pass


class EngineOperationsService:
    def __init__(
        self,
        profiles: list[ProductProfile],
        replay: ReplayOutcome,
        drill: DrillResult,
        as_of: datetime,
    ) -> None:
        self._profiles = profiles
        self._replay = replay
        self._drill = drill
        self.as_of = as_of
        self._records: dict[str, dict[str, Any]] = {
            r.dlq_id: self._record_view(r) for r in replay.dlq
        }
        self._report: ProbeReport | None = None
        self._models: ReadModels | None = None

    @classmethod
    def build(
        cls,
        aml: AmlSnapshot,
        partners: EnginePartnerService,
        executive: ExecutiveWorld,
        as_of: datetime,
    ) -> EngineOperationsService:
        replay = replay_transactions(aml.world, as_of)
        p = partners.snapshot.world
        e = executive.days
        frames = (
            (
                DataProductEnum.TRANSACTIONS_AML,
                aml.world.transactions,
                "timestamp",
                replay,
                frozenset(),
            ),
            (
                DataProductEnum.CLIENT_360,
                aml.world.clients,
                "kyc_approved_at",
                None,
                frozenset(
                    {"kyc_approved_at", "partner_id", "declared_monthly_income_usd"}
                ),  # optional in the contract
            ),
            (DataProductEnum.TRADING_ACTIVITY, aml.world.trades, "timestamp", None, frozenset()),
            (DataProductEnum.PARTNER_360, p.roster, None, None, frozenset()),
            (DataProductEnum.PARTNER_ENGAGEMENT_SIGNALS, p.days, "date", None, frozenset()),
            (DataProductEnum.PARTNER_COMMS, p.messages, "timestamp", None, frozenset()),
            (DataProductEnum.COMMISSION_LEDGER, p.commissions, "paid_at", None, frozenset()),
            (
                DataProductEnum.COMPETITOR_BENCHMARKS,
                e[["date", "competitor_payout_rate"]],
                "date",
                None,
                frozenset(),
            ),
            (
                DataProductEnum.FINANCIAL_PNL,
                e[["date", "net_revenue_usd"]],
                "date",
                None,
                frozenset(),
            ),
        )
        profiles = [profile(prod, f, col, as_of, rep, opt) for prod, f, col, rep, opt in frames]
        return cls(profiles, replay, run_restore_drill(replay.accepted_events), as_of)

    def measure(self, models: ReadModels, aml: AmlSnapshot) -> ProbeReport:
        """Run the probes against the finished read models; their events land in `models.slo_engine`."""
        self._models = models
        self._report = run_probes(models, aml, self._replay)
        return self._report

    # --- data products ------------------------------------------------------------------------------------

    def get_data_products(self, as_of: datetime | None = None) -> list[DataProductSLAStatus]:
        return [
            DataProductSLAStatus(
                product_name=p.product.value,
                contract_schema_version=d["contract_schema_version"],
                row_count=p.rows,
                null_check_pass_rate=p.completeness,
                last_ingestion_timestamp=p.newest_event,
                freshness_sla_seconds=d["freshness_sla_seconds"],
                status=p.status,
                is_degraded=p.status is not DataProductHealthStatus.HEALTHY,
            )
            for p in self._profiles
            for d in (p.to_contract_dict(),)
        ]

    def product_cards(self) -> list[dict[str, Any]]:
        return [p.to_contract_dict() for p in self._profiles]

    def get_contract_breach_alerts(self, as_of: datetime | None = None) -> list[dict[str, Any]]:
        alerts: list[dict[str, Any]] = []
        for p in self._profiles:
            if p.status is DataProductHealthStatus.HEALTHY:
                continue
            rate = f"{p.breach_rate:.3%}" if p.breach_rate is not None else "n/a"
            alerts.append(
                {
                    "alert_id": f"alt_contract_{p.product.value}",
                    "severity": "CRITICAL"
                    if p.status is DataProductHealthStatus.BREACHED
                    else "WARNING",
                    "product_name": p.product.value,
                    "type": "CONTRACT_BREACH",
                    "message": (
                        f"{p.quarantined} records quarantined; breach rate {rate} against a budget of "
                        f"{BREACH_BUDGET:.3%}."
                    ),
                    "detected_at": self.as_of.isoformat(),
                }
            )
        return alerts

    def get_identity_cluster_conflicts(self) -> list[dict[str, Any]]:
        return []  # identity resolution is not computed on this plane

    def get_board_summary(self, as_of: datetime | None = None) -> dict[str, Any]:
        products = self.get_data_products()
        total = len(products)
        count = lambda s: sum(1 for p in products if p.status is s)  # noqa: E731
        healthy = count(DataProductHealthStatus.HEALTHY)
        return {
            "total_products": total,
            "healthy_products": healthy,
            "degraded_products": count(DataProductHealthStatus.DEGRADED),
            "breached_products": count(DataProductHealthStatus.BREACHED),
            "sla_compliance_rate_pct": round(healthy / total * 100.0, 1) if total else 100.0,
            "active_alerts_count": len(self.get_contract_breach_alerts()),
            "unresolved_conflicts_count": None,  # not assessed here, which is not the same as none
            "products": self.product_cards(),
            "alerts": self.get_contract_breach_alerts(),
        }

    # --- quarantine ---------------------------------------------------------------------------------------

    @staticmethod
    def _record_view(r: ContractBreachRecord) -> dict[str, Any]:
        return {
            "dlq_id": r.dlq_id,
            "source_stream": r.source_topic,
            "error_category": r.breach_type.value,
            "error_message": "; ".join(
                f"{f}: {m}" for f, m in zip(r.field_paths, r.error_messages, strict=False)
            ),
            "quarantined_at": r.breach_timestamp.isoformat(),
            "payload": json.loads(base64.b64decode(r.raw_payload_bytes)),
            "redrive_count": 0,
            "status": "QUARANTINED",
        }

    def dlq_records(self) -> list[dict[str, Any]]:
        return [dict(r) for r in self._records.values()]

    def redrive(self, dlq_id: str, repair: dict[str, Any] | None) -> dict[str, Any]:
        """Re-run a quarantined record through the real pipeline after the operator's repair; refuse if it still breaks."""
        record = self._records.get(dlq_id)
        if record is None:
            raise UnknownRecordError(dlq_id)
        payload = {**record["payload"], **(repair or {})}
        pipeline = self._replay.pipeline
        check = pipeline.validator.validate(PRODUCT, payload)
        record["redrive_count"] += 1
        if not check.is_valid:
            raise RedriveRejectedError(
                dlq_id, [f"{e.field_path}: {e.message}" for e in check.errors]
            )
        event = DataProductEvent(
            product_name=PRODUCT,
            tenant_id=TENANT,
            event_timestamp=check.validated_model.timestamp,
            payload=payload,  # type: ignore[union-attr]
        )
        pipeline.process_event(event)
        record["status"] = "REDRIVEN_COMMITTED"
        record["redriven_at"] = datetime.now(UTC).isoformat()
        return dict(record)

    # --- reliability, red lines, drill --------------------------------------------------------------------

    def error_budgets(self) -> list[dict[str, Any]]:
        """One row per indicator from the SLO engine; an indicator nothing probed reads NO_DATA, never healthy."""
        if self._models is None:
            return []
        out = []
        for s in self._models.slo_engine.evaluate_all_slos():
            cfg = DEFAULT_SLO_CATALOG[s.sli_name]
            out.append(
                {
                    "slo_id": s.sli_name.value,
                    "name": cfg.display_name,
                    "consumed_pct": None
                    if s.total_events == 0
                    else round(100.0 - s.budget_remaining_pct, 1),
                    "status": "NO_DATA" if s.total_events == 0 else STATUS_FOR_BUDGET[s.status],
                    "total_events": s.total_events,
                }
            )
        return out

    def red_lines(self) -> list[RedLine]:
        return list(self._report.red_lines) if self._report else []

    @property
    def drill(self) -> DrillResult:
        return self._drill

    @property
    def replay(self) -> ReplayOutcome:
        return self._replay

    def probe_events(self) -> dict[str, int]:
        return dict(self._report.events) if self._report else {}
