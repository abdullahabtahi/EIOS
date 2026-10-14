"""AML capabilities (spec 023 US1): built from `AMLWorkstationService`, the service the dossier screen renders."""

from pydantic import Field

from eios.aml.withdrawal_sentinel import WithdrawalSentinel, score_withdrawal
from eios.common.validation import StrictModel
from eios.ontology.config import SecurityMarking
from eios.ontology.omcp.port.aml_fixtures import (
    DOSSIER_ENTITY,
    PENDING_WITHDRAWALS,
    timeline_for,
)
from eios.ontology.omcp.port.common import envelope
from eios.ontology.omcp.port.contracts import PortError, ToolErrorCode, ToolResult
from eios.ontology.omcp.port.entities import EntityKind
from eios.ontology.omcp.port.principal import Principal, Workstation
from eios.ontology.omcp.port.readmodels import ReadModels
from eios.ontology.omcp.port.registry import ToolSpec

AML = (Workstation.AML_INVESTIGATOR,)
PRIVATE = (SecurityMarking.PII, SecurityMarking.SENSITIVE_COMPLIANCE)
_SVC = "cockpit.aml.AMLWorkstationService"


class AccountArgs(StrictModel):
    entity_id: str


class AlertsArgs(StrictModel):
    min_score: int = Field(default=50, ge=0, le=100)
    limit: int = Field(default=10, ge=1, le=50)


def _account(ctx: ReadModels, raw: str) -> str:
    return ctx.directory.resolve(raw, EntityKind.ACCOUNT).entity_id


def _dossier_account(ctx: ReadModels, raw: str, what: str) -> str:
    entity_id = _account(ctx, raw)
    if entity_id != DOSSIER_ENTITY:
        raise PortError(
            ToolErrorCode.DATA_UNAVAILABLE, f"no {what} is available for {entity_id} yet"
        )
    return entity_id


# --- list_alerts -----------------------------------------------------------------------------------------


class AlertItem(StrictModel):
    alert_id: str
    entity_id: str
    risk_score: int
    discrepancy_summary: str
    syndicate_size: int
    age_hours: float
    status: str


class AlertList(ToolResult):
    alerts: list[AlertItem]


def list_alerts(ctx: ReadModels, _who: Principal, args: AlertsArgs) -> AlertList:
    items = ctx.aml.get_triage_queue(min_score=args.min_score, limit=args.limit)
    ranked = sorted(items, key=lambda a: a["risk_score"], reverse=True)
    return AlertList(
        **envelope(
            ctx,
            "aml.alerts",
            None,
            f"{_SVC}.get_triage_queue",
            {
                "alerts[].risk_score": "score",
                "alerts[].syndicate_size": "accounts",
                "alerts[].age_hours": "hours",
            },
            PRIVATE,
        ),
        alerts=[AlertItem(**a) for a in ranked],
    )


# --- get_aml_dossier -------------------------------------------------------------------------------------


class AmlDossier(ToolResult):
    case_id: str
    identity_cluster_key: str
    composite_risk_score: int
    declared_monthly_income_usd: float
    employment_status: str
    country_of_residence: str
    kyc_approval_timestamp: str
    realized_deposit_volume_30d_usd: float
    discrepancy_multiplier: float
    crypto_usdt_deposit_ratio: float
    syndicate_ring_size: int
    dowhy_refuter_confirmed: bool
    is_withdrawal_held: bool


def get_aml_dossier(ctx: ReadModels, _who: Principal, args: AccountArgs) -> AmlDossier:
    entity_id = _dossier_account(ctx, args.entity_id, "dossier")
    d = ctx.aml.get_entity_dossier(entity_id)
    return AmlDossier(
        **envelope(
            ctx,
            "aml.dossier",
            entity_id,
            f"{_SVC}.get_entity_dossier",
            {
                "composite_risk_score": "score",
                "declared_monthly_income_usd": "USD",
                "realized_deposit_volume_30d_usd": "USD",
                "discrepancy_multiplier": "multiplier",
                "crypto_usdt_deposit_ratio": "ratio",
                "syndicate_ring_size": "accounts",
            },
            PRIVATE,
        ),
        case_id=d.case_id,
        identity_cluster_key=d.identity_cluster_key,
        composite_risk_score=d.composite_risk_score,
        declared_monthly_income_usd=d.kyc.declared_monthly_income_usd,
        employment_status=d.kyc.employment_status,
        country_of_residence=d.kyc.country_of_residence,
        kyc_approval_timestamp=d.kyc.kyc_approval_timestamp.isoformat(),
        realized_deposit_volume_30d_usd=d.discrepancy.realized_deposit_volume_30d_usd,
        discrepancy_multiplier=d.discrepancy.discrepancy_multiplier,
        crypto_usdt_deposit_ratio=d.discrepancy.crypto_usdt_deposit_ratio,
        syndicate_ring_size=d.syndicate_ring_size,
        dowhy_refuter_confirmed=d.dowhy_refuter_confirmed,
        is_withdrawal_held=d.is_withdrawal_held,
    )


