"""Expose the governed tool port to an ADK agent (spec 021 FR-006, FR-009; spec 023).

One `PortTool` per capability the verified principal is offered. The principal is fixed when the toolset is built,
so a model can never choose an identity; arguments are validated by the port against the capability's own model.
Fact ids of every figure a result returned are kept in turn state, which is what the answer assembler checks a
`{{fact:...}}` placeholder against.
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import Iterator
from typing import Any

from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext

from eios.assistant.map_commands import targets_of
from eios.assistant.visuals import sources_of
from eios.llm_gateway.providers.adk_types import FunctionDeclaration
from eios.ontology.omcp.port.principal import Principal
from eios.ontology.omcp.port.proposals import Proposal, stage_request
from eios.ontology.omcp.port.registry import ToolSpec
from eios.ontology.omcp.port.service import CallOutcome, GovernedToolPort

# `temp:` state lives for one invocation: the loop's attempts share it, the stored session does not keep it.
FACTS_KEY = "temp:facts"  # fact id -> the figure, unit and envelope a tool returned this turn
SOURCES_KEY = "temp:sources"
PASSAGES_KEY = "temp:passages"  # passage id -> a regulation passage a tool returned this turn
ORIGINS_KEY = "temp:data_origins"
PROPOSALS_KEY = "temp:proposals"
TABLES_KEY = "temp:tables"  # `<tool>.<field>` -> a list of records a tool returned, as a table or chart may show it
MAP_TARGETS_KEY = (
    "temp:map_targets"  # `kind:ID` of every object a trusted result offered to the map
)
IDENTIFIERS_KEY = (
    "temp:identifiers"  # names a trusted result returned (case, SAR, cluster ids): not figures
)
NUMBERS_KEY = (
    "temp:numbers"  # the plain numbers a trusted result held (not text a user or a dataset wrote)
)
_PROPOSAL_KIND = "propose"
_MAX_NUMBERS = 5000
_IDENTIFIER_FIELD = re.compile(r"(?:^id|_id|_key|_ref)$")
_IDENTIFIER_VALUE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:\-]{2,79}$")


# Short labels a trusted result names things with. Their wording is the platform's, so a digit inside one ("P2P",
# "Volatility 100") belongs to the name. Narrative fields are never in this list.
_NAME_FIELD = re.compile(r"^(?:name|title|label|market|primary_root_cause|[a-z]+_name)$")
_MAX_NAME = 80
_DIGIT_WORD = re.compile(r"\d")


def _name_phrases(value: str) -> set[str]:
    """The name, and the parts of it a model would write on their own: "P2P", "Volatility 100"."""
    words = value.split()
    found = {value}
    for i, word in enumerate(words):
        if not _DIGIT_WORD.search(word):
            continue
        if re.search(r"[A-Za-z]", word):
            found.add(word.strip(".,;:()"))
        elif i > 0:
            found.add(f"{words[i - 1]} {word.strip('.,;:()')}")
    return found


def _walk(node: Any) -> Iterator[tuple[str, str]]:
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(value, str):
                yield key, value
            else:
                yield from _walk(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk(item)


def identifiers_of(payload: dict[str, Any]) -> set[str]:
    """The names and identifier strings a trusted result returns in its own id, key and name fields.

    Only `*_id`, `*_key`, `*_ref`, `name`, `*_name`, `title`, `label`, `market` and `primary_root_cause` fields count (in a nested row as
    well as at the top), and never a result marked untrusted, so free text (a narrative, an injected sentence)
    cannot smuggle a number past the assembler as if it were a name. A bare number is never a name.
    """
    if payload.get("untrusted"):
        return set()
    found: set[str] = set()
    for key, value in _walk(payload):
        if _IDENTIFIER_FIELD.search(key) and _IDENTIFIER_VALUE.match(value):
            found.add(value)
        elif _NAME_FIELD.match(key) and 0 < len(value) <= _MAX_NAME:
            found |= {n for n in _name_phrases(value) if not n.replace(" ", "").isdigit()}
    return found


class PortTool(BaseTool):
    def __init__(self, port: GovernedToolPort, principal: Principal, spec: ToolSpec) -> None:
        super().__init__(name=spec.name, description=spec.description or spec.capability)
        self._port = port
        self._principal = principal
        self._spec = spec

    def _get_declaration(self) -> FunctionDeclaration:
        schema = self._spec.args_model.model_json_schema()
        schema.pop("title", None)
        return FunctionDeclaration(
            name=self.name, description=self.description, parameters_json_schema=schema
        )

    async def run_async(self, *, args: dict[str, Any], tool_context: ToolContext) -> dict[str, Any]:
        outcome = await asyncio.to_thread(self._port.call, self._principal, self.name, dict(args))
        return record_result(tool_context.state, self._spec, outcome, args)


def numbers_of(node: Any, found: set[float] | None = None) -> set[float]:
    """The numbers a result holds as numbers, and the digits in its field names (`realized_volume_30d` holds 30).

    Strings are not read: a message a partner wrote or a name a dataset carries could contain any figure, and a figure
    the model may repeat must come from a value the platform produced."""
    found = set() if found is None else found
    if len(found) >= _MAX_NUMBERS:
        return found
    if isinstance(node, bool):
        return found
    if isinstance(node, int | float):
        found.add(float(node))
    elif isinstance(node, dict):
        for key, value in node.items():
            found.update(float(n) for n in re.findall(r"\d+(?:\.\d+)?", str(key)))
            numbers_of(value, found)
    elif isinstance(node, list | tuple):
        for value in node:
            numbers_of(value, found)
    return found


def record_result(
    state: Any, spec: ToolSpec, outcome: CallOutcome, args: dict[str, Any]
) -> dict[str, Any]:
    """Keep what a tool returned in turn state, and return what the model is shown.

    Used for a tool the model called and for one the platform ran before the model's first turn, so both kinds of result
    can be cited the same way (their fact ids and passage ids are the ones the assembler accepts)."""
    raw = outcome.payload()
    if outcome.result is None:
        return raw
    expanded = expand_fact_ids(raw)
    payload = _model_view(
        expanded
    )  # what the model sees; the facts are read from the result as the port gave it
    tables = sources_of(spec.name, raw, expanded)
    if tables:  # the lists this result offers for a table or chart, by the name the draft writes
        payload = {**payload, "visual_sources": sorted(tables)}
        state[TABLES_KEY] = {**state.get(TABLES_KEY, {}), **tables}
    state[FACTS_KEY] = {**state.get(FACTS_KEY, {}), **_turn_facts(raw)}
    state[PASSAGES_KEY] = {**state.get(PASSAGES_KEY, {}), **_turn_passages(raw)}
    state[SOURCES_KEY] = [*state.get(SOURCES_KEY, []), payload["source"]]
    state[ORIGINS_KEY] = [*state.get(ORIGINS_KEY, []), payload["data_origin"]]
    state[IDENTIFIERS_KEY] = sorted({*state.get(IDENTIFIERS_KEY, []), *identifiers_of(raw)})
    state[NUMBERS_KEY] = sorted({*state.get(NUMBERS_KEY, []), *numbers_of(raw)})[:_MAX_NUMBERS]
    state[MAP_TARGETS_KEY] = sorted({*state.get(MAP_TARGETS_KEY, []), *targets_of(raw)})
    if spec.kind == _PROPOSAL_KIND and isinstance(outcome.result, Proposal):
        kept = {**payload, "stage_request": stage_request(outcome.result, args)}
        state[PROPOSALS_KEY] = [*state.get(PROPOSALS_KEY, []), kept]
    return payload


# A list result names its facts with a template path (`events[].event_amount_usd`); each item gets its own id so a
# model can cite one item's figure. Bounded so a long list cannot flood the model's context. [ASSUMPTION]
MAX_LIST_ITEMS = 40


def _concrete_paths(node: Any, segments: list[str], prefix: str = "") -> Iterator[tuple[str, Any]]:
    """Every (concrete path, value) a template path reaches; `name[]` fans out over the items of a list."""
    if not segments:
        yield prefix, node
        return
    segment, rest = segments[0], segments[1:]
    wildcard = segment.endswith("[]")
    key = segment[:-2] if wildcard else segment
    if not isinstance(node, dict) or key not in node:
        return
    child, base = node[key], f"{prefix}.{key}" if prefix else key
    if not wildcard:
        yield from _concrete_paths(child, rest, base)
    elif isinstance(child, list):
        for index, item in enumerate(child[:MAX_LIST_ITEMS]):
            yield from _concrete_paths(item, rest, f"{base}[{index}]")


def _facts_of(payload: dict[str, Any]) -> list[tuple[str, str, str | None, Any]]:
    """(concrete path, fact id, unit, value) for every value a result's `fact_ids` names, one per list item."""
    out: list[tuple[str, str, str | None, Any]] = []
    for path, fact_id in (payload.get("fact_ids") or {}).items():
        if "[]" in path and not fact_id.endswith(path):
            continue
        unit = (payload.get("units") or {}).get(path)
        for concrete, value in _concrete_paths(payload, path.split(".")):
            if value is None:  # an item without a value offers nothing to cite
                continue
            out.append((concrete, fact_id[: len(fact_id) - len(path)] + concrete, unit, value))
    return out


