"""Tag rules for structured config and data files that carry numbers."""

from __future__ import annotations

import csv
import re
from pathlib import Path

from tools.common.findings import Finding
from tools.common.yaml_io import load_yaml
from tools.label_check.rules import STRUCTURED, LabelRules
from tools.repo_checks._walk import relative_posix

_NUMBER_CELL = re.compile(r"^[\s$€£]*-?\d[\d,]*(?:\.\d+)?%?\s*$")


def _has_number(value: object) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int | float):
        return True
    if isinstance(value, dict):
        return any(_has_number(v) for v in value.values())
    if isinstance(value, list):
        return any(_has_number(v) for v in value)
    return False


def _yaml_verification(root: Path, rule: dict[str, str], rules: LabelRules) -> list[Finding]:
    findings: list[Finding] = []
    key = rule.get("verification_key", "verification")
    for path in sorted(root.glob(rule["glob"])):
        data = load_yaml(path)
        if not isinstance(data, dict):
            continue
        verification = data.get(key)
        tags = verification if isinstance(verification, dict) else {}
        for name, value in data.items():
            if name == key or not _has_number(value):
                continue
            if tags.get(name) not in rules.evidence:
                findings.append(
                    Finding(
                        relative_posix(root, path),
                        0,
                        STRUCTURED,
                        f"numeric key {name} has no provenance tag under {key}",
                    )
                )
    return findings


def _csv_tag_column(root: Path, rule: dict[str, str], rules: LabelRules) -> list[Finding]:
    findings: list[Finding] = []
    column = rule.get("tag_column", "tag")
    for path in sorted(root.glob(rule["glob"])):
        relative = relative_posix(root, path)
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if column not in (reader.fieldnames or []):
                findings.append(Finding(relative, 1, STRUCTURED, f"missing tag column {column}"))
                continue
            for row in reader:
                numeric = any(_NUMBER_CELL.match(v) for k, v in row.items() if k != column and v)
                if numeric and (row.get(column) or "").strip() not in rules.evidence:
                    findings.append(
                        Finding(
                            relative, reader.line_num, STRUCTURED, "numeric row has no valid tag"
                        )
                    )
    return findings


def scan_structured(root: Path, rules: LabelRules) -> list[Finding]:
    handlers = {"yaml_verification": _yaml_verification, "csv_tag_column": _csv_tag_column}
    findings: list[Finding] = []
    for rule in rules.structured_rules:
        findings.extend(handlers[rule["kind"]](root, rule, rules))
    return findings
