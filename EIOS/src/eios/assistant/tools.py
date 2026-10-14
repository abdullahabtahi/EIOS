"""Expose the governed tool port to an ADK agent (spec 021 FR-006, FR-009; spec 023).

One `PortTool` per capability the verified principal is offered. The principal is fixed when the toolset is built,
so a model can never choose an identity; arguments are validated by the port against the capability's own model.
Fact ids of every figure a result returned are kept in turn state, which is what the answer assembler checks a
`{{fact:...}}` placeholder against.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from typing import Any

from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext

from eios.llm_gateway.providers.adk_types import FunctionDeclaration
from eios.ontology.omcp.port.principal import Principal
from eios.ontology.omcp.port.registry import ToolSpec
from eios.ontology.omcp.port.service import GovernedToolPort

# `temp:` state lives for one invocation: the loop's attempts share it, the stored session does not keep it.
FACTS_KEY = "temp:facts"  # fact id -> the figure, unit and envelope a tool returned this turn
SOURCES_KEY = "temp:sources"
ORIGINS_KEY = "temp:data_origins"
PROPOSALS_KEY = "temp:proposals"
_PROPOSAL_KIND = "propose"


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
        raw = outcome.payload()
        if outcome.result is None:
            return raw
        payload = expand_fact_ids(
            raw
        )  # what the model sees; the facts are read from the result as the port gave it
        state = tool_context.state
        state[FACTS_KEY] = {**state.get(FACTS_KEY, {}), **_turn_facts(raw)}
        state[SOURCES_KEY] = [*state.get(SOURCES_KEY, []), payload["source"]]
        state[ORIGINS_KEY] = [*state.get(ORIGINS_KEY, []), payload["data_origin"]]
        if self._spec.kind == _PROPOSAL_KIND:
            state[PROPOSALS_KEY] = [*state.get(PROPOSALS_KEY, []), payload]
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


def build_toolset(port: GovernedToolPort, principal: Principal) -> list[PortTool]:
    return [PortTool(port, principal, spec) for spec in port.list_tools(principal)]
