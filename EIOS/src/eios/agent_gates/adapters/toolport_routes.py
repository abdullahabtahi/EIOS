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
_GATEWAY = re.compile(r"\bGW-[A-Z]{2}-[A-Z]\d{2}\b", re.IGNORECASE)
_CORRIDOR = re.compile(r"\b[A-Z]{2}>[A-Z]{2}\b")
_COUNTRY = re.compile(r"\(([A-Z]{2})\)|\bcountry ([A-Z]{2})\b")  # a code the question spells out
_LIST_EU = re.compile(r"\b(?:eu|european)\b", re.IGNORECASE)


@dataclass
class Found:
    question: str
    account: str | None
    partner: str | None
    percent: float | None
    gateway: str | None = None
    corridor: str | None = None
    country: str | None = None
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
    gateway, corridor, country = (
        _GATEWAY.search(question),
        _CORRIDOR.search(question),
        _COUNTRY.search(question),
    )
    return Found(
        question=question,
        account=account.group(0)
        if account
        else (on_screen if str(on_screen).upper().startswith("CR") else None),
        partner=partner.group(0)
        if partner
        else (on_screen if str(on_screen or "").upper()[:2] in {"PT", "AP", "P-"} else None),
        percent=float(percent.group(1)) if percent else None,
        gateway=gateway.group(0).upper() if gateway else None,
        corridor=corridor.group(0) if corridor else None,
        country=(country.group(1) or country.group(2)) if country else None,
    )


def _acct(f: Found) -> dict[str, Any] | None:
    return {"entity_id": f.account} if f.account else None


def _part(f: Found) -> dict[str, Any] | None:
    return {"entity_id": f.partner} if f.partner else None


def _kind_target(f: Found) -> dict[str, Any] | None:
    target = f.partner or f.account
    return {"entity_id": target} if target else None


def _none(_f: Found) -> dict[str, Any]:
    return {}


_JURISDICTIONS = (
    ("MT", re.compile(r"malta|maltese|\bfiau\b|pmlftr", re.IGNORECASE)),
    ("LB", re.compile(r"labuan", re.IGNORECASE)),
)


def _regulation(f: Found) -> dict[str, Any]:
    """The question as the search query, narrowed to a regulator only when the question names one."""
    args: dict[str, Any] = {"query": f.question}
    for code, pattern in _JURISDICTIONS:
        if pattern.search(f.question):
            args["jurisdiction"] = code
    return args


def _cheapest_deal(f: Found) -> dict[str, Any] | None:
    deals = f.results.get("get_partner_signals", {}).get("retention_deals") or []
    if not (f.partner and deals):
        return None
    return {
        "entity_id": f.partner,
        "playbook_id": min(deals, key=lambda d: d["estimated_cost_usd"])["playbook_id"],
    }


def _what_if(f: Found) -> dict[str, Any] | None:
    if f.percent is None:
        return None
    shock = (
        "competitor_spread_cut" if "spread" in f.question.lower() else "competitor_payout_increase"
    )
    return {"shock": shock, "magnitude_pct": f.percent}


def _revenue(_f: Found) -> dict[str, Any]:
    return {"metric_id": "net_revenue_usd"}


def _forecast(_f: Found) -> dict[str, Any]:
    return {"metric_id": "net_revenue_usd"}


def _gateway(f: Found) -> dict[str, Any] | None:
    return {"gateway_id": f.gateway} if f.gateway else None


def _corridor(f: Found) -> dict[str, Any] | None:
    return {"corridor_id": f.corridor} if f.corridor else None


def _country(f: Found) -> dict[str, Any] | None:
    return {"country_id": f.country} if f.country else None


def _reporting_duty(_f: Found) -> dict[str, Any]:
    return {"query": "duty to report a suspicious transaction", "jurisdiction": "MT"}


def _list(f: Found) -> dict[str, Any]:
    return {"list_id": "eu" if _LIST_EU.search(f.question) else "fatf"}


def _lead_kind(f: Found) -> dict[str, Any]:
    q = f.question.lower()
    kind = "corridor" if "corridor" in q else "account" if "account" in q else "shared_exit"
    return {"kind": kind, "limit": 10}


