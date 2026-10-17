"""Executive capabilities (spec 023 US4): the briefing, the projection, the simulation, all from the screen's service."""

import math
from enum import StrEnum
from typing import Any

from pydantic import Field

from eios.cockpit.executive import ForecastView
from eios.common.validation import StrictModel
from eios.ontology.omcp.port.common import envelope
from eios.ontology.omcp.port.contracts import PortError, ToolErrorCode, ToolResult
from eios.ontology.omcp.port.principal import Principal, Workstation
from eios.ontology.omcp.port.readmodels import ReadModels
from eios.ontology.omcp.port.registry import ToolSpec
from eios.ontology.omcp.port.shared_tools import CORRELATION, MetricId, causal_label

EXEC = (Workstation.EXECUTIVE,)
_SVC = "cockpit.executive.ExecutiveCockpitService"


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
            origin=ctx.executive_origin,
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
    horizon_days: int | None = None
    interval_low: float | None = None
    interval_high: float | None = None
    interval_nominal_pct: float | None = (
        None  # e.g. 90: the interval is meant to hold 90% of the time
    )
    interval_coverage_pct: float | None = (
        None  # how often it held on forecasts held out from its calibration
    )
    error_vs_persistence: float | None = (
        None  # this model's error over the error of carrying today's value forward
    )
    backtest_origins: int | None = None
    assumption: str | None = None


_FORECAST_UNITS = {
    "point_estimate": "USD",
    "delta_period_pct": "percent",
    "horizon_days": "days",
    "interval_low": "USD",
    "interval_high": "USD",
    "interval_nominal_pct": "percent",
    "interval_coverage_pct": "percent",
    "error_vs_persistence": "ratio",
    "backtest_origins": "forecasts",
}


def _forecast_fields(view: ForecastView) -> dict[str, Any]:
    """The view in the tool's units: ratios read as percentages, the way a person quotes them."""
    fields = view.model_dump(
        exclude={"interval_nominal", "interval_coverage", "skill_vs_persistence"}
    )

    def pct(v: float | None) -> float | None:
        return None if v is None else round(v * 100.0, 1)

    return fields | {
        "interval_nominal_pct": pct(view.interval_nominal),
        "interval_coverage_pct": pct(view.interval_coverage),
        "error_vs_persistence": view.skill_vs_persistence,
    }


def get_forecast(ctx: ReadModels, _who: Principal, args: ForecastArgs) -> Forecast:
    # The interval, when there is one, was measured by backtesting the model on past origins; a plane that has
    # no such measurement returns none, because an invented interval would read as a measured one.
    if args.metric_id is not MetricId.NET_REVENUE:
        raise PortError(
            ToolErrorCode.DATA_UNAVAILABLE, f"no projection exists for {args.metric_id.value}"
        )
    view: ForecastView = ctx.executive.get_forecast(args.metric_id.value)
    return Forecast(
        **envelope(
            ctx,
            "exec.forecast",
            None,
            f"{_SVC}.get_forecast",
            _FORECAST_UNITS,
            origin=ctx.executive_origin,
        ),
        is_projection=True,
        **_forecast_fields(view),
    )


# --- run_what_if -----------------------------------------------------------------------------------------


class Shock(StrEnum):
    COMPETITOR_PAYOUT_INCREASE = "competitor_payout_increase"
    COMPETITOR_SPREAD_CUT = "competitor_spread_cut"


class WhatIfArgs(StrictModel):
    shock: Shock
    magnitude_pct: float = Field(ge=-100.0, le=100.0)


class Attribution(StrictModel):
    driver: str
    contribution_pct: float


class Mitigation(StrictModel):
    playbook_id: str
    title: str
    action_type: str
    target_region: str
    partners: int
    estimated_cost_usd: float
    projected_margin_kept_usd: float


class WhatIf(ToolResult):
    shock: str
    magnitude_pct: float
    is_simulation: bool
    partner_churn_delta_pct: float
    first_deposit_delta_pct: float
    projected_revenue_impact_usd: float
    revenue_interval_low_usd: float
    revenue_interval_high_usd: float
    attribution: list[Attribution]
    attribution_sum_pct: float
    causal_label: str
    causal_reason: str
    extrapolates_beyond_history: bool = False
    mitigations: list[Mitigation] = Field(default_factory=list)
    mitigation_basis: str | None = None


def run_what_if(ctx: ReadModels, _who: Principal, args: WhatIfArgs) -> WhatIf:
    try:
        out = ctx.executive.simulate_what_if_shock(args.shock.value, args.magnitude_pct)
    except ValueError as err:  # a shock with no tested causal path is refused, never simulated
        raise PortError(ToolErrorCode.DATA_UNAVAILABLE, str(err)) from err
    changes, ci = out["projected_changes"], sorted(out["confidence_interval"])
    attribution = [
        Attribution(driver=a["driver"], contribution_pct=a["contribution_pct"])
        for a in out["attribution_waterfall"]
    ]
    total = round(sum(a.contribution_pct for a in attribution), 2)
    if not math.isclose(
        total, 100.0, abs_tol=1e-5
    ):  # RL-6: attribution must close to 100; a result that does not is never shown
        raise PortError(
            ToolErrorCode.DATA_UNAVAILABLE, "the simulation's attribution did not sum to 100%"
        )
    label, reason = _chain_label(ctx, args.shock.value)
    extrapolates = bool(out.get("extrapolates_beyond_history", False))
    if extrapolates:
        label, reason = (
            CORRELATION,
            "the shocked level lies outside anything seen in the history; the fitted effects are not tested there",
        )
    return WhatIf(
        **envelope(
            ctx,
            "exec.what_if",
            None,
            f"{_SVC}.simulate_what_if_shock",
            {
                "magnitude_pct": "percent",
                "partner_churn_delta_pct": "percent",
                "first_deposit_delta_pct": "percent",
                "projected_revenue_impact_usd": "USD",
                "revenue_interval_low_usd": "USD",
                "revenue_interval_high_usd": "USD",
                "attribution[].contribution_pct": "percent",
                "attribution_sum_pct": "percent",
                "mitigations[].partners": "partners",
                "mitigations[].estimated_cost_usd": "USD",
                "mitigations[].projected_margin_kept_usd": "USD",
            },
            origin=ctx.executive_origin,
        ),
        shock=args.shock.value,
        magnitude_pct=args.magnitude_pct,
        is_simulation=True,
        partner_churn_delta_pct=changes["partner_churn_delta_pct"],
        first_deposit_delta_pct=changes["first_deposit_delta_pct"],
        projected_revenue_impact_usd=changes["projected_revenue_impact_usd"],
        revenue_interval_low_usd=ci[0],
        revenue_interval_high_usd=ci[1],
        attribution=attribution,
        attribution_sum_pct=total,
        causal_label=label,
        causal_reason=reason,
        extrapolates_beyond_history=extrapolates,
        mitigations=[Mitigation(**m) for m in out.get("mitigations", [])],
        mitigation_basis=out.get("mitigation_basis"),
    )


def _chain_label(ctx: ReadModels, shock: str) -> tuple[str, str]:
    edges = {(e.source_node_id, e.target_node_id): e for e in ctx.executive.get_causal_dag().edges}
    for pair in ctx.executive.shock_path(shock):
        edge = edges.get(pair)
        if edge is None:
            return CORRELATION, f"no tested causal link from {pair[0]} to {pair[1]}"
        label, reason = causal_label(edge.refuter.confidence, edge.refuter.placebo_p_value)
        if label == CORRELATION:
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
