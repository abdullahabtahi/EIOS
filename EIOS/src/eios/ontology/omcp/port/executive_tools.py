"""Executive capabilities (spec 023 US4): the briefing, the projection, the simulation, all from the screen's service."""

from enum import StrEnum

from pydantic import Field

from eios.common.validation import StrictModel
from eios.ontology.omcp.port.common import envelope
from eios.ontology.omcp.port.contracts import PortError, ToolErrorCode, ToolResult
from eios.ontology.omcp.port.principal import Principal, Workstation
from eios.ontology.omcp.port.readmodels import ReadModels
from eios.ontology.omcp.port.registry import ToolSpec
from eios.ontology.omcp.port.shared_tools import CORRELATION, MetricId, causal_label

EXEC = (Workstation.EXECUTIVE,)
_SVC = "cockpit.executive.ExecutiveCockpitService"
# The causal chain the structural equations propagate a competitor shock along.
_SHOCK_PATH = (
    ("competitor_payout_rate", "partner_churn_rate"),
    ("partner_churn_rate", "client_volume_decay"),
    ("client_volume_decay", "net_pnl_usd"),
)


class NoArgs(StrictModel):
    pass


# --- get_briefing ----------------------------------------------------------------------------------------


class Horizon(StrictModel):
    horizon_name: str
    headline: str
    primary_metric_id: str
    observed_value: float
    delta_period_pct: float


class Risk(StrictModel):
    risk_id: str
    title: str
    severity: str
    exposure_usd: float


class Opportunity(StrictModel):
    opportunity_id: str
    title: str
    projected_upside_usd: float


class Briefing(ToolResult):
    briefing_id: str
    horizons: list[Horizon]
    risks: list[Risk]
    opportunities: list[Opportunity]


def get_briefing(ctx: ReadModels, _who: Principal, _args: NoArgs) -> Briefing:
    b = ctx.executive.get_morning_briefing()
    return Briefing(
        **envelope(
            ctx,
            "exec.briefing",
            None,
            f"{_SVC}.get_morning_briefing",
            {
                "horizons[].observed_value": "USD",
                "horizons[].delta_period_pct": "percent",
                "risks[].exposure_usd": "USD",
                "opportunities[].projected_upside_usd": "USD",
            },
        ),
        briefing_id=b.briefing_id,
        horizons=[
            Horizon(
                horizon_name=h.horizon_name,
                headline=h.headline,
                primary_metric_id=h.primary_metric_id,
                observed_value=h.observed_value,
                delta_period_pct=h.delta_period_pct,
            )
            for h in b.horizons
        ],
        risks=[
            Risk(risk_id=r.risk_id, title=r.title, severity=r.severity, exposure_usd=r.exposure_usd)
            for r in b.risks
        ],
        opportunities=[
            Opportunity(
                opportunity_id=o.opportunity_id,
                title=o.title,
                projected_upside_usd=o.projected_upside_usd,
            )
            for o in b.opportunities
        ],
    )


# --- get_forecast ----------------------------------------------------------------------------------------


class ForecastArgs(StrictModel):
    metric_id: MetricId


class Forecast(ToolResult):
    metric_id: str
    point_estimate: float
    delta_period_pct: float
    headline: str
    is_projection: bool


def get_forecast(ctx: ReadModels, _who: Principal, args: ForecastArgs) -> Forecast:
    # The only projection the executive screen shows is the Financial horizon's. No interval is modelled, so none
    # is returned: an invented interval would read as a measured one.
    if args.metric_id is not MetricId.NET_REVENUE:
        raise PortError(
            ToolErrorCode.DATA_UNAVAILABLE, f"no projection exists for {args.metric_id.value}"
        )
    h = next(
        h for h in ctx.executive.get_morning_briefing().horizons if h.horizon_name == "Financial"
    )
    return Forecast(
        **envelope(
            ctx,
            "exec.forecast",
            None,
            f"{_SVC}.get_morning_briefing",
            {"point_estimate": "USD", "delta_period_pct": "percent"},
        ),
        metric_id=args.metric_id.value,
        point_estimate=h.observed_value,
        delta_period_pct=h.delta_period_pct,
        headline=h.headline,
        is_projection=True,
    )


