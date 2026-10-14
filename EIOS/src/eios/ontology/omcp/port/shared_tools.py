"""Capabilities every workstation or several workstations share: metrics, identity, causal labels, derived figures."""

from enum import StrEnum
from typing import Any

from pydantic import Field

from eios.common.validation import StrictModel
from eios.ontology.config import SecurityMarking
from eios.ontology.omcp.port.common import envelope, require_clearance
from eios.ontology.omcp.port.contracts import (
    DataOrigin,
    PortError,
    ToolErrorCode,
    ToolResult,
    weakest,
)
from eios.ontology.omcp.port.entities import EntityKind
from eios.ontology.omcp.port.principal import Principal, Workstation
from eios.ontology.omcp.port.readmodels import ReadModels
from eios.ontology.omcp.port.registry import ToolSpec

W = Workstation
ALL = tuple(Workstation)
PRIVATE_AML = (SecurityMarking.PII, SecurityMarking.SENSITIVE_COMPLIANCE)
COMMERCIAL = (SecurityMarking.PARTNER_COMMERCIAL,)
VERIFIED, CORRELATION = "VERIFIED_CAUSAL", "CORRELATION_ONLY"
MIN_CONFIDENCE, MIN_PLACEBO_P = 0.80, 0.05  # constitution RL-3


class MetricId(StrEnum):
    NET_REVENUE = "net_revenue_usd"
    PARTNER_VOLUME = "realized_volume_30d_usd"
    CHURN_HAZARD = "churn_hazard_probability"
    DEPOSIT_VOLUME = "realized_deposit_volume_30d_usd"
    DISCREPANCY = "discrepancy_multiplier"


# metric -> (entity kind it is about or None for the portfolio, unit, markings of the data class)
_RULES: dict[MetricId, tuple[EntityKind | None, str, tuple[SecurityMarking, ...]]] = {
    MetricId.NET_REVENUE: (None, "USD", ()),
    MetricId.PARTNER_VOLUME: (EntityKind.PARTNER, "USD", COMMERCIAL),
    MetricId.CHURN_HAZARD: (EntityKind.PARTNER, "ratio", COMMERCIAL),
    MetricId.DEPOSIT_VOLUME: (EntityKind.ACCOUNT, "USD", PRIVATE_AML),
    MetricId.DISCREPANCY: (EntityKind.ACCOUNT, "multiplier", PRIVATE_AML),
}


def causal_label(confidence: float, placebo_p_value: float) -> tuple[str, str]:
    """RL-3: causal only if the placebo refuter p > 0.05 and confidence >= 0.80, whatever the stored label says."""
    if placebo_p_value > MIN_PLACEBO_P and confidence >= MIN_CONFIDENCE:
        return VERIFIED, "placebo refuter passed with sufficient confidence"
    reasons = []
    if placebo_p_value <= MIN_PLACEBO_P:
        reasons.append("placebo p-value is not above the required threshold")
    if confidence < MIN_CONFIDENCE:
        reasons.append("confidence is below the required level")
    return CORRELATION, "; ".join(reasons)


# --- get_metric ------------------------------------------------------------------------------------------


class MetricArgs(StrictModel):
    metric_id: MetricId
    entity_id: str | None = None


class MetricValue(ToolResult):
    metric_id: str
    value: float
    definition_version: str
    owner_role: str
    formula_summary: str | None

    def fact_scope(self) -> str:
        return f"{self.metric_id}@{self.entity_id}" if self.entity_id else self.metric_id


