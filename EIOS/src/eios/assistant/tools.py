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
FACT_IDS_KEY = "temp:fact_ids"
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
        state[FACT_IDS_KEY] = [*state.get(FACT_IDS_KEY, []), *payload.get("fact_ids", {}).values()]
        state[SOURCES_KEY] = [*state.get(SOURCES_KEY, []), payload["source"]]
        state[ORIGINS_KEY] = [*state.get(ORIGINS_KEY, []), payload["data_origin"]]
        if self._spec.kind == _PROPOSAL_KIND:
            state[PROPOSALS_KEY] = [*state.get(PROPOSALS_KEY, []), payload]
        return payload


def build_toolset(port: GovernedToolPort, principal: Principal) -> list[PortTool]:
    return [PortTool(port, principal, spec) for spec in port.list_tools(principal)]
