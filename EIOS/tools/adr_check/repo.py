"""Load the ADR index, ADR files and spike files of a repository and run every check."""

from __future__ import annotations

import re
from pathlib import Path

from eios.common.errors import ConfigError
from tools.adr_check.agreement import LoadedAdr, check_agreement, supersedes_of
from tools.adr_check.validate import validate_adr, validate_spike
from tools.common.findings import Finding
from tools.records.adr import parse_adr
from tools.records.index import DEFAULT_SOURCE, parse_adr_index
from tools.records.spike import parse_spike

ADR_DIR = "docs/adr"
TEMPLATE_PREFIX = "_template-"
_ADR_FILE = re.compile(r"^(?P<number>\d{3})-[a-z0-9][a-z0-9-]*\.md$")
_SPIKE_FILE = re.compile(r"^(?P<number>S-\d{2})-[a-z0-9][a-z0-9-]*\.md$")


def _read(path: Path, relative: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ConfigError(relative, "$", f"cannot read file: {exc}") from exc


def _record_files(repo_root: Path) -> list[Path]:
    directory = repo_root / ADR_DIR
    if not directory.is_dir():
        return []
    return sorted(
        p for p in directory.glob("*.md") if p.is_file() and not p.name.startswith(TEMPLATE_PREFIX)
    )


def _load(repo_root: Path) -> tuple[list[LoadedAdr], list[Finding], list[Path]]:
    adrs: list[LoadedAdr] = []
    findings: list[Finding] = []
    spikes: list[Path] = []
    for path in _record_files(repo_root):
        relative = f"{ADR_DIR}/{path.name}"
        match = _ADR_FILE.match(path.name)
        if match:
            text = _read(path, relative)
            record = parse_adr(text, relative)
            adrs.append(LoadedAdr(record, relative, match["number"], supersedes_of(text)))
        elif path.name.startswith("S-"):
            spikes.append(path)
        elif path.name[:1].isdigit():
            message = "ADR filename must be NNN-title.md (three digits, kebab-case)"
            findings.append(Finding(relative, 1, "adr.filename", message))
    return adrs, findings, spikes


def _spike_findings(
    repo_root: Path, spikes: list[Path], adr_status: dict[str, str]
) -> list[Finding]:
    findings: list[Finding] = []
    for path in spikes:
        relative = f"{ADR_DIR}/{path.name}"
        match = _SPIKE_FILE.match(path.name)
        if match is None:
            message = "Spike filename must be S-NN-title.md"
            findings.append(Finding(relative, 1, "spike.filename", message))
            continue
        record = parse_spike(_read(path, relative), relative)
        findings += validate_spike(record, relative, match["number"], adr_status)
    return findings


def check_repo(repo_root: Path) -> list[Finding]:
    """Validate every ADR and spike file and the index agreement under ``repo_root``."""
    rows = parse_adr_index(_read(repo_root / DEFAULT_SOURCE, DEFAULT_SOURCE), DEFAULT_SOURCE)
    adrs, findings, spikes = _load(repo_root)
    for adr in adrs:
        findings += validate_adr(adr.record, adr.source, adr.number)
    adr_status = {row.adr_id: row.status.strip() for row in rows}
    findings += _spike_findings(repo_root, spikes, adr_status)
    return findings + check_agreement(rows, adrs, DEFAULT_SOURCE)
