"""Service documentation check (FR-039): each service ships an SLO, runbook and warm-start note.

A service is a subdirectory of ``services/`` whose name does not start with ``_`` or ``.``
(so ``__pycache__`` and shared-code packages are skipped). Each service must hold non-empty
``slo.md``, ``runbook.md`` and ``warm_start.md`` with the structure checked below.
"""

from __future__ import annotations

import re
from pathlib import Path

from eios.common.errors import ToolError
from eios.common.provenance import Tag
from tools.common.findings import Finding

SERVICES_DIR = "services"
SLO_FIELDS = ("indicator", "objective", "owner feature", "status")
SLO_STATUSES = frozenset({"placeholder", "active"})
RUNBOOK_SECTIONS = ("symptoms", "first checks", "escalation", "rollback")
_RULE = "repo.service_docs"
_SKIPPED_PREFIXES = ("_", ".")
_MARKUP = str.maketrans("", "", "*_`")
_HEADING = re.compile(r"^#{1,6}\s+(.*?)\s*#*\s*$")
_STATE = re.compile(r"holds in-memory state\s*:\s*(yes|no)\b", re.IGNORECASE)
_WARM_UP_LINE = re.compile(r"warm-up behaviou?r\s*:\s*(.*)$", re.IGNORECASE)
_WARM_UP_HEADING = re.compile(r"warm-up behaviou?r", re.IGNORECASE)
_FIGURE = re.compile(r"\d")


def _finding(service: str, name: str, rule: str, message: str) -> Finding:
    return Finding(f"{SERVICES_DIR}/{service}/{name}", 1, f"{_RULE}.{rule}", message)


def _plain(line: str) -> str:
    """A line without list bullets and emphasis markers, so ``- **Status:** x`` reads as text."""
    return line.strip().lstrip("-+ ").translate(_MARKUP).strip()


def _fields(text: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for line in text.splitlines():
        name, sep, value = _plain(line).partition(":")
        if sep and name.strip().lower() in SLO_FIELDS:
            found.setdefault(name.strip().lower(), value.strip())
    return found


def _check_slo(service: str, text: str) -> list[Finding]:
    fields = _fields(text)
    findings = [
        _finding(service, "slo.md", "slo_field", f"service {service}: slo.md lacks a value for {f}")
        for f in SLO_FIELDS
        if not fields.get(f)
    ]
    status = fields.get("status", "").lower()
    if status and status not in SLO_STATUSES:
        allowed = ", ".join(sorted(SLO_STATUSES))
        msg = f"service {service}: slo.md status {status!r} is not one of {allowed}"
        findings.append(_finding(service, "slo.md", "slo_status", msg))
    objective = fields.get("objective", "")
    if _FIGURE.search(objective) and not any(tag.value in objective for tag in Tag):
        msg = f"service {service}: slo.md objective holds a figure without a provenance tag"
        findings.append(_finding(service, "slo.md", "slo_untagged_figure", msg))
    return findings


def _sections(text: str) -> dict[str, str]:
    """Heading text (lower case) to the body beneath it, up to the next heading."""
    sections: dict[str, list[str]] = {}
    current: list[str] | None = None
    for line in text.splitlines():
        heading = _HEADING.match(line)
        if heading:
            current = sections.setdefault(heading.group(1).translate(_MARKUP).strip().lower(), [])
        elif current is not None:
            current.append(line)
    return {name: "\n".join(body).strip() for name, body in sections.items()}


def _check_runbook(service: str, text: str) -> list[Finding]:
    sections = _sections(text)
    return [
        _finding(
            service,
            "runbook.md",
            "runbook_section",
            f"service {service}: runbook.md lacks a non-empty '{name}' section",
        )
        for name in RUNBOOK_SECTIONS
        if not sections.get(name)
    ]


def _has_warm_up(text: str) -> bool:
    for line in text.splitlines():
        match = _WARM_UP_LINE.search(_plain(line))
        if match and match.group(1).strip():
            return True
    return any(body and _WARM_UP_HEADING.fullmatch(name) for name, body in _sections(text).items())


def _check_warm_start(service: str, text: str) -> list[Finding]:
    state = _STATE.search(text.translate(_MARKUP))
    if state is None:
        msg = f"service {service}: warm_start.md must state 'holds in-memory state: yes' or 'no'"
        return [_finding(service, "warm_start.md", "warm_state", msg)]
    if state.group(1).lower() == "yes" and not _has_warm_up(text):
        msg = f"service {service}: warm_start.md says state is held but gives no warm-up behaviour"
        return [_finding(service, "warm_start.md", "warm_up", msg)]
    return []


_CHECKS = {
    "slo.md": _check_slo,
    "runbook.md": _check_runbook,
    "warm_start.md": _check_warm_start,
}


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ToolError(f"cannot read {path}: {exc}") from exc


def _check_service(directory: Path) -> list[Finding]:
    service = directory.name
    findings: list[Finding] = []
    for name, check in _CHECKS.items():
        path = directory / name
        if not path.is_file():
            msg = f"service {service}: {name} is missing"
            findings.append(_finding(service, name, "missing_file", msg))
            continue
        text = _read(path)
        if not text.strip():
            findings.append(
                _finding(service, name, "empty_file", f"service {service}: {name} is empty")
            )
            continue
        findings.extend(check(service, text))
    return findings


def check_service_docs(repo_root: Path) -> tuple[Finding, ...]:
    """Findings for every service directory under ``repo_root/services``, sorted by service."""
    services = repo_root.resolve() / SERVICES_DIR
    if not services.is_dir():
        return ()
    findings: list[Finding] = []
    for directory in sorted(services.iterdir()):
        if directory.is_dir() and not directory.name.startswith(_SKIPPED_PREFIXES):
            findings.extend(_check_service(directory))
    return tuple(findings)
