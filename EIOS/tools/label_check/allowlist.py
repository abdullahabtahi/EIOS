"""Reviewed exceptions for label findings: ``config/label_allowlist.yaml``."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tools.common.yaml_io import load_validated

CONFIG_PATH = "config/label_allowlist.yaml"

_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["entries"],
    "properties": {
        "entries": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["path", "literal", "reason"],
                "properties": {
                    "path": {"type": "string", "minLength": 1},
                    "literal": {"type": "string", "minLength": 1},
                    "reason": {"type": "string", "pattern": r"\S"},
                },
            },
        }
    },
}


@dataclass(frozen=True, slots=True)
class AllowEntry:
    path: str
    literal: str
    reason: str

    def covers(self, file: str, line_text: str) -> bool:
        return file == self.path and self.literal in line_text


def load_allowlist(path: Path) -> tuple[AllowEntry, ...]:
    """A missing file means no exceptions; a blank reason is a ``ConfigError``."""
    if not path.is_file():
        return ()
    data = load_validated(path, _SCHEMA)
    assert isinstance(data, dict)  # noqa: S101
    return tuple(AllowEntry(e["path"], e["literal"], e["reason"]) for e in data["entries"])
