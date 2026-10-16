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
    r"(?P<cap>[a-z_]+\.[a-z_]+):(?P<scope>[A-Za-z0-9@_.>-]{1,64}):"
    r"(?P<path>[a-z0-9_]{1,64}(?:\[\d{1,3}\])?(?:\.[a-z0-9_]{1,64}(?:\[\d{1,3}\])?){0,4})"
)
_SEGMENT = re.compile(r"([a-z0-9_]+)(?:\[(\d+)\])?")
_INDEX = re.compile(r"\[\d+\]")
# A geo result's scope is the id it was asked about; this is the argument that asks for it again.
_GEO_SCOPE_ARGUMENT = {
    "geo.exit": "gateway_id",
    "geo.corridor": "corridor_id",
    "geo.account": "entity_id",
    "geo.jurisdiction": "country_id",
    "geo.leads": "kind",
    "geo.list_change": "list_id",
}


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
    if capability in _GEO_SCOPE_ARGUMENT:
        return {_GEO_SCOPE_ARGUMENT[capability]: scope}
    return {} if scope == "-" else {"entity_id": scope}


def _at(payload: Any, path: str) -> Any:
    """The value a dotted path names, with `[n]` for the n-th item of a list; None when the path leads nowhere."""
    node = payload
    for part in path.split("."):
        match = _SEGMENT.fullmatch(part)
        if match is None or not isinstance(node, dict):
            return None
        node = node.get(match[1])
        if match[2] is not None:
            index = int(match[2])
            node = node[index] if isinstance(node, list) and index < len(node) else None
    return node


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
        value = _at(payload, path)
        # Units name list items by template: `countries[].sessions`.
        template = _INDEX.sub("[]", path)
        if (
            isinstance(value, bool)
            or not isinstance(value, int | float)
            or template not in payload["units"]
        ):
            raise PortError(ToolErrorCode.NOT_FOUND, f"'{path}' is not a figure of {capability}")
        return ResolvedFact(
            fact_id=fact_id,
            value=float(value),
            unit=payload["units"][template],
            as_of=payload["as_of"],
            data_origin=payload["data_origin"],
            markings=tuple(payload["markings"]),
        )
