"""Operations capabilities (spec 023): the data platform and reliability boards, without calling silence healthy."""

from eios.common.validation import StrictModel
from eios.ingestion.circuit_breaker import IngestionCircuitBreaker
from eios.ontology.omcp.port.common import envelope
from eios.ontology.omcp.port.contracts import PortError, ToolErrorCode, ToolResult
from eios.ontology.omcp.port.principal import Principal, Workstation
from eios.ontology.omcp.port.readmodels import ReadModels
from eios.ontology.omcp.port.registry import ToolSpec

OPS = (Workstation.DATA_OPERATIONS,)


class NoArgs(StrictModel):
    pass


# --- get_dq_board ----------------------------------------------------------------------------------------


class Product(StrictModel):
    product_name: str
    contract_schema_version: str
    row_count: int
    null_check_pass_rate: float
    last_ingestion_timestamp: str
    freshness_sla_seconds: int
    status: str
    freshness_judged: bool = True  # False where the product is a batch snapshot, so the newest event's age is not a delay
    newest_event_age_seconds: float | None = None
    contract_breach_rate: float | None = None
    quarantined_records: int | None = None


class BoardAlert(StrictModel):
    alert_id: str
    severity: str
    product_name: str
    type: str
    message: str


class DqBoard(ToolResult):
    total_products: int
    healthy_products: int
    degraded_products: int
    breached_products: int
    sla_compliance_rate_pct: float
    contract_breach_budget: (
        float  # the breach rate above which a product is breached; alerts quote it in a sentence
    )
    active_alerts_count: int
    unresolved_conflicts_count: (
        int | None
    )  # None: identity resolution is not computed on this plane
    products: list[Product]
    alerts: list[BoardAlert]


def get_dq_board(ctx: ReadModels, _who: Principal, _args: NoArgs) -> DqBoard:
    b = ctx.operations.get_board_summary()
    return DqBoard(
        **envelope(
            ctx,
            "ops.dq_board",
            None,
            "cockpit.operations.get_board_summary",
            {
                "total_products": "products",
                "healthy_products": "products",
                "degraded_products": "products",
                "breached_products": "products",
                "sla_compliance_rate_pct": "percent",
                "contract_breach_budget": "ratio",
                "active_alerts_count": "alerts",
                "unresolved_conflicts_count": "conflicts",
                "products[].row_count": "rows",
                "products[].null_check_pass_rate": "ratio",
                "products[].freshness_sla_seconds": "seconds",
                "products[].newest_event_age_seconds": "seconds",
                "products[].contract_breach_rate": "ratio",
                "products[].quarantined_records": "records",
            },
            origin=ctx.operations_origin,
        ),
        total_products=b["total_products"],
        healthy_products=b["healthy_products"],
        degraded_products=b["degraded_products"],
        breached_products=b["breached_products"],
        sla_compliance_rate_pct=b["sla_compliance_rate_pct"],
        contract_breach_budget=IngestionCircuitBreaker().breach_rate_threshold,
        active_alerts_count=b["active_alerts_count"],
        unresolved_conflicts_count=b["unresolved_conflicts_count"],
        products=[
            Product(**{k: p[k] for k in Product.model_fields if k in p}) for p in b["products"]
        ],
        alerts=[BoardAlert(**{k: a[k] for k in BoardAlert.model_fields}) for a in b["alerts"]],
    )


# --- get_reliability -------------------------------------------------------------------------------------


class Objective(StrictModel):
    sli_name: str
    total_events: int
    compliance_percentage: (
        float | None
    )  # None when nothing was observed: no events is not compliance
    target_percentage: float
    budget_remaining_pct: float | None
    status: str
    is_frozen: bool


class Reliability(ToolResult):
    overall_health: str
    objectives: list[Objective]


def get_reliability(ctx: ReadModels, _who: Principal, _args: NoArgs) -> Reliability:
    slos = ctx.slo_engine.evaluate_all_slos()
    if all(s.total_events == 0 for s in slos):
        health = "NO_DATA"  # a target met by zero events is not health
    elif any(s.is_frozen for s in slos):
        health = "FEATURE_FREEZE"
    elif any(s.status.value == "WARNING" for s in slos):
        health = "WARNING"
    else:
        health = "HEALTHY"
    return Reliability(
        **envelope(
            ctx,
            "ops.reliability",
            None,
            "observability.slo_engine.evaluate_all_slos",
            {
                "objectives[].total_events": "events",
                "objectives[].compliance_percentage": "percent",
                "objectives[].target_percentage": "percent",
                "objectives[].budget_remaining_pct": "percent",
            },
            origin=ctx.operations_origin,
        ),
        overall_health=health,
        objectives=[
            Objective(
                sli_name=s.sli_name.value,
                total_events=s.total_events,
                compliance_percentage=None if s.total_events == 0 else s.compliance_percentage,
                target_percentage=s.target_percentage,
                budget_remaining_pct=None if s.total_events == 0 else s.budget_remaining_pct,
                status="NO_DATA" if s.total_events == 0 else s.status.value,
                is_frozen=s.is_frozen,
            )
            for s in slos
        ],
    )


# --- get_drill_status ------------------------------------------------------------------------------------


class Runbook(StrictModel):
    runbook_id: str
    title: str
    trigger: str


class RestoreDrill(StrictModel):
    verified: bool
    rows_exported: int
    rows_restored: int
    export_ms: float
    restore_ms: float
    checkpoint_hash: str
    ran_at: str