# --- run_what_if -----------------------------------------------------------------------------------------


class Shock(StrEnum):
    COMPETITOR_SPREAD_CUT = "competitor_spread_cut"


class WhatIfArgs(StrictModel):
    shock: Shock
    magnitude_pct: float = Field(ge=-100.0, le=100.0)


class Attribution(StrictModel):
    driver: str
    contribution_pct: float


class WhatIf(ToolResult):
    shock: str
    magnitude_pct: float
    is_simulation: bool
    partner_churn_delta_pct: float
    client_turnover_delta_pct: float
    projected_ebitda_impact_usd: float
    ebitda_interval_low_usd: float
    ebitda_interval_high_usd: float
    attribution: list[Attribution]
    attribution_sum_pct: float
    causal_label: str
    causal_reason: str


def run_what_if(ctx: ReadModels, _who: Principal, args: WhatIfArgs) -> WhatIf:
    out = ctx.executive.simulate_what_if_shock(args.shock.value, args.magnitude_pct)
    changes, ci = out["projected_changes"], sorted(out["confidence_interval"])
    attribution = [
        Attribution(driver=a["driver"], contribution_pct=a["contribution_pct"])
        for a in out["attribution_waterfall"]
    ]
    total = round(sum(a.contribution_pct for a in attribution), 2)
    if total != 100.0:  # RL-6: attribution must close to 100; a result that does not is never shown
        raise PortError(
            ToolErrorCode.DATA_UNAVAILABLE, "the simulation's attribution did not sum to 100%"
        )
    label, reason = _chain_label(ctx)
    return WhatIf(
        **envelope(
            ctx,
            "exec.what_if",
            None,
            f"{_SVC}.simulate_what_if_shock",
            {
                "magnitude_pct": "percent",
                "partner_churn_delta_pct": "percent",
                "client_turnover_delta_pct": "percent",
                "projected_ebitda_impact_usd": "USD",
                "ebitda_interval_low_usd": "USD",
                "ebitda_interval_high_usd": "USD",
                "attribution[].contribution_pct": "percent",
                "attribution_sum_pct": "percent",
            },
        ),
        shock=args.shock.value,
        magnitude_pct=args.magnitude_pct,
        is_simulation=True,
        partner_churn_delta_pct=changes["partner_churn_delta_pct"],
        client_turnover_delta_pct=changes["client_turnover_delta_pct"],
        projected_ebitda_impact_usd=changes["projected_ebitda_impact_usd"],
        ebitda_interval_low_usd=ci[0],
        ebitda_interval_high_usd=ci[1],
        attribution=attribution,
        attribution_sum_pct=total,
        causal_label=label,
        causal_reason=reason,
    )


def _chain_label(ctx: ReadModels) -> tuple[str, str]:
    edges = {(e.source_node_id, e.target_node_id): e for e in ctx.executive.get_causal_dag().edges}
    weakest = CORRELATION
    for pair in _SHOCK_PATH:
        edge = edges.get(pair)
        if edge is None:
            return CORRELATION, f"no tested causal link from {pair[0]} to {pair[1]}"
        label, reason = causal_label(edge.refuter.confidence, edge.refuter.placebo_p_value)
        if label == weakest:
            return CORRELATION, f"{pair[0]} to {pair[1]}: {reason}"
    return "VERIFIED_CAUSAL", "every link on the shock path passed the placebo refuter"


TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        "get_briefing", "exec.briefing", "evidence", EXEC, NoArgs, Briefing, get_briefing, 300.0
    ),
    ToolSpec(
        "get_forecast",
        "exec.forecast",
        "evidence",
        EXEC,
        ForecastArgs,
        Forecast,
        get_forecast,
        300.0,
    ),
    ToolSpec(
        "run_what_if", "exec.what_if", "compute", EXEC, WhatIfArgs, WhatIf, run_what_if, 200.0
    ),
)
