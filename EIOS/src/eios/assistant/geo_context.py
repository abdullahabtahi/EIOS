"""What the geospatial assistant is told on top of the shared rules: how to use geography fairly, and what is on the map.

The map context arrives with the question (`MapContext`, validated: closed vocabularies and the map's own id shapes), so
"why is this suspicious?" is about the selected object without the model guessing, and the platform can run that
object's tool before the model's first call (`prefetch.py`).
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any, Literal

from pydantic import Field

from eios.common.validation import StrictModel

MapView = Literal["corridors", "logins", "jurisdictions"]
MapBasis = Literal["fatf", "eu", "basel"]
SelectionKind = Literal["country", "corridor", "mismatch", "gateway", "account"]


class MapSelection(StrictModel):
    kind: SelectionKind
    id: str = Field(
        pattern=r"^[A-Za-z0-9>_-]{1,64}$"
    )  # the map's own id shapes, as its URL accepts them


class MapContext(StrictModel):
    view: MapView
    selection: MapSelection | None = None
    basis: MapBasis | None = None


GEO_RULES = """\
Geography rules for this workstation:
10. Geography is evidence, never a verdict. Never draw a conclusion from where a person lives or comes from. Describe
    behaviour the tools found: accounts registered in different countries logging in through one gateway abroad, a jump
    no flight could make, money routed through a listed jurisdiction. A lens flag is a reason to look, not proof.
11. A lens that could not judge an account (assessable false or null) has not cleared it: say it was not assessed,
    never that it is clean or low risk. A country absent from a list is unlisted; absent from the Basel index, unrated;
    neither is safe.
12. To move the map, put {{map:<kind>:<id>}} right after the object it shows, with a kind and target_id from a
    map_targets entry of a tool result of this turn (country, corridor, mismatch, gateway or account). The first is
    selected and framed on the map. Use at most three, only for objects you discuss, and never write coordinates.
13. Name a gateway, account, corridor or country by the id or name a result gives. Never write the id of a device,
    payment token or address.
14. Linked accounts come from BigQuery Graph (a ring, a neighbourhood, list-change links). If that part of a result
    carries an error, say the graph could not be reached and answer from the rest of the result.
15. A list change ends or starts a duty to apply enhanced measures; it does not change what the accounts did. When a
    country leaves a list, say what activity there continues.
16. Never count the items of a list yourself, in digits or in words ("two countries", "four lenses"). State a count only
    when a result returns it (login_country_count, gateway_count, lens_count, accounts, home_countries); otherwise name
    the items instead of counting them.
