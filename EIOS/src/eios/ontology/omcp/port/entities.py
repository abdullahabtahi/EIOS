"""Canonical entity identity (spec 023 FR-011): known aliases resolve once, unknown ids are not found.

The canonical sets come from the same services the workstations render, so a partner on the radar is a
partner the assistant can name, and nothing else is.
"""

import re
from enum import StrEnum
from functools import cache
from pathlib import Path

import yaml

from eios.common.validation import StrictModel
from eios.ontology.omcp.port.contracts import PortError, ToolErrorCode

_ID = re.compile(r"[A-Z0-9][A-Z0-9_-]{1,31}")
_ALIASES_PATH = Path(__file__).with_name("aliases.yaml")


class EntityKind(StrEnum):
    PARTNER = "partner"
    ACCOUNT = "account"


class Entity(StrictModel):
    entity_id: str
    kind: EntityKind


def validate_aliases(
    canonical: dict[str, EntityKind], aliases: dict[str, list[str]]
) -> dict[str, str]:
    """The alias to canonical map, or a `ValueError` naming the offending alias."""
    resolved: dict[str, str] = {}
    for target, names in aliases.items():
        if target not in canonical:
            raise ValueError(f"alias target {target} is not a canonical entity")
        for name in names:
            key = name.strip().upper()
            if key in canonical:
                raise ValueError(f"alias {key} shadows the canonical id {key}")
            if resolved.get(key, target) != target:
                raise ValueError(f"alias {key} maps to both {resolved[key]} and {target}")
            resolved[key] = target
    return resolved


class EntityDirectory:
    def __init__(self, canonical: dict[str, EntityKind], aliases: dict[str, list[str]]) -> None:
        self._canonical = dict(canonical)
        self._aliases = validate_aliases(canonical, aliases)

    def resolve(self, raw: str, kind: EntityKind | None = None) -> Entity:
        text = raw.strip().upper() if isinstance(raw, str) else ""
        if not _ID.fullmatch(text):
            raise PortError(
                ToolErrorCode.INVALID_ARGUMENTS, "an entity id is required, not free text"
            )
        entity_id = self._aliases.get(text, text)
        found = self._canonical.get(entity_id)
        if found is None or (kind is not None and found is not kind):
            raise PortError(
                ToolErrorCode.NOT_FOUND, f"no {kind.value if kind else 'entity'} '{text}'"
            )
        return Entity(entity_id=entity_id, kind=found)


@cache
def default_directory() -> EntityDirectory:
    from eios.cockpit.aml import AMLWorkstationService
    from eios.cockpit.partner import PartnerWorkstationService

    canonical: dict[str, EntityKind] = {
        p.partner_id: EntityKind.PARTNER
        for p in PartnerWorkstationService().get_churn_radar_scatter().partners
    }
    canonical.update(
        {
            a["entity_id"]: EntityKind.ACCOUNT
            for a in AMLWorkstationService().get_triage_queue(0, 100)
        }
    )
    aliases = yaml.safe_load(_ALIASES_PATH.read_text(encoding="utf-8"))["partner"]
    return EntityDirectory(canonical, aliases)