def get_metric(ctx: ReadModels, who: Principal, args: MetricArgs) -> MetricValue:
    kind, unit, markings = _RULES[args.metric_id]
    require_clearance(who, markings)
    entity: str | None = None
    if kind is None:
        if args.entity_id:
            raise PortError(
                ToolErrorCode.INVALID_ARGUMENTS, f"{args.metric_id.value} is a portfolio metric"
            )
        financial = next(
            h
            for h in ctx.executive.get_morning_briefing().horizons
            if h.horizon_name == "Financial"
        )
        value, source = financial.observed_value, "cockpit.executive.get_morning_briefing"
    else:
        if not args.entity_id:
            raise PortError(
                ToolErrorCode.INVALID_ARGUMENTS, f"{args.metric_id.value} needs an entity_id"
            )
        entity = ctx.directory.resolve(args.entity_id, kind).entity_id
        value, source = _entity_value(ctx, args.metric_id, entity)
    prov = ctx.executive.provenance_resolver.resolve(args.metric_id.value, as_of=ctx.clock())
    return MetricValue(
        **envelope(
            ctx,
            "metric.get",
            entity,
            source,
            {"value": unit},
            markings,
            origin=_metric_origin(ctx, args),
        ),
        metric_id=args.metric_id.value,
        value=value,
        definition_version=prov.definition_version,
        owner_role=prov.owner_role,
        formula_summary=prov.formula_summary,
    )


def _metric_origin(ctx: ReadModels, args: MetricArgs) -> DataOrigin:
    """AML-derived metrics take the AML plane's origin; everything else is fixture until its plane lands."""
    aml_metrics = (MetricId.DISCREPANCY, MetricId.DEPOSIT_VOLUME)
    return (
        ctx.aml_origin if args.metric_id in aml_metrics and args.entity_id else DataOrigin.FIXTURE
    )


def _entity_value(ctx: ReadModels, metric: MetricId, entity: str) -> tuple[float, str]:
    if metric in (MetricId.PARTNER_VOLUME, MetricId.CHURN_HAZARD):
        item = next(
            p for p in ctx.partner.get_churn_radar_scatter().partners if p.partner_id == entity
        )
        field = (
            "realized_volume_30d_usd"
            if metric is MetricId.PARTNER_VOLUME
            else "churn_hazard_probability"
        )
        return float(getattr(item, field)), "cockpit.partner.get_churn_radar_scatter"
    if not ctx.aml.supports_detail(entity):
        raise PortError(
            ToolErrorCode.DATA_UNAVAILABLE, f"{metric.value} is not available for {entity} yet"
        )
    d = ctx.aml.get_entity_dossier(entity).discrepancy
    value = (
        d.discrepancy_multiplier
        if metric is MetricId.DISCREPANCY
        else d.realized_deposit_volume_30d_usd
    )
    return value, "cockpit.aml.get_entity_dossier"


# --- resolve_entity --------------------------------------------------------------------------------------


class ResolveArgs(StrictModel):
    entity_id: str


class ResolvedEntity(ToolResult):
    kind: str


def resolve_entity(ctx: ReadModels, _who: Principal, args: ResolveArgs) -> ResolvedEntity:
    found = ctx.directory.resolve(args.entity_id)
    return ResolvedEntity(
        **envelope(ctx, "entity.resolve", found.entity_id, "port.entities", {}),
        kind=found.kind.value,
    )


# --- get_causal_evidence ---------------------------------------------------------------------------------


class CausalArgs(StrictModel):
    source_node_id: str | None = Field(default=None, max_length=64)
    target_node_id: str | None = Field(default=None, max_length=64)


class CausalEdgeOut(StrictModel):
    source_node_id: str
    target_node_id: str
    weight: float
    confidence: float
    placebo_p_value: float
    causal_label: str
    reason: str


class CausalEvidence(ToolResult):
    dag_version: str
    required_placebo_p_above: float
    required_confidence_at_least: float
    edges: list[CausalEdgeOut]


