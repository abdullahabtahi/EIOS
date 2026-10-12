"""Current state of the spikes, ADRs and features a feature may depend on (read-only)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from eios.common.errors import ConfigError
from tools.common.yaml_io import load_validated
from tools.records.index import DEFAULT_SOURCE, parse_adr_index, parse_spike_index
from tools.records.spike import parse_spike

NOT_FOUND = "not found"
REGISTER_PATH = "docs/feature_register.yaml"
SPIKE_RECORD_GLOB = "docs/adr/S-[0-9][0-9]-*.md"

_REGISTER_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["features"],
    "properties": {
        "features": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "name", "complete"],
                "properties": {
                    "id": {"type": "string", "pattern": "^F[0-9]{2}$"},
                    "name": {"type": "string", "minLength": 1},
                    "complete": {"type": "boolean"},
                },
            },
        }
    },
}


def _read_index(repo_root: Path) -> str:
    try:
        return (repo_root / DEFAULT_SOURCE).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ConfigError(
            DEFAULT_SOURCE, "$", f"cannot read the spike and ADR index: {exc}"
        ) from exc


def adr_statuses(repo_root: Path) -> dict[str, str]:
    """ADR id -> status as the index shows it."""
    rows = parse_adr_index(_read_index(repo_root), DEFAULT_SOURCE)
    return {row.adr_id: row.status for row in rows}


def _record_states(repo_root: Path) -> dict[str, str]:
    """Spike id -> ``open``/``closed`` (as written, lower-cased) from the spike record files."""
    states: dict[str, str] = {}
    for path in sorted(repo_root.glob(SPIKE_RECORD_GLOB)):
        relative = path.relative_to(repo_root).as_posix()
        try:
            record = parse_spike(path.read_text(encoding="utf-8"), relative)
        except (OSError, UnicodeDecodeError) as exc:
            raise ConfigError(relative, "$", f"cannot read spike record: {exc}") from exc
        if isinstance(record.spike_id, str) and isinstance(record.state, str):
            states[record.spike_id] = record.state.strip().lower()
    return states


def spike_states(repo_root: Path) -> dict[str, str]:
    """Spike id -> state; a spike in the index with no record file is ``open``."""
    index_rows = parse_spike_index(_read_index(repo_root), DEFAULT_SOURCE)
    states = {row.spike_id: "open" for row in index_rows}
    states.update(_record_states(repo_root))
    return states


def feature_completeness(repo_root: Path) -> dict[str, bool]:
    """Feature id -> ``complete`` flag from the feature register."""
    data = load_validated(repo_root / REGISTER_PATH, _REGISTER_SCHEMA)
    entries = cast("dict[str, Any]", data)["features"]  # shape fixed by the schema
    return {str(entry["id"]): bool(entry["complete"]) for entry in entries}
