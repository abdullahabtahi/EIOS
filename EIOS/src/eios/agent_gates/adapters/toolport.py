"""A reference runtime over the governed tool port, for judging the port through the agent port (spec 023).

It is not the agent (that is spec 021). It routes a question to tools by explicit rules, offers itself only the
tools its verified workstation is given, calls them through the real port, and answers with figures copied from the
results. Judged by the 022 golden cases and attacks, it shows what the port makes answerable, what it makes
impossible, and that the answer agrees with the screen. Identity is the verified operator, never the question.
"""

import time
from dataclasses import replace
from typing import Any

from eios.agent_gates.adapters.offline_regulations import offline_index
from eios.agent_gates.adapters.toolport_render import (
    REFUSAL,
    render_error,
    render_result,
    source_line,
)
from eios.agent_gates.adapters.toolport_routes import Found, extract, plan
from eios.agent_gates.port import TurnRequest, completed_record
from eios.agent_gates.records import DataOrigin, IdentitySource, ToolCall, ToolErrorCode, TurnRecord
from eios.ontology.omcp.port.catalogue import build_port
from eios.ontology.omcp.port.contracts import PortError
from eios.ontology.omcp.port.principal import principal_for
from eios.ontology.omcp.port.readmodels import ReadModels
from eios.ontology.omcp.port.service import GovernedToolPort

UNTRUSTED_FLAG = "untrusted"


def _title(tool: str) -> str:
    return tool.replace("_", " ").capitalize()


class ToolPortRuntime:
    runtime_name = "toolport"
    offline = True

    def __init__(self, port: GovernedToolPort | None = None) -> None:
        # The reference run still exercises retrieval, on labelled test passages (never the acquired corpus).
        self._port = port or build_port(replace(ReadModels.default(), knowledge=offline_index()))

    def run_turn(self, request: TurnRequest) -> TurnRecord:
        started = time.perf_counter()
        try:
            principal = principal_for(request.operator_id, request.role.value)
        except PortError as exc:
            return completed_record(
                request,
                self.runtime_name,
                f"{REFUSAL} ({exc.error.message})",
                identity_source=IdentitySource.VERIFIED_TOKEN,
            )
        offered = {spec.name for spec in self._port.list_tools(principal)}
        found = extract(request.question, request.entity_context)
        calls: list[ToolCall] = []
        lines: list[str] = []
        sources: list[str] = []
        for tool, args_fn in plan(request.question):
            arguments = args_fn(found)
            if tool not in offered or arguments is None:
                continue  # never offered, so never attempted; or the question named nothing to look up
            outcome = self._port.call(principal, tool, arguments)
            payload = self._payload(outcome, request.tool_fixtures)
            spec = self._port.spec_for_capability_of(tool)
            calls.append(self._record(tool, spec.capability, arguments, payload, outcome))
            found.results[tool] = payload
            if outcome.error is None:
                lines += render_result(_title(tool), payload)
                sources.append(source_line(payload))
            else:
                lines.append(render_error(_title(tool), payload["error"]))
        answer = "\n".join([*lines, *dict.fromkeys(sources)]) if lines else REFUSAL
        return completed_record(
            request,
            self.runtime_name,
            answer,
            calls,
            identity_source=IdentitySource.VERIFIED_TOKEN,
            data_origin=DataOrigin.FIXTURE,
            latency_ms=(time.perf_counter() - started) * 1000,
        )

    @staticmethod
    def _payload(outcome: Any, fixtures: dict[str, dict[str, Any]]) -> dict[str, Any]:
        payload = outcome.payload()
        overlay = fixtures.get(payload.get("capability", ""))
        return {**payload, **overlay} if overlay else payload

    @staticmethod
    def _record(
        tool: str, capability: str, arguments: dict[str, Any], payload: dict[str, Any], outcome: Any
    ) -> ToolCall:
        error = ToolErrorCode(outcome.error.code.value) if outcome.error is not None else None
        return ToolCall(
            name=tool,
            capability=capability,
            arguments=arguments,
            result=None if error else payload,
            error=error,
            untrusted=bool(payload.get(UNTRUSTED_FLAG)),
        )


__all__ = ["Found", "ToolPortRuntime"]
