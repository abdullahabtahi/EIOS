"""Read-only parser for an ADR file (`docs/adr/NNN-title.md`); no validation rules."""

import re
from dataclasses import dataclass

from tools.records.markdown import ABSENT, FieldValue, extract_fields, first_h1

_ALIASES: dict[str, tuple[str, ...]] = {
    "status": ("Status",),
    "date": ("Date",),
    "context": ("Context",),
    "options": ("Options considered", "Options"),
    "decision": ("Decision",),
    "consequences": ("Consequences",),
    "evidence": ("Evidence",),
    "revisit_when": ("Revisit when", "Revisit"),
}
_HEADING = re.compile(r"^(?P<id>ADR-\d+)\s*:\s*(?P<title>.*)$")


@dataclass(frozen=True)
class AdrRecord:
    """An ADR as written. Every field is text as found, or ``ABSENT`` when not present."""

    source: str
    adr_id: FieldValue
    title: FieldValue
    status: FieldValue
    date: FieldValue
    context: FieldValue
    options: FieldValue
    decision: FieldValue
    consequences: FieldValue
    evidence: FieldValue
    revisit_when: FieldValue


def parse_adr(text: str, source: str) -> AdrRecord:
    """Parse ``text`` (read from ``source``) into an ``AdrRecord`` without judging content."""
    fields = extract_fields(text, _ALIASES)
    heading = first_h1(text)
    adr_id: FieldValue = ABSENT
    title: FieldValue = heading
    if isinstance(heading, str):
        match = _HEADING.match(heading)
        if match:
            adr_id, title = match["id"], match["title"]
    return AdrRecord(
        source=source,
        adr_id=adr_id,
        title=title,
        status=fields["status"],
        date=fields["date"],
        context=fields["context"],
        options=fields["options"],
        decision=fields["decision"],
        consequences=fields["consequences"],
        evidence=fields["evidence"],
        revisit_when=fields["revisit_when"],
    )