# --- get_network_evidence --------------------------------------------------------------------------------


class NetworkNode(StrictModel):
    node_id: str
    node_type: str
    label: str
    degree: int
    is_hub_suppressed: bool
    collapsed_node_count: int


class NetworkEdge(StrictModel):
    source_node_id: str
    target_node_id: str
    edge_type: str
    transaction_volume_usd: float | None
    matched_timing_seconds: float | None


class NetworkEvidence(ToolResult):
    graph_id: str
    nodes: list[NetworkNode]
    edges: list[NetworkEdge]
    total_uncollapsed_entities: int
    hub_suppressed_count: int


def get_network_evidence(ctx: ReadModels, _who: Principal, args: AccountArgs) -> NetworkEvidence:
    entity_id = _dossier_account(ctx, args.entity_id, "network graph")
    g = ctx.aml.get_kinetic_network_graph(entity_id)
    nodes = [
        NetworkNode(
            node_id=n.node_id,
            node_type=n.node_type.value,
            label=n.label,
            degree=n.degree,
            is_hub_suppressed=n.is_hub_suppressed,
            collapsed_node_count=n.collapsed_node_count,
        )
        for n in g.nodes
    ]
    return NetworkEvidence(
        **envelope(
            ctx,
            "aml.network",
            entity_id,
            f"{_SVC}.get_kinetic_network_graph",
            {
                "nodes[].degree": "count",
                "nodes[].collapsed_node_count": "count",
                "edges[].transaction_volume_usd": "USD",
                "edges[].matched_timing_seconds": "seconds",
                "total_uncollapsed_entities": "accounts",
                "hub_suppressed_count": "count",
            },
            PRIVATE,
        ),
        graph_id=g.graph_id,
        nodes=nodes,
        edges=[
            NetworkEdge(
                source_node_id=e.source_node_id,
                target_node_id=e.target_node_id,
                edge_type=e.edge_type,
                transaction_volume_usd=e.transaction_volume_usd,
                matched_timing_seconds=e.matched_timing_seconds,
            )
            for e in g.edges
        ],
        total_uncollapsed_entities=g.total_uncollapsed_entities,
        hub_suppressed_count=sum(1 for n in nodes if n.is_hub_suppressed),
    )


# --- get_activity_timeline -------------------------------------------------------------------------------


class TimelineItem(StrictModel):
    at: str
    kind: str
    amount_usd: float | None
    detail: str


class ActivityTimeline(ToolResult):
    events: list[TimelineItem]


def get_activity_timeline(ctx: ReadModels, _who: Principal, args: AccountArgs) -> ActivityTimeline:
    entity_id = _dossier_account(ctx, args.entity_id, "activity timeline")
    kyc = ctx.aml.get_entity_dossier(entity_id).kyc.kyc_approval_timestamp
    events = timeline_for(entity_id, kyc) or []
    return ActivityTimeline(
        **envelope(
            ctx,
            "aml.timeline",
            entity_id,
            "cockpit.aml + port.aml_fixtures",
            {"events[].amount_usd": "USD"},
            PRIVATE,
        ),
        events=[
            TimelineItem(at=e.at.isoformat(), kind=e.kind, amount_usd=e.amount_usd, detail=e.detail)
            for e in events
        ],
    )


# --- check_withdrawal_risk -------------------------------------------------------------------------------


class WithdrawalRisk(ToolResult):
    withdrawal_id: str
    amount_usd: float
    hours_since_deposit: float
    risk_score: float
    hold_threshold: float
    recommendation: str


