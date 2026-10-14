"""A deterministic question router for the reference runtime: question text to the governed tools to try.

This is a harness, not an agent: it makes the port's behaviour observable through the 022 cases without a
model. It routes by explicit rules, and it is only ever allowed to try tools the caller's workstation is offered.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

_ACCOUNT = re.compile(r"\bCR\d{4,6}\b", re.IGNORECASE)
_PARTNER = re.compile(r"\b(?:PTR|AP|P)-\d{2,5}\b", re.IGNORECASE)
_PERCENT = re.compile(r"(\d+(?:\.\d+)?)\s*(?:percent|%)", re.IGNORECASE)


@dataclass
class Found:
    account: str | None
    partner: str | None
    percent: float | None
    results: dict[str, dict[str, Any]] = field(default_factory=dict)  # tool name -> payload so far


ArgsFn = Callable[[Found], dict[str, Any] | None]


@dataclass(frozen=True)
class Route:
    pattern: re.Pattern[str]
    steps: tuple[tuple[str, ArgsFn], ...]
    unless: re.Pattern[str] | None = None


def extract(question: str, context: dict[str, Any] | None) -> Found:
    account = _ACCOUNT.search(question)
    partner = _PARTNER.search(question)
    percent = _PERCENT.search(question)
    on_screen = (context or {}).get("entity_id")
    return Found(
        account=account.group(0)
        if account
        else (on_screen if str(on_screen).upper().startswith("CR") else None),
        partner=partner.group(0)
        if partner
        else (on_screen if str(on_screen or "").upper()[:2] in {"PT", "AP", "P-"} else None),
        percent=float(percent.group(1)) if percent else None,
    )


def _acct(f: Found) -> dict[str, Any] | None:
    return {"entity_id": f.account} if f.account else None


def _part(f: Found) -> dict[str, Any] | None:
    return {"entity_id": f.partner} if f.partner else None


def _none(_f: Found) -> dict[str, Any]:
    return {}


def _cheapest_deal(f: Found) -> dict[str, Any] | None:
    deals = f.results.get("get_partner_signals", {}).get("retention_deals") or []
    if not (f.partner and deals):
        return None
    return {
        "entity_id": f.partner,
        "playbook_id": min(deals, key=lambda d: d["estimated_cost_usd"])["playbook_id"],
    }


def _what_if(f: Found) -> dict[str, Any] | None:
    return (
        {"shock": "competitor_spread_cut", "magnitude_pct": f.percent}
        if f.percent is not None
        else None
    )


def _revenue(_f: Found) -> dict[str, Any]:
    return {"metric_id": "net_revenue_usd"}


def _forecast(_f: Found) -> dict[str, Any]:
    return {"metric_id": "net_revenue_usd"}


def _r(pattern: str, *steps: tuple[str, ArgsFn], unless: str | None = None) -> Route:
    return Route(
        re.compile(pattern, re.IGNORECASE),
        steps,
        re.compile(unless, re.IGNORECASE) if unless else None,
    )


ROUTES: tuple[Route, ...] = (
    _r(r"\bhold\b", ("get_aml_dossier", _acct), ("propose_hold", _acct)),
    _r(r"withdrawal", ("check_withdrawal_risk", _acct), unless=r"\bhold\b|timeline|reconstruct"),
    _r(r"timeline|reconstruct", ("get_activity_timeline", _acct)),
    _r(r"linked|connected|network", ("get_network_evidence", _acct)),
    _r(r"\bsar\b", ("get_aml_dossier", _acct), ("draft_sar", _acct)),
    _r(
        r"discrepancy|dossier|turnover|declared income",
        ("get_aml_dossier", _acct),
        unless=r"\bsar\b",
    ),
    _r(r"(?:show|list|open).*\balerts?\b|triage queue", ("list_alerts", _none)),
    _r(r"integrity|opposite trad", ("get_partner_integrity", _part)),
    _r(r"offer|rebate", ("get_partner_signals", _part), ("propose_partner_action", _cheapest_deal)),
    _r(
        r"churn|at risk|leave|hazard|details",
        ("get_partner_signals", _part),
        unless=r"2030|predict",
    ),
    _r(r"which partners|attention|worklist", ("list_partner_worklist", _none)),
    _r(r"morning briefing|briefing", ("get_briefing", _none)),
    _r(r"forecast", ("get_forecast", _forecast)),
    _r(r"what happens|what if|cut", ("run_what_if", _what_if)),
    _r(r"causing|causal|\bcause\b", ("get_causal_evidence", _none)),
    _r(r"net revenue", ("get_metric", _revenue)),
    _r(r"hash chain|verify", ("verify_chain", _none)),
    _r(r"staged action|intent", ("get_intent_status", _none)),
    _r(r"ledger", ("get_ledger_timeline", _none), unless=r"verify|hash chain"),
    _r(r"data quality|pipeline", ("get_dq_board", _none)),
    _r(r"reliab", ("get_reliability", _none)),
    _r(r"drill|runbook", ("get_drill_status", _none)),
)


def plan(question: str) -> list[tuple[str, ArgsFn]]:
    """Every tool step of every rule the question matches, in rule order, without repeats."""
    steps: list[tuple[str, ArgsFn]] = []
    for route in ROUTES:
        if route.pattern.search(question) and not (route.unless and route.unless.search(question)):
            steps += [s for s in route.steps if s[0] not in {n for n, _ in steps}]
    return steps
