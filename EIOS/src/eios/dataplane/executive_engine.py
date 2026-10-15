"""Run the executive engines over the seeded firm world and measure them against what was planted (spec 034).

`run_executive_engine` fits the structural causal model from the daily series (each edge gated on its own
evidence), forecasts net revenue 28 days ahead with an interval taken from a rolling-origin backtest, and reports how
close the fit came to the planted coefficients. Nothing reads the truth until the last step, and only to score.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from eios.foundry.scenarios.executive_world import (
    CALENDAR,
    CHURN,
    FTD,
    PAYOUT,
    REVENUE,
    SERIES,
    SPREAD,
    ExecutiveWorld,
    calendar_regressors,
)
from eios.synthesis.backtest import IntervalForecast, forecast_with_interval
from eios.synthesis.scm_fit import CandidateEdge, EmpiricalSCMFitter, FittedSCM

CANDIDATES = (
    CandidateEdge(PAYOUT, CHURN, "A competitor paying more draws partners away"),
    CandidateEdge(CHURN, FTD, "Fewer active partners refer fewer first-time depositors"),
    CandidateEdge(
        FTD,
        REVENUE,
        "First-time depositors bring net revenue",
        adjust=CALENDAR,  # trend and the quarterly cycle are removed so slow drift is not read as an effect
    ),
    CandidateEdge(
        SPREAD,
        CHURN,
        "Control: spread rides on the competitor's move and is expected to cause nothing",
        adjust=(PAYOUT,),
        control=True,
    ),
)
MODEL_VERSION = "scm-fit-1"


@dataclass(frozen=True)
class ExecutiveQuality:
    """How the engines did against the planted truth `[MEASURED]`."""

    history_days: int
    chain_edges_passed: int
    chain_edges: int
    max_coefficient_error: (
        float  # largest relative error of a chain edge's weight against the planted one
    )
    control_rejected: bool
    backtest_origins: int
    forecast_mase: (
        float  # model error over persistence error; below 1 beats carrying the last value
    )
    forecast_coverage: float  # out-of-sample coverage of the 90% interval
    build_seconds: float


@dataclass(frozen=True)
class ExecutiveSnapshot:
    world: ExecutiveWorld
    fit: FittedSCM
    forecast: IntervalForecast
    quality: ExecutiveQuality

    @property
    def latest(self) -> dict[str, float]:
        row = self.world.days.iloc[-1]
        return {name: float(row[name]) for name in SERIES}


def _quality(
    world: ExecutiveWorld, fit: FittedSCM, forecast: IntervalForecast, seconds: float
) -> ExecutiveQuality:
    truth = world.truth
    planted = {
        (PAYOUT, CHURN): truth.payout_to_churn,
        (CHURN, FTD): truth.churn_to_ftd,
        (FTD, REVENUE): truth.ftd_to_revenue,
    }
    chain = [e for e in fit.edges if not e.candidate.control]
    errors = [
        abs(e.weight - planted[(e.candidate.source, e.candidate.target)])
        / abs(planted[(e.candidate.source, e.candidate.target)])
        for e in chain
    ]
    bt = forecast.backtest
    return ExecutiveQuality(
        history_days=len(world.days),
        chain_edges_passed=sum(1 for e in chain if e.passed),
        chain_edges=len(chain),
        max_coefficient_error=round(max(errors), 4),
        control_rejected=fit.controls_rejected,
        backtest_origins=bt.origins,
        forecast_mase=round(bt.mase, 3),
        forecast_coverage=round(bt.coverage_out_of_sample, 3),
        build_seconds=round(seconds, 2),
    )


def run_executive_engine(world: ExecutiveWorld) -> ExecutiveSnapshot:
    started = time.perf_counter()
    days = world.days
    data = {name: days[name].to_numpy() for name in SERIES} | calendar_regressors(len(days))
    fit = EmpiricalSCMFitter(CANDIDATES, MODEL_VERSION).fit(data)
    forecast = forecast_with_interval(days[REVENUE].to_numpy(), {PAYOUT: days[PAYOUT].to_numpy()})
    return ExecutiveSnapshot(
        world=world,
        fit=fit,
        forecast=forecast,
        quality=_quality(world, fit, forecast, time.perf_counter() - started),
    )