def check_withdrawal_risk(ctx: ReadModels, _who: Principal, args: AccountArgs) -> WithdrawalRisk:
    entity_id = _account(ctx, args.entity_id)
    pending = PENDING_WITHDRAWALS.get(entity_id)
    if pending is None:
        raise PortError(ToolErrorCode.NOT_FOUND, f"no pending withdrawal for {entity_id}")
    alert = next(
        (
            a
            for a in ctx.aml.get_triage_queue(min_score=0, limit=100)
            if a["entity_id"] == entity_id
        ),
        None,
    )
    if alert is None:
        raise PortError(ToolErrorCode.DATA_UNAVAILABLE, f"no alert score for {entity_id}")
    score = score_withdrawal(
        alert["risk_score"] / 100.0,
        pending.hours_since_deposit,
        pending.market_risk_pct,
        pending.hours_since_kyc,
    )
    threshold = WithdrawalSentinel().hold_risk_threshold
    return WithdrawalRisk(
        **envelope(
            ctx,
            "aml.withdrawal_risk",
            entity_id,
            "aml.withdrawal_sentinel.score_withdrawal",
            {
                "amount_usd": "USD",
                "hours_since_deposit": "hours",
                "risk_score": "ratio",
                "hold_threshold": "ratio",
            },
            PRIVATE,
        ),
        withdrawal_id=pending.withdrawal_id,
        amount_usd=pending.amount_usd,
        hours_since_deposit=pending.hours_since_deposit,
        risk_score=score,
        hold_threshold=threshold,
        recommendation="PROPOSE_HOLD" if score >= threshold else "ALLOW",
    )


# --- draft_sar -------------------------------------------------------------------------------------------


class SarDraft(ToolResult):
    sar_id: str
    case_id: str
    regulator_template_id: str
    pseudonymized_cluster_key: str
    narrative_summary: str
    statutory_citations: list[str]
    cited_fact_ids: list[str]
    investigator_id: str
    status: str
    requires_human_review: bool


_CITED = {"realized_deposit_volume_30d_usd", "discrepancy_multiplier"}


def draft_sar(ctx: ReadModels, who: Principal, args: AccountArgs) -> SarDraft:
    entity_id = _dossier_account(ctx, args.entity_id, "SAR draft")
    sar = ctx.aml.compose_sar_draft(entity_id=entity_id, investigator_id=who.uid)
    cited = [f"aml.dossier:{entity_id}:{m}" for m in sar.cited_metric_ids if m in _CITED]
    return SarDraft(
        **envelope(ctx, "aml.sar_draft", entity_id, f"{_SVC}.compose_sar_draft", {}, PRIVATE),
        sar_id=sar.sar_id,
        case_id=sar.case_id,
        regulator_template_id=sar.regulator_template_id,
        pseudonymized_cluster_key=sar.pseudonymized_cluster_key,
        narrative_summary=sar.narrative_summary,
        statutory_citations=sar.statutory_citations,
        cited_fact_ids=cited,
        investigator_id=sar.investigator_id,
        status="DRAFT",
        requires_human_review=True,
    )


def _spec(
    name: str,
    capability: str,
    kind: str,
    args: type[StrictModel],
    out: type[ToolResult],
    fn,
    budget_ms: float = 300.0,
) -> ToolSpec:
    return ToolSpec(
        name=name,
        capability=capability,
        kind=kind,
        workstations=AML,
        args_model=args,
        result_model=out,
        handler=fn,
        budget_ms=budget_ms,
        markings=PRIVATE,
    )


TOOLS: tuple[ToolSpec, ...] = (
    _spec("list_alerts", "aml.alerts", "evidence", AlertsArgs, AlertList, list_alerts),
    _spec("get_aml_dossier", "aml.dossier", "evidence", AccountArgs, AmlDossier, get_aml_dossier),
    _spec(
        "get_network_evidence",
        "aml.network",
        "evidence",
        AccountArgs,
        NetworkEvidence,
        get_network_evidence,
    ),
    _spec(
        "get_activity_timeline",
        "aml.timeline",
        "evidence",
        AccountArgs,
        ActivityTimeline,
        get_activity_timeline,
    ),
    _spec(
        "check_withdrawal_risk",
        "aml.withdrawal_risk",
        "evidence",
        AccountArgs,
        WithdrawalRisk,
        check_withdrawal_risk,
    ),
    _spec("draft_sar", "aml.sar_draft", "draft", AccountArgs, SarDraft, draft_sar),
)