"""

_VIEW = {"corridors": "Corridors", "logins": "Login vs KYC", "jurisdictions": "Jurisdictions"}
_BASIS = {"fatf": "the FATF lists", "eu": "the EU high-risk list", "basel": "the Basel AML Index"}
_KIND = {
    "country": "country",
    "corridor": "corridor",
    "mismatch": "login-country pair",
    "gateway": "gateway",
    "account": "account",
}


_LIST_CHANGE = re.compile(
    r"\b(?:plenary|gr[ae]y.?list\w*|black.?list\w*|de.?list\w*|newly listed|list change\w*|amend\w*|"
    r"(?:off|onto|from|to) (?:its|the|their) (?:[\w-]+ ){0,2}list)\b",
    re.IGNORECASE,
)
_EU = re.compile(r"\b(?:eu|european)\b", re.IGNORECASE)
# What a question can name in the map's own id shapes. A country counts only when spelled out as a code: "(IQ)".
_NAMED = (
    (re.compile(r"\bGW-[A-Z]{2}-[A-Z]\d{2}\b", re.IGNORECASE), "get_shared_exit", "gateway_id"),
    (re.compile(r"\b[A-Z]{2}>[A-Z]{2}\b"), "get_corridor", "corridor_id"),
    (re.compile(r"\(([A-Z]{2})\)"), "get_jurisdiction", "country_id"),
)
# The overview is read ahead only for a question about where to look; anything else is left to the model, so a question
# no tool should answer (one about people by origin) is not handed a result to answer from.
_WHERE_TO_LOOK = re.compile(
    r"\b(?:where should|where do i|where to|look first|start(?:ing)? (?:with|from)|overview|summar\w*|brief me|"
    r"stands? out|anything (?:new|unusual)|whole book|what should i (?:look|check))\b",
    re.IGNORECASE,
)
# "Rank the top corridors": a ranking of one kind of lead reads that list, not the overview (which shows only a few).
_RANKING = re.compile(
    r"\b(?:rank\w*|top|largest|biggest|highest|riskiest|most (?:suspicious|elevated|unusual))\b",
    re.IGNORECASE,
)
_LEAD_WORDS = (
    (re.compile(r"\bcorridors?\b", re.IGNORECASE), "corridor"),
    (re.compile(r"\b(?:shared )?(?:exits?|gateways?)\b", re.IGNORECASE), "shared_exit"),
    (re.compile(r"\blogin.country pairs?\b|\bmismatch\w*\b", re.IGNORECASE), "login_country"),
    (re.compile(r"\baccounts?\b", re.IGNORECASE), "account"),
)
_SELECTION_TOOL = {
    "account": ("get_geo_account", "entity_id"),
    "gateway": ("get_shared_exit", "gateway_id"),
    "corridor": ("get_corridor", "corridor_id"),
    "country": ("get_jurisdiction", "country_id"),
}


def _named_step(question: str) -> tuple[str, dict[str, Any]] | None:
    for pattern, tool, field in _NAMED:
        match = pattern.search(question)
        if match:
            value = match.group(match.lastindex or 0)
            return tool, {field: value.upper()}
    return None


_PROTECTED = re.compile(
    r"\b(?:nationalit\w*|ethnic\w*|race|racial\w*|religio\w*|citizenship|immigrants?|"
    r"(?:people|clients|customers|users) (?:from|born in) (?:which|what)|country of birth)\b",
    re.IGNORECASE,
)


def asks_about_origin(question: str) -> bool:
    """Does the question ask to judge people by nationality, ethnicity, race or religion (refused, rule 10)?"""
    return bool(_PROTECTED.search(question))


def _ranked_kind(question: str) -> str | None:
    """The lead kind a ranking question asks for ("rank the top corridors" is corridor), or None."""
    if not _RANKING.search(question):
        return None
    return next((kind for pattern, kind in _LEAD_WORDS if pattern.search(question)), None)


def geo_steps(
    question: str, named: str | None, context: Mapping[str, Any] | None
) -> list[tuple[str, dict[str, Any]]]:
    """The tool to run before the model speaks: what the question names, else what the map has selected.

    In order: a list change runs the list comparison; an account, exit, corridor or country code the question names runs
    its own tool; a selection on the map runs its tool (a login-country pair has none of its own, so the model chooses);
    with nothing selected, only a where-to-look question reads the overview. A wrong guess costs a tool call, never a
    wrong answer: the result passes through the same port and the same assembler. A question about people by origin
    reads nothing: the drafter refuses it before the model runs (origin_guard.py)."""
    if asks_about_origin(question):
        return []
    if _LIST_CHANGE.search(question):
        return [("get_list_change_impact", {"list_id": "eu" if _EU.search(question) else "fatf"})]
    if named:
        return [("get_geo_account", {"entity_id": named})]
    if (step := _named_step(question)) is not None:
        return [step]
    found = parse(context)
    if found is None or found.selection is None:
        if (kind := _ranked_kind(question)) is not None:
            return [("list_geo_leads", {"kind": kind})]
        return [("get_geo_overview", {})] if _WHERE_TO_LOOK.search(question) else []
    selected = _SELECTION_TOOL.get(found.selection.kind)
    return [(selected[0], {selected[1]: found.selection.id})] if selected else []


def parse(context: Mapping[str, Any] | None) -> MapContext | None:
    """The map context the turn carries, or None when there is none or it does not validate."""
    if not context:
        return None
    try:
        return MapContext.model_validate(context)
    except ValueError:
        return None


def describe_map(context: Mapping[str, Any] | None, *, named: str | None = None) -> str:
    """One paragraph for the instructions: the view, the colouring basis and what is selected."""
    found = parse(context)
    lines: list[str] = []
    if found is None:
        lines.append("The map context is not known.")
    else:
        basis = (
            f", coloured by {_BASIS[found.basis]}"
            if found.view == "jurisdictions" and found.basis
            else ""
        )
        if found.selection is None:
            lines.append(
                f"On the map: the {_VIEW[found.view]} view{basis}, nothing selected. A question that names nothing "
                "is about the whole book: start from the overview."
            )
        else:
            kind = _KIND[found.selection.kind]
            lines.append(
                f"On the map: the {_VIEW[found.view]} view{basis}, with {kind} {found.selection.id} selected. "
                f"'This' or 'it' in the question means that {kind}."
            )
    if named:
        lines.append(
            f"The question names account {named}: answer about it, and say which account you answered about."
        )
    return " ".join(lines)
