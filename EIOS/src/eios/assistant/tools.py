"""Expose the governed tool port to an ADK agent (spec 021 FR-006, FR-009; spec 023).

One `PortTool` per capability the verified principal is offered. The principal is fixed when the toolset is built,
so a model can never choose an identity; arguments are validated by the port against the capability's own model.
Fact ids of every figure a result returned are kept in turn state, which is what the answer assembler checks a
`{{fact:...}}` placeholder against.
"""

from __future__ import annotations

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
        outcome = self._port.call(self._principal, self.name, dict(args))
        payload = outcome.payload()
        if outcome.result is None:
            return payload
        state = tool_context.state
        state[FACTS_KEY] = {**state.get(FACTS_KEY, {}), **_turn_facts(payload)}
        state[SOURCES_KEY] = [*state.get(SOURCES_KEY, []), payload["source"]]
        state[ORIGINS_KEY] = [*state.get(ORIGINS_KEY, []), payload["data_origin"]]
        if self._spec.kind == _PROPOSAL_KIND:
            state[PROPOSALS_KEY] = [*state.get(PROPOSALS_KEY, []), payload]
        return payload


def _figure(payload: dict[str, Any], path: str) -> float | None:
    """The number at a dotted path of a result, or None for list items and anything that is not a plain number."""
    if "[]" in path:
        return None
    node: Any = payload
    for key in path.split("."):
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    return float(node) if isinstance(node, int | float) and not isinstance(node, bool) else None


def _turn_facts(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Every figure of a result the assembler may later show: its value, unit, as-of and origin, by fact id."""
    facts: dict[str, dict[str, Any]] = {}
    for path, fact_id in (payload.get("fact_ids") or {}).items():
        value, unit = _figure(payload, path), (payload.get("units") or {}).get(path)
        if value is not None and unit:
            facts[fact_id] = {
                "value": value,
                "unit": unit,
                "as_of": payload["as_of"],
                "data_origin": payload["data_origin"],
            }
    return facts


def build_toolset(port: GovernedToolPort, principal: Principal) -> list[PortTool]:
    return [PortTool(port, principal, spec) for spec in port.list_tools(principal)]
