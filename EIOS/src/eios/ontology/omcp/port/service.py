"""`GovernedToolPort`: the one way an agent reaches data (spec 023 FR-001 to FR-007).

`call` validates arguments, enforces the caller's workstation allow-list and markings before any handler
runs, validates the result against the declared contract, and records a trace of every call and a refusal
for every out-of-scope one. A tool that is not in the caller's toolset is refused the same way whether or
not it exists, so the response does not reveal the catalogue. Approve and execute are never registered.
"""

import logging
import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError

from eios.ontology.omcp.markings import SecurityMarkingEnforcer
from eios.ontology.omcp.port.contracts import PortError, ToolError, ToolErrorCode, ToolResult
from eios.ontology.omcp.port.principal import Principal, Workstation, enforcer_role
from eios.ontology.omcp.port.registry import ToolSpec

_LOG = logging.getLogger("eios.ontology.omcp.port")

MAX_RECORDED = 10_000  # bounded in memory; the durable trail is the ledger, not this list


@dataclass(frozen=True)
class Refusal:
    uid: str
    workstation: Workstation
    tool: str
    code: ToolErrorCode
    at: datetime


@dataclass(frozen=True)
class CallTrace:
    tool: str
    workstation: Workstation
    status: str
    duration_ms: float
    over_budget: bool = False


@dataclass
class RefusalLog:
    entries: list[Refusal] = field(default_factory=list)

    def record(self, refusal: Refusal) -> None:
        self.entries.append(refusal)
        del self.entries[:-MAX_RECORDED]
        _LOG.warning(
            "refused uid=%s workstation=%s tool=%s code=%s",
            refusal.uid,
            refusal.workstation.value,
            refusal.tool,
            refusal.code.value,
        )


@dataclass(frozen=True)
class CallOutcome:
    tool: str
    result: ToolResult | None = None
    error: ToolError | None = None

    def payload(self) -> dict[str, Any]:
        """The JSON form an agent sees: the result, or `{"error": {...}}`."""
        if self.result is not None:
            return self.result.model_dump(mode="json")
        return {"error": self.error.model_dump(mode="json") if self.error else None}


class GovernedToolPort:
    def __init__(
        self, specs: Iterable[ToolSpec], context: Any, refusals: RefusalLog | None = None
    ) -> None:
        self._specs: dict[str, ToolSpec] = {}
        for spec in specs:
            if spec.name in self._specs:
                raise ValueError(f"duplicate tool name '{spec.name}'")
            self._specs[spec.name] = spec
        self._context = context
        self.refusals = refusals or RefusalLog()
        self.traces: list[CallTrace] = []

    def spec_for_capability(self, capability: str) -> ToolSpec | None:
        return next((s for s in self._specs.values() if s.capability == capability), None)

    def spec_for_capability_of(self, tool: str) -> ToolSpec:
        """The spec of a tool the caller already holds (raises `KeyError` for an unknown tool)."""
        return self._specs[tool]

    def list_tools(self, principal: Principal) -> list[ToolSpec]:
        return [s for s in self._specs.values() if principal.workstation in s.workstations]

    def call(self, principal: Principal, tool: str, arguments: dict[str, Any]) -> CallOutcome:
        started = time.perf_counter()
        spec = self._specs.get(tool)
        if spec is None or principal.workstation not in spec.workstations:
            return self._refuse(
                principal,
                tool,
                ToolErrorCode.FORBIDDEN_ROLE,
                started,
                "this capability is not available to your workstation",
            )
        enforcer = SecurityMarkingEnforcer(enforcer_role(principal.workstation))
        if not all(enforcer.can_access(m) for m in spec.markings):
            return self._refuse(
                principal,
                tool,
                ToolErrorCode.FORBIDDEN_MARKING,
                started,
                "your workstation lacks clearance for this data class",
            )
        try:
            args = spec.args_model.model_validate(arguments)
        except ValidationError as exc:
            fields = ", ".join(
                sorted({str(e["loc"][0]) if e["loc"] else "arguments" for e in exc.errors()})
            )
            return self._finish(
                principal,
                spec,
                started,
                error=ToolError(
                    code=ToolErrorCode.INVALID_ARGUMENTS, message=f"invalid arguments: {fields}"
                ),
            )
        try:
            result = spec.handler(self._context, principal, args)
        except PortError as exc:
            return self._finish(principal, spec, started, error=exc.error)
        if not isinstance(result, spec.result_model):
            _LOG.error(
                "tool %s returned %s, expected %s",
                tool,
                type(result).__name__,
                spec.result_model.__name__,
            )
            return self._finish(
                principal,
                spec,
                started,
                error=ToolError(
                    code=ToolErrorCode.DATA_UNAVAILABLE,
                    message="the capability returned an invalid result",
                ),
            )
        return self._finish(principal, spec, started, result=result)

    def _refuse(
        self, principal: Principal, tool: str, code: ToolErrorCode, started: float, message: str
    ) -> CallOutcome:
        self.refusals.record(
            Refusal(principal.uid, principal.workstation, tool, code, datetime.now(UTC))
        )
        self.traces.append(CallTrace(tool, principal.workstation, code.value, _ms(started)))
        return CallOutcome(tool=tool, error=ToolError(code=code, message=message))

    def _finish(
        self,
        principal: Principal,
        spec: ToolSpec,
        started: float,
        result: ToolResult | None = None,
        error: ToolError | None = None,
    ) -> CallOutcome:
        elapsed = _ms(started)
        status = "ok" if error is None else error.code.value
        self.traces.append(
            CallTrace(spec.name, principal.workstation, status, elapsed, elapsed > spec.budget_ms)
        )
        del self.traces[:-MAX_RECORDED]
        return CallOutcome(tool=spec.name, result=result, error=error)


def _ms(started: float) -> float:
    return (time.perf_counter() - started) * 1000
