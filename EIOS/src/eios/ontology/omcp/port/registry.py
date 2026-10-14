"""A capability's declaration: name, who may call it, typed inputs and outputs, latency budget."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from eios.common.validation import StrictModel
from eios.ontology.config import SecurityMarking
from eios.ontology.omcp.port.contracts import ToolResult
from eios.ontology.omcp.port.principal import Workstation

KINDS = frozenset({"evidence", "compute", "draft", "propose", "knowledge"})


@dataclass(frozen=True)
class ToolSpec:
    name: str
    capability: str
    kind: str
    workstations: tuple[Workstation, ...]
    args_model: type[StrictModel]
    result_model: type[ToolResult]
    handler: Callable[[Any, Any], ToolResult]
    budget_ms: float
    markings: tuple[SecurityMarking, ...] = ()
    description: str = ""

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise ValueError(f"unknown kind '{self.kind}' for {self.name}")
        if not self.workstations:
            raise ValueError(f"{self.name} is offered to no workstation")
