"""Resolve a fact id back to its value through the port, so derived figures use only governed inputs.

A fact id is `<capability>:<scope>:<path>` as every result lists in `fact_ids`. The value is fetched again
through the same port with the caller's own principal, so role, markings and tracing apply to the inputs of a
calculation exactly as they do to any other call, and a model cannot supply a number of its own.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from eios.ontology.config import SecurityMarking
from eios.ontology.omcp.port.contracts import DataOrigin, PortError, ToolErrorCode
from eios.ontology.omcp.port.principal import Principal

_FACT_ID = re.compile(
    r"(?P<cap>[a-z_]+\.[a-z_]+):(?P<scope>[A-Za-z0-9@_.-]{1,64}):(?P<path>[a-z0-9_]{1,64})"
)


@dataclass(frozen=True)
class ResolvedFact:
    fact_id: str
    value: float
    unit: str
    as_of: datetime
    data_origin: DataOrigin
    markings: tuple[SecurityMarking, ...]


class _PortLike(Protocol):
    def call(self, principal: Principal, tool: str, arguments: dict[str, Any]) -> Any: ...
    def spec_for_capability(self, capability: str) -> Any: ...


def _args_for(capability: str, scope: str) -> dict[str, Any]:
    if capability == "metric.get":  # scope is `metric_id` or `metric_id@entity`
        metric, _, entity = scope.partition("@")
        return {"metric_id": metric, **({"entity_id": entity} if entity else {})}
    return {} if scope == "-" else {"entity_id": scope}


class FactResolver:
    def __init__(self) -> None:
        self._port: _PortLike | None = None

    def bind(self, port: _PortLike) -> None:
        self._port = port

    def resolve(self, principal: Principal, fact_id: str) -> ResolvedFact:
        match = _FACT_ID.fullmatch(fact_id) if isinstance(fact_id, str) else None
        if match is None or self._port is None:
            raise PortError(
                ToolErrorCode.INVALID_ARGUMENTS, "a fact id from an earlier result is required"
            )
        capability, scope, path = match["cap"], match["scope"], match["path"]
        spec = self._port.spec_for_capability(capability)
        if spec is None:
            raise PortError(ToolErrorCode.NOT_FOUND, f"no capability '{capability}'")
        outcome = self._port.call(principal, spec.name, _args_for(capability, scope))
        if outcome.error is not None:
            raise PortError(outcome.error.code, outcome.error.message)
        payload = outcome.result.model_dump(mode="python")
        value = payload.get(path)
        if (
            isinstance(value, bool)
            or not isinstance(value, int | float)
            or path not in payload["units"]
        ):
            raise PortError(ToolErrorCode.NOT_FOUND, f"'{path}' is not a figure of {capability}")
        return ResolvedFact(
            fact_id=fact_id,
            value=float(value),
            unit=payload["units"][path],
            as_of=payload["as_of"],
            data_origin=payload["data_origin"],
            markings=tuple(payload["markings"]),
        )
