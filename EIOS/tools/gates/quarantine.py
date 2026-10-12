"""Gate quarantine (FR-012): named owner and expiry required; expired entries fail the run."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator

from eios.common.errors import ConfigError
from eios.common.validation import StrictModel
from tools.gates._config_loading import ensure_unique, load_entries

NonBlank = Annotated[str, Field(min_length=1)]


class QuarantineEntry(StrictModel):
    """A quarantined gate. The entry is valid through its ``expires`` date, inclusive."""

    gate_id: NonBlank
    owner: NonBlank
    expires: date
    reason: NonBlank

    @field_validator("owner", "reason", "gate_id")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


def load_quarantine(
    path: Path, known_gate_ids: frozenset[str] | None = None
) -> tuple[QuarantineEntry, ...]:
    """Load ``config/quarantine.yaml``; a missing or malformed file raises ConfigError."""
    entries = load_entries(path, QuarantineEntry)
    ensure_unique(str(path), [e.gate_id for e in entries], "quarantined gate")
    if known_gate_ids is not None:
        for index, entry in enumerate(entries):
            if entry.gate_id not in known_gate_ids:
                raise ConfigError(
                    str(path), f"[{index}].gate_id", f"unknown gate {entry.gate_id!r}"
                )
    return entries


def partition(
    entries: Sequence[QuarantineEntry], today: date
) -> tuple[tuple[QuarantineEntry, ...], tuple[QuarantineEntry, ...]]:
    """Split into (active, expired) as of ``today``; input order is kept."""
    active = tuple(e for e in entries if e.expires >= today)
    expired = tuple(e for e in entries if e.expires < today)
    return active, expired
