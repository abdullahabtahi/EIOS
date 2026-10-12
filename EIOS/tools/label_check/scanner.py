"""Provenance label scanner: per-unit rules and the repository walk."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from tools.common.findings import Finding
from tools.label_check.allowlist import CONFIG_PATH as ALLOWLIST_PATH
from tools.label_check.allowlist import AllowEntry, load_allowlist
from tools.label_check.citations import Citations
from tools.label_check.numeric import numeric_claim_kinds
from tools.label_check.origins import has_origin, origin_problems
from tools.label_check.rules import (
    ALLOWLIST_STALE,
    BRIEF_CITATION,
    CONFIG_PATH,
    FORBIDDEN,
    MULTIPLE_TAGS,
    SPIKE_REFERENCE,
    UNKNOWN_TAG,
    UNLABELLED,
    LabelRules,
    load_rules,
)
from tools.label_check.structured import scan_structured
from tools.label_check.units import iter_units
from tools.repo_checks._walk import iter_files, relative_posix
from tools.repo_checks.forbidden_literals import CONFIG_PATH as FORBIDDEN_PATH
from tools.repo_checks.forbidden_literals import load_patterns

__all__ = ["ScanResult", "numeric_claim_kinds", "scan_repo", "scan_text"]

_BRACKETED = re.compile(r"\[[A-Z][A-Z-]{3,}\](?!\()")


def _scan_unit(
    name: str, line: int, unit: str, rules: LabelRules, citations: Citations
) -> list[Finding]:
    tags = set(rules.tag_pattern.findall(unit))
    unknown = sorted(set(_BRACKETED.findall(unit)) - tags)
    kinds = numeric_claim_kinds(unit, rules)
    origin = has_origin(unit)
    out = [Finding(name, line, UNKNOWN_TAG, f"unknown provenance tag {tag}") for tag in unknown]
    out += [Finding(name, line, rule, message) for rule, message in origin_problems(unit)]
    if kinds and len(tags) >= 2:
        out.append(
            Finding(name, line, MULTIPLE_TAGS, "figure carries more than one provenance tag")
        )
    elif kinds and not tags and not origin:
        problem = citations.brief_problem(unit) if citations.has_brief_citation(unit) else None
        if problem:
            out.append(Finding(name, line, BRIEF_CITATION, problem))
        elif not citations.has_brief_citation(unit):
            out.append(Finding(name, line, UNLABELLED, "numeric claim has no provenance tag"))
    elif len(tags) == 1:
        out.extend(_evidence(name, line, unit, next(iter(tags)), rules, citations))
    return out


def _evidence(
    name: str, line: int, unit: str, tag: str, rules: LabelRules, citations: Citations
) -> list[Finding]:
    kind = rules.evidence[tag]
    if kind == "brief_citation":
        problem = citations.brief_problem(unit)
        return [Finding(name, line, BRIEF_CITATION, problem)] if problem else []
    if kind == "spike_id":
        return [Finding(name, line, SPIKE_REFERENCE, p) for p in citations.spike_problems(unit)]
    return []


def scan_text(name: str, text: str, rules: LabelRules, citations: Citations) -> tuple[Finding, ...]:
    """Findings for one document; messages never echo the offending figure."""
    findings: list[Finding] = []
    for line, unit in iter_units(text):
        findings.extend(_scan_unit(name, line, unit, rules, citations))
    return tuple(findings)


@dataclass(frozen=True)
class ScanResult:
    findings: tuple[Finding, ...]
    scanned: tuple[str, ...]
    excluded: tuple[str, ...]
    spike_states: dict[str, str]


def _glob_regex(pattern: str) -> re.Pattern[str]:
    out, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out, i = out + "(?:.*/)?", i + 3
        elif pattern.startswith("**", i):
            out, i = out + ".*", i + 2
        else:
            ch = pattern[i]
            out += {"*": "[^/]*", "?": "[^/]"}.get(ch, re.escape(ch))
            i += 1
    return re.compile(out)


def _in_scope(relative: str, rules: LabelRules) -> bool:
    if any(
        relative.startswith(e) if e.endswith("/") else _glob_regex(e).fullmatch(relative)
        for e in rules.exclude
    ):
        return False
    return any(_glob_regex(g).fullmatch(relative) for g in rules.include)


def _forbidden(root: Path, rel: str, text: str) -> list[Finding]:
    path = root / FORBIDDEN_PATH
    if not path.is_file():
        return []
    out = []
    for pattern in load_patterns(path):
        if pattern.allows(rel):
            continue
        for number, line in enumerate(text.split("\n"), start=1):
            if pattern.regex.search(line):
                out.append(Finding(rel, number, FORBIDDEN, f"{pattern.id}: {pattern.reason}"))
    return out


def _apply_allowlist(
    findings: list[Finding], lines: dict[str, list[str]], entries: tuple[AllowEntry, ...]
) -> list[Finding]:
    used: set[int] = set()
    kept = []
    for finding in findings:
        text = lines.get(finding.file, [""])[finding.line - 1] if finding.line else ""
        hit = [i for i, e in enumerate(entries) if e.covers(finding.file, text)]
        used.update(hit)
        if not hit:
            kept.append(finding)
    stale = [
        Finding(ALLOWLIST_PATH, 0, ALLOWLIST_STALE, f"allowlist entry for {e.path} matches nothing")
        for i, e in enumerate(entries)
        if i not in used
    ]
    return kept + stale


def scan_repo(repo_root: Path) -> ScanResult:
    rules = load_rules(repo_root / CONFIG_PATH)
    entries = load_allowlist(repo_root / ALLOWLIST_PATH)
    citations = Citations(repo_root, rules)
    skip = (*rules.prototype_excluded, *(e for e in rules.exclude if e.endswith("/")))
    scanned: list[str] = []
    lines: dict[str, list[str]] = {}
    findings: list[Finding] = []
    for path in iter_files(repo_root, suffixes=frozenset({".md"}), exclude=skip):
        rel = relative_posix(repo_root, path)
        if not _in_scope(rel, rules):
            continue
        text = path.read_text(encoding="utf-8")
        scanned.append(rel)
        lines[rel] = text.split("\n")
        findings += scan_text(rel, text, rules, citations)
        findings += _forbidden(repo_root, rel, text)
    findings = _apply_allowlist(findings, lines, entries) + scan_structured(repo_root, rules)
    ordered = tuple(sorted(findings, key=lambda f: (f.file, f.line, f.rule_id)))
    return ScanResult(
        ordered, tuple(scanned), (*rules.prototype_excluded, *rules.exclude), citations.spike_states
    )
