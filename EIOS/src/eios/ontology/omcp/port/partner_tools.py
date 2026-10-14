"""Partner capabilities (spec 023 US3): built from the radar the partner workstation renders."""

from pydantic import Field

from eios.common.validation import StrictModel
from eios.ontology.config import SecurityMarking
from eios.ontology.omcp.port.common import envelope
from eios.ontology.omcp.port.contracts import PortError, ToolErrorCode, ToolResult
from eios.ontology.omcp.port.entities import EntityKind
from eios.ontology.omcp.port.partner_fixtures import MESSAGES, STORY_PARTNER
from eios.ontology.omcp.port.principal import Principal, Workstation
from eios.ontology.omcp.port.readmodels import ReadModels
from eios.ontology.omcp.port.registry import ToolSpec
from eios.ontology.omcp.port.untrusted import bound_excerpt

PM = (Workstation.PARTNER_MANAGER,)
COMMERCIAL = (SecurityMarking.PARTNER_COMMERCIAL,)
_RADAR = "cockpit.partner.PartnerWorkstationService.get_churn_radar_scatter"


class PartnerArgs(StrictModel):
    entity_id: str


class WorklistArgs(StrictModel):
    limit: int = Field(default=10, ge=1, le=20)


def _partner(ctx: ReadModels, raw: str) -> str:
    return ctx.directory.resolve(raw, EntityKind.PARTNER).entity_id


def _radar_item(ctx: ReadModels, partner_id: str):
    return next(
        p for p in ctx.partner.get_churn_radar_scatter().partners if p.partner_id == partner_id
    )


# --- list_partner_worklist -------------------------------------------------------------------------------


class WorklistItem(StrictModel):
    partner_id: str
    name: str
    churn_hazard_probability: float
    realized_volume_30d_usd: float
    expected_loss_usd: float
    primary_root_cause: str
    days_to_intervention_deadline: int


class Worklist(ToolResult):
    partners: list[WorklistItem]


def list_partner_worklist(ctx: ReadModels, _who: Principal, args: WorklistArgs) -> Worklist:
    items = [
        WorklistItem(
            partner_id=p.partner_id,
            name=p.name or p.partner_id,
            churn_hazard_probability=p.churn_hazard_probability,
            realized_volume_30d_usd=p.realized_volume_30d_usd,
            expected_loss_usd=round(p.churn_hazard_probability * p.realized_volume_30d_usd, 2),
            primary_root_cause=p.primary_root_cause,
            days_to_intervention_deadline=p.days_to_intervention_deadline,
        )
        for p in ctx.partner.get_churn_radar_scatter().partners
    ]
    ranked = sorted(items, key=lambda i: i.expected_loss_usd, reverse=True)[: args.limit]
    return Worklist(
        **envelope(
            ctx,
            "partner.worklist",
            None,
            _RADAR,
            {
                "partners[].churn_hazard_probability": "ratio",
                "partners[].realized_volume_30d_usd": "USD",
                "partners[].expected_loss_usd": "USD",
                "partners[].days_to_intervention_deadline": "days",
            },
            COMMERCIAL,
        ),
        partners=ranked,
    )


# --- get_partner_signals ---------------------------------------------------------------------------------


class RetentionDeal(StrictModel):
    playbook_id: str
    title: str
    estimated_cost_usd: float
    projected_retention_uplift_pct: float
    requires_four_eyes: bool


class PartnerSignals(ToolResult):
    name: str
    tier: str | None
    region: str | None
    quadrant: str
    primary_root_cause: str
    churn_hazard_probability: float
    login_decay_pct: float
    ftd_decay_pct: float
    realized_volume_30d_usd: float
    days_to_intervention_deadline: int
    retention_deals: list[RetentionDeal]


def get_partner_signals(ctx: ReadModels, _who: Principal, args: PartnerArgs) -> PartnerSignals:
    partner = _partner(ctx, args.entity_id)
    p = _radar_item(ctx, partner)
    deals = (
        [
            RetentionDeal(
                playbook_id=d.playbook_id,
                title=d.title,
                estimated_cost_usd=d.estimated_cost_usd,
                projected_retention_uplift_pct=d.projected_retention_uplift_pct,
                requires_four_eyes=d.requires_four_eyes,
            )
            for d in ctx.partner.get_retention_playbooks(partner)
        ]
        if partner == STORY_PARTNER
        else []
    )
    return PartnerSignals(
        **envelope(
            ctx,
            "partner.signals",
            partner,
            _RADAR,
            {
                "churn_hazard_probability": "ratio",
                "login_decay_pct": "percent",
                "ftd_decay_pct": "percent",
                "realized_volume_30d_usd": "USD",
                "days_to_intervention_deadline": "days",
                "retention_deals[].estimated_cost_usd": "USD",
                "retention_deals[].projected_retention_uplift_pct": "percent",
            },
            COMMERCIAL,
        ),
        name=p.name or p.partner_id,
        tier=p.tier,
        region=p.region,
        quadrant=p.quadrant.value,
        primary_root_cause=p.primary_root_cause,
        churn_hazard_probability=p.churn_hazard_probability,
        login_decay_pct=p.login_decay_pct,
        ftd_decay_pct=p.ftd_decay_pct,
        realized_volume_30d_usd=p.realized_volume_30d_usd,
        days_to_intervention_deadline=p.days_to_intervention_deadline,
        retention_deals=deals,
    )