def expand_fact_ids(payload: dict[str, Any]) -> dict[str, Any]:
    """A copy of a tool payload whose `fact_ids` and `units` name one fact per value, never a list template."""
    facts = _facts_of(payload)
    return {
        **payload,
        "fact_ids": {path: fact_id for path, fact_id, _, _ in facts},
        "units": {path: unit for path, _, unit, _ in facts if unit},
    }


def _turn_facts(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Every figure of a result the assembler may later show: its value, unit, as-of and origin, by fact id."""
    return {
        fact_id: {
            "value": float(value),
            "unit": unit,
            "as_of": payload["as_of"],
            "data_origin": payload["data_origin"],
            "source": payload["source"],
        }
        for _, fact_id, unit, value in _facts_of(payload)
        if unit and isinstance(value, int | float) and not isinstance(value, bool)
    }


def figures_of(payload: dict[str, Any]) -> dict[str, float]:
    """Every unit-bearing figure of a result, by fact id: what an evidence replay compares."""
    return {fact_id: fact["value"] for fact_id, fact in _turn_facts(payload).items()}


def _model_view(payload: dict[str, Any]) -> dict[str, Any]:
    """A result as the model reads it. A regulation passage is shown as numbered sentences only, so the model picks the
    sentences to quote by number and the same words are not sent twice; the whole text stays in turn state for the source."""
    found = payload.get("passages")
    if not isinstance(found, list):
        return payload
    kept = [
        {k: v for k, v in p.items() if k not in {"text", "highlight"}}
        if isinstance(p, dict) and p.get("sentences")
        else p
        for p in found
    ]
    return {**payload, "passages": kept}


def _turn_passages(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """The regulation passages of a result by passage id, each with the origin of the result that carried it."""
    found = payload.get("passages")
    if not isinstance(found, list):
        return {}
    return {
        item["passage_id"]: {**item, "data_origin": payload["data_origin"]}
        for item in found
        if isinstance(item, dict)
        and isinstance(item.get("passage_id"), str)
        and isinstance(item.get("text"), str)
    }


def build_toolset(port: GovernedToolPort, principal: Principal) -> list[PortTool]:
    return [PortTool(port, principal, spec) for spec in port.list_tools(principal)]