def get_causal_evidence(ctx: ReadModels, _who: Principal, args: CausalArgs) -> CausalEvidence:
    dag = ctx.executive.get_causal_dag()
    nodes = {n.node_id for n in dag.nodes}
    for wanted in (args.source_node_id, args.target_node_id):
        if wanted is not None and wanted not in nodes:
            raise PortError(ToolErrorCode.NOT_FOUND, f"no causal node '{wanted}'")
    edges = []
    for e in dag.edges:
        if args.source_node_id not in (None, e.source_node_id) or args.target_node_id not in (
            None,
            e.target_node_id,
        ):
            continue
        label, reason = causal_label(e.refuter.confidence, e.refuter.placebo_p_value)
        edges.append(
            CausalEdgeOut(
                source_node_id=e.source_node_id,
                target_node_id=e.target_node_id,
                weight=e.weight,
                confidence=e.refuter.confidence,
                placebo_p_value=e.refuter.placebo_p_value,
                causal_label=label,
                reason=reason,
            )
        )
    return CausalEvidence(
        **envelope(
            ctx,
            "causal.evidence",
            None,
            "cockpit.executive.get_causal_dag",
            {
                "edges[].weight": "model weight",
                "edges[].confidence": "ratio",
                "edges[].placebo_p_value": "ratio",
                "required_placebo_p_above": "ratio",
                "required_confidence_at_least": "ratio",
            },
        ),
        dag_version=dag.dag_version,
        required_placebo_p_above=MIN_PLACEBO_P,
        required_confidence_at_least=MIN_CONFIDENCE,
        edges=edges,
    )


# --- compare_facts ---------------------------------------------------------------------------------------


class Operation(StrEnum):
    DIFFERENCE = "difference"
    RATIO = "ratio"
    PERCENT_CHANGE = "percent_change"


class CompareArgs(StrictModel):
    left_fact_id: str
    right_fact_id: str
    operation: Operation


class Comparison(ToolResult):
    operation: str
    left_fact_id: str
    right_fact_id: str
    left_value: float
    right_value: float
    result: float


def _compute(
    op: Operation, left: float, right: float, left_unit: str, right_unit: str
) -> tuple[float, str]:
    if op is Operation.DIFFERENCE:
        if left_unit != right_unit:
            raise PortError(
                ToolErrorCode.INVALID_ARGUMENTS, f"cannot subtract {right_unit} from {left_unit}"
            )
        return left - right, left_unit
    if right == 0:
        raise PortError(ToolErrorCode.INVALID_ARGUMENTS, "the right-hand figure is zero")
    if op is Operation.RATIO:
        return left / right, "ratio"
    if left_unit != right_unit:
        raise PortError(
            ToolErrorCode.INVALID_ARGUMENTS, f"cannot compare {left_unit} with {right_unit}"
        )
    return (left - right) / abs(right) * 100.0, "percent"


def compare_facts(ctx: ReadModels, who: Principal, args: CompareArgs) -> Comparison:
    left, right = (
        ctx.facts.resolve(who, args.left_fact_id),
        ctx.facts.resolve(who, args.right_fact_id),
    )
    result, unit = _compute(args.operation, left.value, right.value, left.unit, right.unit)
    origin = weakest((left.data_origin, right.data_origin))
    base: dict[str, Any] = envelope(
        ctx,
        "calc.compare",
        None,
        "port.compare_facts",
        {"left_value": left.unit, "right_value": right.unit, "result": unit},
        tuple(dict.fromkeys((*left.markings, *right.markings))),
    )
    base.update(as_of=min(left.as_of, right.as_of), data_origin=origin)
    return Comparison(
        **base,
        operation=args.operation.value,
        left_fact_id=left.fact_id,
        right_fact_id=right.fact_id,
        left_value=left.value,
        right_value=right.value,
        result=result,
    )


TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        "get_metric", "metric.get", "evidence", ALL, MetricArgs, MetricValue, get_metric, 300.0
    ),
    ToolSpec(
        "resolve_entity",
        "entity.resolve",
        "evidence",
        (W.AML_INVESTIGATOR, W.PARTNER_MANAGER, W.EXECUTIVE),
        ResolveArgs,
        ResolvedEntity,
        resolve_entity,
        300.0,
    ),
    ToolSpec(
        "get_causal_evidence",
        "causal.evidence",
        "evidence",
        (W.AML_INVESTIGATOR, W.EXECUTIVE),
        CausalArgs,
        CausalEvidence,
        get_causal_evidence,
        300.0,
    ),
    ToolSpec(
        "compare_facts",
        "calc.compare",
        "compute",
        (W.AML_INVESTIGATOR, W.PARTNER_MANAGER, W.EXECUTIVE),
        CompareArgs,
        Comparison,
        compare_facts,
        300.0,
    ),
)