# --- get_partner_integrity -------------------------------------------------------------------------------


class RingObservation(StrictModel):
    ring_id: str
    scheme: str
    paired_accounts: list[str]
    matched_timing_seconds: float
    unearned_commission_liability_usd: float


class PartnerIntegrity(ToolResult):
    statement: str
    referred_client_count: int
    active_sub_affiliates_count: int
    rings: list[RingObservation]


def get_partner_integrity(ctx: ReadModels, _who: Principal, args: PartnerArgs) -> PartnerIntegrity:
    partner = _partner(ctx, args.entity_id)
    if partner != STORY_PARTNER:
        raise PortError(
            ToolErrorCode.DATA_UNAVAILABLE,
            f"no integrity evidence is loaded for {partner}; "
            "absence of evidence here is not a clean result",
        )
    tree = ctx.partner.get_partner_referral_tree(partner)
    return PartnerIntegrity(
        **envelope(
            ctx,
            "partner.integrity",
            partner,
            "cockpit.partner.get_partner_referral_tree",
            {
                "referred_client_count": "clients",
                "active_sub_affiliates_count": "partners",
                "rings[].matched_timing_seconds": "seconds",
                "rings[].unearned_commission_liability_usd": "USD",
            },
            COMMERCIAL,
        ),
        statement="Observed patterns only; they are not a finding about the partner's intent.",
        referred_client_count=tree["referred_client_count"],
        active_sub_affiliates_count=tree["active_sub_affiliates_count"],
        rings=[RingObservation(**r) for r in tree["detected_abusive_rings"]],
    )


# --- get_client_quality ----------------------------------------------------------------------------------


class ClientQuality(ToolResult):
    client_quality_index: float


def get_client_quality(ctx: ReadModels, _who: Principal, args: PartnerArgs) -> ClientQuality:
    partner = _partner(ctx, args.entity_id)
    # The scorer runs over a referred-client portfolio and no portfolio feed exists yet (spec 025). Scoring an
    # empty portfolio returns a perfect index, which would read as good news, so it is not served.
    raise PortError(
        ToolErrorCode.DATA_UNAVAILABLE, f"no referred-client portfolio is loaded for {partner}"
    )


# --- read_partner_comms ----------------------------------------------------------------------------------


class TopicCount(StrictModel):
    topic: str
    count: int


class CommsMessage(StrictModel):
    message_id: str
    channel: str
    sentiment: str
    received_at: str
    untrusted: bool
    excerpt: str


class PartnerComms(ToolResult):
    topic_counts: list[TopicCount]
    messages: list[CommsMessage]


def read_partner_comms(ctx: ReadModels, _who: Principal, args: PartnerArgs) -> PartnerComms:
    partner = _partner(ctx, args.entity_id)
    found = MESSAGES.get(partner)
    if not found:
        raise PortError(
            ToolErrorCode.DATA_UNAVAILABLE, f"no partner messages are loaded for {partner}"
        )
    counts: dict[str, int] = {}
    for m in found:
        counts[m.topic] = counts.get(m.topic, 0) + 1
    return PartnerComms(
        **envelope(
            ctx,
            "partner.comms",
            partner,
            "port.partner_fixtures.MESSAGES",
            {"topic_counts[].count": "messages"},
            COMMERCIAL,
            untrusted=True,
        ),
        topic_counts=[TopicCount(topic=t, count=c) for t, c in sorted(counts.items())],
        messages=[
            CommsMessage(
                message_id=m.message_id,
                channel=m.channel,
                sentiment=m.sentiment,
                received_at=m.received_at.isoformat(),
                untrusted=True,
                excerpt=bound_excerpt(m.text),
            )
            for m in found
        ],
    )


def _spec(name: str, cap: str, args: type[StrictModel], out: type[ToolResult], fn) -> ToolSpec:
    return ToolSpec(name, cap, "evidence", PM, args, out, fn, 300.0, COMMERCIAL)


TOOLS: tuple[ToolSpec, ...] = (
    _spec(
        "list_partner_worklist", "partner.worklist", WorklistArgs, Worklist, list_partner_worklist
    ),
    _spec(
        "get_partner_signals", "partner.signals", PartnerArgs, PartnerSignals, get_partner_signals
    ),
    _spec(
        "get_partner_integrity",
        "partner.integrity",
        PartnerArgs,
        PartnerIntegrity,
        get_partner_integrity,
    ),
    _spec(
        "get_client_quality",
        "partner.client_quality",
        PartnerArgs,
        ClientQuality,
        get_client_quality,
    ),
    _spec("read_partner_comms", "partner.comms", PartnerArgs, PartnerComms, read_partner_comms),
)
