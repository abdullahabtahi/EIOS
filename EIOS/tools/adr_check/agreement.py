"""Agreement between the ADR index and the ADR files, including the supersession chain."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from tools.adr_check.validate import ADR_ID, text_of
from tools.common.findings import Finding
from tools.records.adr import AdrRecord
from tools.records.index import AdrIndexRow
from tools.records.markdown import extract_fields

_SUCCESSOR = re.compile(r"^Superseded by (ADR-\d{3})$")
_REQUIRES_FILE = ("Accepted", "Superseded")


@dataclass(frozen=True)
class LoadedAdr:
    """An ADR file as read: its record, repo-relative path and filename number."""

    record: AdrRecord
    source: str
    number: str
    supersedes: tuple[str, ...]

    @property
    def adr_id(self) -> str:
        return f"ADR-{self.number}"

    @property
    def status(self) -> str:
        return text_of(self.record.status)

    @property
    def successor(self) -> str | None:
        match = _SUCCESSOR.match(self.status)
        return match[1] if match else None


def supersedes_of(text: str) -> tuple[str, ...]:
    """ADR ids named by a ``Supersedes`` field (heading or label) in an ADR file."""
    value = extract_fields(text, {"supersedes": ("Supersedes",)})["supersedes"]
    return tuple(dict.fromkeys(ADR_ID.findall(text_of(value))))


def _normal(text: str) -> str:
    return " ".join(text.split()).casefold().rstrip(".")


def _f(source: str, rule: str, message: str) -> Finding:
    return Finding(source, 1, rule, message)


def _duplicates(
    rows: Sequence[AdrIndexRow], adrs: Sequence[LoadedAdr], index: str
) -> list[Finding]:
    findings = [
        _f(index, "adr.index.duplicate_number", f"{adr_id} appears {count} times in the index")
        for adr_id, count in Counter(row.adr_id for row in rows).items()
        if count > 1
    ]
    by_number: dict[str, list[str]] = {}
    for adr in adrs:
        by_number.setdefault(adr.number, []).append(adr.source)
    for number, sources in by_number.items():
        findings.extend(
            _f(source, "adr.index.duplicate_number", f"ADR-{number} has {len(sources)} files")
            for source in sources[1:]
        )
    return findings


def _row_findings(row: AdrIndexRow, adr: LoadedAdr | None, index: str) -> list[Finding]:
    status = row.status.strip()
    if adr is None:
        if status.startswith(_REQUIRES_FILE):
            message = f"{row.adr_id} is {status} in the index but has no file in docs/adr/"
            return [_f(index, "adr.index.missing_file", message)]
        return []
    findings: list[Finding] = []
    if _normal(row.decision) != _normal(text_of(adr.record.title)):
        message = f"{row.adr_id}: index title {row.decision!r} differs from the file title"
        findings.append(_f(adr.source, "adr.index.title_mismatch", message))
    if adr.status and _normal(status) != _normal(adr.status):
        message = f"{row.adr_id}: index status {status!r} differs from file status {adr.status!r}"
        findings.append(_f(adr.source, "adr.index.status_mismatch", message))
    return findings


def _chain_findings(adrs: Sequence[LoadedAdr]) -> list[Finding]:
    by_id = {adr.adr_id: adr for adr in adrs}
    findings: list[Finding] = []
    for adr in adrs:
        successor = adr.successor
        if successor is not None:
            findings += _forward(adr, by_id.get(successor), successor)
        for target in adr.supersedes:
            findings += _backward(adr, by_id.get(target), target)
    return findings


def _forward(adr: LoadedAdr, successor: LoadedAdr | None, successor_id: str) -> list[Finding]:
    if successor is None:
        message = f"{adr.adr_id} is superseded by {successor_id}, which has no file"
        return [_f(adr.source, "adr.supersession.missing_successor", message)]
    if adr.adr_id in successor.supersedes:
        return []
    message = f"{adr.adr_id} names {successor_id} as successor, but {successor_id} does not name it"
    return [_f(adr.source, "adr.supersession.one_way", message)]


def _backward(adr: LoadedAdr, target: LoadedAdr | None, target_id: str) -> list[Finding]:
    if target is None:
        message = f"{adr.adr_id} supersedes {target_id}, which has no file"
        return [_f(adr.source, "adr.supersession.unknown_target", message)]
    if target.successor == adr.adr_id:
        return []
    message = f"{adr.adr_id} supersedes {target_id}, but {target_id} does not name it as successor"
    return [_f(adr.source, "adr.supersession.one_way", message)]


def check_agreement(
    rows: Sequence[AdrIndexRow], adrs: Sequence[LoadedAdr], index_source: str
) -> list[Finding]:
    """Findings for index/file disagreement and broken supersession chains."""
    files = {adr.adr_id: adr for adr in reversed(adrs)}
    findings = _duplicates(rows, adrs, index_source)
    listed = {row.adr_id for row in rows}
    for row in rows:
        findings += _row_findings(row, files.get(row.adr_id), index_source)
    findings += [
        _f(adr.source, "adr.index.missing_entry", f"{adr.adr_id} has a file but no index entry")
        for adr in adrs
        if adr.adr_id not in listed
    ]
    return findings + _chain_findings(adrs)
