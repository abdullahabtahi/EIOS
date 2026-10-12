"""Read-only parsers for the spike table and ADR index in `docs/spikes_and_adrs.md`.

Statuses and ids are returned as found; checking them against the contract belongs to the
`adr_check` story, not here.
"""

import re
from dataclasses import dataclass

from eios.common.errors import ConfigError
from tools.records.markdown import find_section, parse_table, split_sections, strip_emphasis

DEFAULT_SOURCE = "docs/spikes_and_adrs.md"

_SPIKE_ID = re.compile(r"\bS-\d+\b")
_ADR_ID = re.compile(r"\bADR-\d+\b")
_ADR_COLUMNS = ("ADR", "Decision", "Status", "Default / current lean", "Depends on")
_SPIKE_COLUMNS = ("ID", "Question", "Why unverified", "Method", "Decision it unlocks", "Fallback")


@dataclass(frozen=True)
class AdrIndexRow:
    """One row of the ADR index table."""

    adr_id: str
    decision: str
    status: str
    default_or_current_lean: str
    depends_on: str
    depends_on_spikes: tuple[str, ...]


@dataclass(frozen=True)
class SpikeIndexRow:
    """One row of the spike table."""

    spike_id: str
    question: str
    why_unverified: str
    method: str
    unlocks: str
    fallback: str
    unlocks_adrs: tuple[str, ...]


def _ids(pattern: re.Pattern[str], text: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(pattern.findall(text)))


def _load_rows(
    text: str, source: str, section: str, columns: tuple[str, ...]
) -> tuple[dict[str, str], ...]:
    """Rows of the table in ``section`` with emphasis stripped; ConfigError if unreadable."""
    path = f"section '{section}'"
    found = find_section(split_sections(text), section)
    if found is None:
        raise ConfigError(source, path, "section not found")
    try:
        rows = parse_table(found.body)
    except ValueError as exc:
        raise ConfigError(source, path, f"malformed table: {exc}") from exc
    if not rows:
        raise ConfigError(source, path, "no table with rows found")
    missing = [column for column in columns if column not in rows[0]]
    if missing:
        raise ConfigError(source, path, f"table is missing columns: {', '.join(missing)}")
    return tuple({key: strip_emphasis(value) for key, value in row.items()} for row in rows)


def parse_adr_index(text: str, source: str = DEFAULT_SOURCE) -> tuple[AdrIndexRow, ...]:
    """Rows of the ``ADR index`` table, in file order."""
    rows = _load_rows(text, source, "ADR index", _ADR_COLUMNS)
    return tuple(
        AdrIndexRow(
            adr_id=row["ADR"],
            decision=row["Decision"],
            status=row["Status"],
            default_or_current_lean=row["Default / current lean"],
            depends_on=row["Depends on"],
            depends_on_spikes=_ids(_SPIKE_ID, row["Depends on"]),
        )
        for row in rows
    )


def parse_spike_index(text: str, source: str = DEFAULT_SOURCE) -> tuple[SpikeIndexRow, ...]:
    """Rows of the ``Spikes`` table, in file order."""
    rows = _load_rows(text, source, "Spikes", _SPIKE_COLUMNS)
    return tuple(
        SpikeIndexRow(
            spike_id=row["ID"],
            question=row["Question"],
            why_unverified=row["Why unverified"],
            method=row["Method"],
            unlocks=row["Decision it unlocks"],
            fallback=row["Fallback"],
            unlocks_adrs=_ids(_ADR_ID, row["Decision it unlocks"]),
        )
        for row in rows
    )
