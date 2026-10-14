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
_NUMBER = re.compile(r"(?:(PARTNER|ACCOUNT)[\s#-]*)?(\d{2,10})")
_ALIASES_PATH = Path(__file__).with_name("aliases.yaml")


class EntityKind(StrEnum):
    PARTNER = "partner"
    ACCOUNT = "account"


_KIND_WORDS = {"PARTNER": EntityKind.PARTNER, "ACCOUNT": EntityKind.ACCOUNT}


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
        numbered = _NUMBER.fullmatch(text)
        if numbered:
            return self._by_number(text, numbered.group(2), numbered.group(1), kind)
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

    def _by_number(
        self, text: str, digits: str, word: str | None, kind: EntityKind | None
    ) -> Entity:
        """ "partner 882" or "882": the one entity whose number is that; none or several is not found."""
        wanted = _KIND_WORDS[word] if word else kind
        matches = [
            (entity_id, found)
            for entity_id, found in self._canonical.items()
            if re.sub(r"\D", "", entity_id).lstrip("0") == digits.lstrip("0")
            and (wanted is None or found is wanted)
            and (kind is None or found is kind)
        ]
        if len(matches) != 1:
            raise PortError(
                ToolErrorCode.NOT_FOUND, f"no {wanted.value if wanted else 'entity'} '{text}'"
            )
        return Entity(entity_id=matches[0][0], kind=matches[0][1])


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
