"""Capability ids and the per-runtime tool map (spec 022 research R-5).

Golden and attack cases name capabilities, never tools, so they survive the tool catalogue changing in
spec 023. A capability the runtime lacks is reported as missing, never as a pass.
"""

from enum import StrEnum
from functools import cache
from pathlib import Path

import yaml

from eios.common.validation import StrictModel

# Handlers that exist in the governed tool server but must never be given to an agent (RL-2).
FORBIDDEN_AGENT_TOOLS = frozenset({"approve_action", "execute_action"})
_MAP_PATH = Path(__file__).with_name("capability_map.yaml")


class Availability(StrEnum):
    AVAILABLE = "available"
    CAPABILITY_MISSING = "capability_missing"
    FIXTURE_ONLY = "fixture_only"
    PLANNED = "planned"


class Capability(StrictModel):
    id: str
    kind: str
    copilot: str | None = None
    target: str | None = None
    copilot_fixture_only: bool = False
    planned: str | None = None


class CapabilityMap(StrictModel):
    capabilities: dict[str, Capability]
    roles: dict[str, list[str]]

    def capability_for_tool(self, runtime: str, tool: str) -> str | None:
        """The capability a runtime's tool serves, or None for an unknown tool."""
        for cap in self.capabilities.values():
            if self._tool_of(cap, runtime) == tool:
                return cap.id
        return None

    def tool_for_capability(self, runtime: str, capability: str) -> str | None:
        cap = self.capabilities.get(capability)
        return self._tool_of(cap, runtime) if cap else None

    def availability(self, runtime: str, capability: str) -> Availability:
        cap = self.capabilities[capability]
        if self._tool_of(cap, runtime) is None:
            return Availability.CAPABILITY_MISSING
        if runtime == "copilot":
            return Availability.FIXTURE_ONLY if cap.copilot_fixture_only else Availability.AVAILABLE
        return Availability.PLANNED if cap.planned else Availability.AVAILABLE

    @staticmethod
    def _tool_of(cap: Capability, runtime: str) -> str | None:
        return cap.copilot if runtime == "copilot" else cap.target


@cache
def default_map() -> CapabilityMap:
    raw = yaml.safe_load(_MAP_PATH.read_text(encoding="utf-8"))
    caps = {c["id"]: Capability.model_validate(c) for c in raw["capabilities"]}
    return CapabilityMap(capabilities=caps, roles=raw["roles"])
