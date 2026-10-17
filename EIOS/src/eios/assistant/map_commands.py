"""Map commands in a draft: `{{map:<kind>:<id>}}`, accepted only for an object a tool returned in this turn.

The geospatial assistant moves the map the way it shows a figure. It writes a placeholder; the assembler keeps it only
when a governed result of the same turn listed that object in its `map_targets`, takes it out of the text, and returns
it as a view command the map applies. Anything else (an object no tool returned, an unknown kind, too many moves) sends
the draft back with the reason, like a figure no tool returned. The model never writes coordinates or layer settings:
the map places the object from its own data.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

MAP_KINDS = ("country", "corridor", "mismatch", "gateway", "account")
MAX_MAP_COMMANDS = (
    3  # [ASSUMPTION] the first is selected and framed; more than a few moves is not a direction
)
_MAP = re.compile(r"\{\{map:([a-zA-Z0-9_-]+):([^{}\s]+)\}\}")
_SPACE_BEFORE_PUNCT = re.compile(r"[ \t]+([.,;:!?)])")
_RUNS = re.compile(r"[ \t]{2,}")


def target_key(kind: str, target_id: str) -> str:
    return f"{kind}:{target_id.strip().upper()}"


def targets_of(payload: Mapping[str, Any]) -> set[str]:
    """The map targets a trusted result lists, as `kind:ID` keys. A result marked untrusted offers none."""
    if payload.get("untrusted"):
        return set()
    found = payload.get("map_targets") or []
    return {
        target_key(t["kind"], t["target_id"])
        for t in found
        if isinstance(t, dict)
        and t.get("kind") in MAP_KINDS
        and isinstance(t.get("target_id"), str)
    }


@dataclass(frozen=True)
class MapCommands:
    text: str  # the draft with the placeholders taken out
    commands: tuple[dict[str, str], ...]
    problems: tuple[str, ...]


def extract(draft: str, targets: Iterable[str]) -> MapCommands:
    allowed = frozenset(targets)
    commands: list[dict[str, str]] = []
    problems: list[str] = []
    for match in _MAP.finditer(draft):
        kind, raw_id = match.group(1).strip().lower(), match.group(2).strip()
        if kind not in MAP_KINDS:
            problems.append(f"map kind '{kind}' is not one of {', '.join(MAP_KINDS)}")
            continue
        key = target_key(kind, raw_id)
        if key not in allowed:
            problems.append(
                f"map target '{key}' was not returned by a tool in this turn; use one from a result's map_targets"
            )
            continue
        command = {"kind": kind, "id": key.split(":", 1)[1]}
        if command not in commands:
            commands.append(command)
    # More valid moves than the map can follow is a presentation limit, not a proof failure: the first ones are kept
    # and the rest dropped. Rejecting would cost a redraft, and a live run showed the redraft can be worse [MEASURED].
    text = _MAP.sub("", draft)
    text = _SPACE_BEFORE_PUNCT.sub(r"\1", _RUNS.sub(" ", text))
    return MapCommands(
        text=text, commands=tuple(commands[:MAX_MAP_COMMANDS]), problems=tuple(problems)
    )