class DrillStatus(ToolResult):
    scope: str
    registered_runbooks_count: int
    runbooks: list[Runbook]
    restore_drill: RestoreDrill | None = None


def get_drill_status(ctx: ReadModels, _who: Principal, _args: NoArgs) -> DrillStatus:
    catalog = ctx.runbooks.get_runbook_catalog()
    drill = getattr(ctx.operations, "drill", None)
    return DrillStatus(
        **envelope(
            ctx,
            "ops.drill_status",
            None,
            "hardening.runbooks.get_runbook_catalog",
            {
                "registered_runbooks_count": "runbooks",
                "restore_drill.rows_exported": "rows",
                "restore_drill.rows_restored": "rows",
                "restore_drill.export_ms": "ms",
                "restore_drill.restore_ms": "ms",
            },
            origin=ctx.operations_origin,
        ),
        scope=(
            "the warm-start restore drill was run for real; the other runbooks are catalogue only"
            if drill is not None
            else "runbook catalogue only; no drill history is loaded"
        ),
        restore_drill=None
        if drill is None
        else RestoreDrill(
            verified=drill.verified,
            rows_exported=drill.rows_exported,
            rows_restored=drill.rows_restored,
            export_ms=drill.export_ms,
            restore_ms=drill.restore_ms,
            checkpoint_hash=drill.checkpoint_hash,
            ran_at=drill.ran_at.isoformat(),
        ),
        registered_runbooks_count=len(catalog),
        runbooks=[
            Runbook(runbook_id=r["runbook_id"], title=r["title"], trigger=r["trigger"])
            for r in catalog
        ],
    )


# --- get_calibration_status ------------------------------------------------------------------------------


class CalibrationArgs(StrictModel):
    pass


class Calibration(ToolResult):
    basis: str | None = None
    model_id: str
    sample_count: int
    expected_calibration_error: float
    brier_score: float
    is_drift_detected: bool


def get_calibration_status(ctx: ReadModels, _who: Principal, _args: CalibrationArgs) -> Calibration:
    sample = ctx.calibration_sample
    if sample is not None:
        probabilities, labels = list(sample.probabilities), [float(x) for x in sample.labels]
        model_id, basis, source = sample.model_id, sample.basis, "partner engine hazard history"
    else:
        records = ctx.outcomes.query_records()
        if not records:
            raise PortError(
                ToolErrorCode.DATA_UNAVAILABLE,
                "calibration needs recorded decision outcomes and none exist yet",
            )
        probabilities = [r.propensity_score for r in records]
        labels = [
            1.0
            if (r.actual_impact_60d and r.actual_impact_60d > 0) or r.treatment_assigned
            else 0.0
            for r in records
        ]
        model_id, basis, source = "churn-hazard-model-v2", None, "decision outcomes ledger"
    report = ctx.calibration.evaluate_calibration(probabilities, labels, model_id=model_id)
    return Calibration(
        **envelope(
            ctx,
            "ops.calibration",
            None,
            f"flywheel.diagnostics.evaluate_calibration over {source}",
            {
                "sample_count": "decisions",
                "expected_calibration_error": "ratio",
                "brier_score": "score",
            },
            origin=ctx.operations_origin,
        ),
        basis=basis,
        model_id=report.model_id,
        sample_count=report.sample_count,
        expected_calibration_error=report.expected_calibration_error,
        brier_score=report.brier_score,
        is_drift_detected=report.is_drift_detected,
    )


# --- get_red_lines ---------------------------------------------------------------------------------------


class RedLineOut(StrictModel):
    gate_id: str
    name: str
    status: str  # PASS, FAIL, or NOT_MEASURED: a gate nothing measured is never reported as passing
    margin: float | None
    basis: str


class RedLines(ToolResult):
    gates: list[RedLineOut]


def get_red_lines(ctx: ReadModels, _who: Principal, _args: NoArgs) -> RedLines:
    measured = getattr(ctx.operations, "red_lines", None)
    if measured is None:
        raise PortError(ToolErrorCode.DATA_UNAVAILABLE, "no red line is measured on this plane")
    return RedLines(
        **envelope(
            ctx,
            "ops.red_lines",
            None,
            "dataplane.ops_probes.run_probes",
            {"gates[].margin": "margin"},
            origin=ctx.operations_origin,
        ),
        gates=[
            RedLineOut(
                gate_id=g.gate_id, name=g.name, status=g.status, margin=g.margin, basis=g.basis
            )
            for g in measured()
        ],
    )


TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec("get_dq_board", "ops.dq_board", "evidence", OPS, NoArgs, DqBoard, get_dq_board, 300.0),
    ToolSpec(
        "get_reliability",
        "ops.reliability",
        "evidence",
        OPS,
        NoArgs,
        Reliability,
        get_reliability,
        300.0,
    ),
    ToolSpec(
        "get_drill_status",
        "ops.drill_status",
        "evidence",
        OPS,
        NoArgs,
        DrillStatus,
        get_drill_status,
        300.0,
    ),
    ToolSpec(
        "get_calibration_status",
        "ops.calibration",
        "evidence",
        OPS,
        CalibrationArgs,
        Calibration,
        get_calibration_status,
        300.0,
    ),
    ToolSpec(
        "get_red_lines",
        "ops.red_lines",
        "evidence",
        OPS,
        NoArgs,
        RedLines,
        get_red_lines,
        300.0,
    ),
)
