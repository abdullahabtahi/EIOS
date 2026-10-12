"""Field rules for one ADR file or one spike record, from `decision-and-spike-records.md`.

Parsing lives in `tools.records`; this module only judges the parsed text. HTML comments are
instructions in the templates and never count as content.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import date

from tools.common.findings import Finding
from tools.records.adr import AdrRecord
from tools.records.markdown import FieldValue
from tools.records.spike import SpikeRecord

ADR_STATUS = re.compile(r"^(?:Proposed|Accepted|Superseded by ADR-\d{3})$")
SPIKE_ID = re.compile(r"^S-\d{2}$")
ADR_ID = re.compile(r"\bADR-\d+\b")
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)]|[A-Za-z][.):])\s+\S", re.MULTILINE)
_INLINE_LETTER = re.compile(r"(?:^|\s)\(?([A-Za-z])\)\s+\S")
_MIN_OPTIONS = 2
_CLOSED_SPIKE_FIELDS = ("method", "data", "result", "decision", "outcome")


def text_of(value: FieldValue) -> str:
    """Field text with template comments removed; empty for an absent field."""
    return _COMMENT.sub("", value).strip() if isinstance(value, str) else ""


def _problem(source: str, prefix: str, name: str, value: FieldValue, label: str) -> Finding | None:
    """A finding when ``value`` is absent or blank, else None."""
    if text_of(value):
        return None
    state = "is empty" if isinstance(value, str) else "is missing"
    return Finding(source, 1, f"{prefix}.field.{name}", f"{label} {state}")


def _finding(source: str, rule: str, message: str) -> Finding:
    return Finding(source, 1, rule, message)


def _present(findings: list[Finding | None]) -> list[Finding]:
    return [f for f in findings if f is not None]


def option_count(text: str) -> int:
    """Number of options written as list items or inline ``A)`` / ``B)`` markers."""
    listed = len(_LIST_ITEM.findall(text))
    inline = len({letter.upper() for letter in _INLINE_LETTER.findall(text)})
    return max(listed, inline)


def _date_problem(source: str, prefix: str, value: FieldValue) -> Finding | None:
    missing = _problem(source, prefix, "date", value, "Date")
    if missing is not None:
        return missing
    text = text_of(value)
    try:
        valid = _ISO_DATE.match(text) is not None and date.fromisoformat(text) is not None
    except ValueError:
        valid = False
    if valid:
        return None
    return _finding(source, f"{prefix}.field.date", f"Date {text!r} is not an ISO YYYY-MM-DD date")


def _title_findings(record: AdrRecord, source: str, number: str) -> list[Finding]:
    adr_id = text_of(record.adr_id)
    if not adr_id or not text_of(record.title):
        return [_finding(source, "adr.field.title", "Title must read 'ADR-NNN: <text>'")]
    if adr_id != f"ADR-{number}":
        message = f"Title number {adr_id} does not match the filename number {number}"
        return [_finding(source, "adr.field.number", message)]
    return []


def _status_findings(record: AdrRecord, source: str) -> list[Finding]:
    status = text_of(record.status)
    if not status:
        return _present([_problem(source, "adr", "status", record.status, "Status")])
    if ADR_STATUS.match(status):
        return []
    message = f"Status {status!r} must be Proposed, Accepted or 'Superseded by ADR-XXX'"
    return [_finding(source, "adr.field.status", message)]


def _options_findings(record: AdrRecord, source: str) -> list[Finding]:
    missing = _problem(source, "adr", "options", record.options, "Options considered")
    if missing is not None:
        return [missing]
    if option_count(text_of(record.options)) >= _MIN_OPTIONS:
        return []
    return [_finding(source, "adr.field.options", "Options considered needs at least two options")]


def validate_adr(record: AdrRecord, source: str, number: str) -> list[Finding]:
    """Every field violation in one ADR file; ``number`` is the filename's NNN."""
    status = text_of(record.status)
    decided = status.startswith(("Accepted", "Superseded"))
    findings = [
        *_title_findings(record, source, number),
        *_status_findings(record, source),
        *_options_findings(record, source),
    ]
    required = [
        ("context", record.context, "Context", True),
        ("decision", record.decision, "Decision", decided),
        ("consequences", record.consequences, "Consequences", True),
        ("evidence", record.evidence, "Evidence", status == "Accepted"),
        ("revisit_when", record.revisit_when, "Revisit when", True),
    ]
    findings += _present(
        [_problem(source, "adr", n, v, label) for n, v, label, need in required if need]
    )
    findings += _present([_date_problem(source, "adr", record.date)])
    return findings


def _spike_id_findings(record: SpikeRecord, source: str, number: str) -> list[Finding]:
    spike_id = text_of(record.spike_id)
    if not SPIKE_ID.match(spike_id):
        return [_finding(source, "spike.field.id", f"Id {spike_id!r} must match S-NN")]
    if spike_id != number:
        return [
            _finding(source, "spike.field.id", f"Id {spike_id} does not match filename {number}")
        ]
    return []


def _linked_adr_findings(
    record: SpikeRecord, source: str, adr_status: Mapping[str, str]
) -> list[Finding]:
    missing = _problem(source, "spike", "linked_adr", record.linked_adr, "Linked ADR")
    if missing is not None:
        return [_finding(source, missing.rule_id, f"{missing.message}; a closed spike needs one")]
    ids = ADR_ID.findall(text_of(record.linked_adr))
    if not ids:
        return [_finding(source, "spike.field.linked_adr", "Linked ADR names no ADR-NNN id")]
    findings: list[Finding] = []
    for adr_id in dict.fromkeys(ids):
        status = adr_status.get(adr_id)
        if status is None:
            findings.append(
                _finding(source, "spike.link.adr_unknown", f"{adr_id} is not in the index")
            )
        elif status == "Open":
            findings.append(_finding(source, "spike.link.adr_open", f"{adr_id} is still Open"))
    return findings


def validate_spike(
    record: SpikeRecord, source: str, number: str, adr_status: Mapping[str, str]
) -> list[Finding]:
    """Every field violation in one spike file; ``adr_status`` maps ADR id to index status."""
    findings = _spike_id_findings(record, source, number)
    findings += _present(
        [
            _problem(source, "spike", "question", record.question, "Question"),
            _problem(source, "spike", "time_box", record.time_box, "Time box"),
            _problem(source, "spike", "owner", record.owner, "Owner"),
        ]
    )
    state = text_of(record.state).casefold()
    if state not in ("open", "closed"):
        return [*findings, _finding(source, "spike.field.state", "State must be open or closed")]
    if state == "open":
        return findings
    findings += _present(
        [
            _problem(source, "spike", name, getattr(record, name), name.capitalize())
            for name in _CLOSED_SPIKE_FIELDS
        ]
    )
    findings += _present([_date_problem(source, "spike", record.date)])
    return [*findings, *_linked_adr_findings(record, source, adr_status)]