def _r(pattern: str, *steps: tuple[str, ArgsFn], unless: str | None = None) -> Route:
    return Route(
        re.compile(pattern, re.IGNORECASE),
        steps,
        re.compile(unless, re.IGNORECASE) if unless else None,
    )


ROUTES: tuple[Route, ...] = (
    # Geography: a list change first, then the object the question names, then the book as a whole.
    _r(
        r"plenary|gr[ae]y.?list|delist|newly listed|list change|off its .*list",
        ("get_list_change_impact", _list),
    ),
    _r(r"\bexit\b|gateway", ("get_shared_exit", _gateway), unless=r"plenary|delist"),
    _r(r"\brank\b|\btop\b.*\b(?:corridors|accounts|exits)\b", ("list_geo_leads", _lead_kind)),
    _r(r"corridor", ("get_corridor", _corridor), unless=r"\brank\b|\btop\b"),
    _r(r"exposure|jurisdiction", ("get_jurisdiction", _country), unless=r"plenary|delist"),
    _r(r"where should i (?:look|start)|geography of|whole book", ("get_geo_overview", _none)),
    # A SAR's geography paragraph reads the account and the licensing jurisdiction's duty to report (geo rule 17).
    _r(r"\bSAR\b", ("get_geo_account", _acct), ("search_regulations", _reporting_duty)),
    _r(
        r"log(?:s|ged)? in from|travel|geograph",
        ("get_geo_account", _acct),
        unless=r"geography of|whole book",
    ),
    _r(r"\bhold\b", ("get_aml_dossier", _acct), ("propose_hold", _acct)),
    _r(
        r"withdrawal|take (?:the )?(?:money|funds|cash) out",
        ("check_withdrawal_risk", _acct),
        unless=r"\bhold\b|timeline|reconstruct",
    ),
    _r(r"trend|over time|history|last \d+ days|past \d+ days", ("get_account_history", _acct)),
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
    _r(
        r"how good are the clients|client quality|quality of .*clients",
        ("get_client_quality", _part),
    ),
    _r(
        r"recent messages|telling us|\bcomms\b|what has .* (?:said|written)",
        ("read_partner_comms", _part),
    ),
    _r(r"partner or a client|what kind of entity", ("resolve_entity", _kind_target)),
    _r(r"offer|rebate", ("get_partner_signals", _part), ("propose_partner_action", _cheapest_deal)),
    _r(
        r"churn|at risk|leave|hazard|details|what should i do",
        ("get_partner_signals", _part),
        unless=r"2030|predict",
    ),
    _r(r"which partners|attention|worklist|ecosystem", ("list_partner_worklist", _none)),
    _r(r"morning briefing|briefing", ("get_briefing", _none)),
    _r(
        r"forecast|outlook|coming months|\bheading (?:over|into|for|towards?)\b",
        ("get_forecast", _forecast),
    ),
    _r(r"what happens|what if|cut", ("run_what_if", _what_if)),
    _r(r"causing|causal|\bcause\b", ("get_causal_evidence", _none)),
    _r(r"net revenue", ("get_metric", _revenue)),
    _r(
        r"regulat|guideline|circular|\bfiau\b|labuan|red.?flag|filing threshold",
        ("search_regulations", _regulation),
    ),
    _r(r"hash chain|verify", ("verify_chain", _none)),
    _r(r"audit status|retained|retention", ("get_audit_status", _none)),
    _r(r"calibrat|trust .*probabilit", ("get_calibration_status", _none)),
    _r(r"staged action|intent", ("get_intent_status", _none)),
    _r(r"ledger", ("get_ledger_timeline", _none), unless=r"verify|hash chain"),
    _r(r"data quality|pipeline", ("get_dq_board", _none)),
    _r(r"reliab", ("get_reliability", _none)),
    _r(r"drill|runbook|restore|backup", ("get_drill_status", _none)),
    _r(r"red.?line|governance gate", ("get_red_lines", _none)),
)


def plan(question: str) -> list[tuple[str, ArgsFn]]:
    """Every tool step of every rule the question matches, in rule order, without repeats."""
    steps: list[tuple[str, ArgsFn]] = []
    for route in ROUTES:
        if route.pattern.search(question) and not (route.unless and route.unless.search(question)):
            steps += [s for s in route.steps if s[0] not in {n for n, _ in steps}]
    return steps
