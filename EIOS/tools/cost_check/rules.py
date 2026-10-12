"""Per-row rules of contracts/cost-model.md. A stale price date is a warning, never a failure."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from eios.common.provenance import Tag
from tools.common.findings import Finding
from tools.cost_check.model import CostRow, parse_decimal, parse_iso_date

_SPIKE_ID = re.compile(r"\bS-\d{2}\b")
_TAGS = frozenset(tag.value for tag in Tag)
_FORBIDDEN_DRIVERS = frozenset({"total", "subtotal"})
_RECONCILED_PREFIX = "reconciled:"


@dataclass(frozen=True, slots=True)
class RuleResult:
    findings: tuple[Finding, ...]
    warnings: tuple[Finding, ...]


class _Reporter:
    """Builds findings for one row; every message names the driver."""

    def __init__(self, file: str, row: CostRow) -> None:
        self._file = file
        self._row = row

    def __call__(self, rule_id: str, message: str) -> Finding:
        driver = self._row.driver or "<blank>"
        return Finding(self._file, self._row.line, rule_id, f"driver {driver!r}: {message}")


def _identity(row: CostRow, report: _Reporter) -> list[Finding]:
    out: list[Finding] = []
    if not row.driver:
        out.append(report("cost.driver.missing", "driver name is empty"))
    elif row.driver.casefold() in _FORBIDDEN_DRIVERS:
        out.append(report("cost.driver.total_name", "totals are computed, never typed as a row"))
    if not row.unit:
        out.append(report("cost.unit.missing", "billing unit is empty"))
    return out


def _non_negative(text: str) -> bool:
    value = parse_decimal(text)
    return value is not None and value >= 0


def _numbers(row: CostRow, report: _Reporter) -> list[Finding]:
    out: list[Finding] = []
    if row.quantity and not _non_negative(row.quantity):
        out.append(report("cost.quantity.invalid", f"quantity {row.quantity!r} is not >= 0"))
    if row.unit_price and not _non_negative(row.unit_price):
        out.append(report("cost.price.invalid", f"unit_price {row.unit_price!r} is not >= 0"))
    return out


def _price_evidence(row: CostRow, report: _Reporter) -> list[Finding]:
    out: list[Finding] = []
    if row.unit_price:
        if not row.price_source:
            out.append(
                report("cost.price.source_missing", "unit_price is set without price_source")
            )
        if not row.price_verified_on:
            out.append(
                report("cost.price.date_missing", "unit_price is set without price_verified_on")
            )
    if row.price_verified_on and parse_iso_date(row.price_verified_on) is None:
        message = f"price_verified_on {row.price_verified_on!r} is not an ISO date (YYYY-MM-DD)"
        out.append(report("cost.date.not_iso", message))
    return out


def _provenance(row: CostRow, report: _Reporter) -> list[Finding]:
    if not row.tag:
        return [report("cost.tag.missing", "every row needs a provenance tag")]
    if row.tag not in _TAGS:
        allowed = ", ".join(sorted(_TAGS))
        return [report("cost.tag.invalid", f"tag {row.tag!r} is not one of {allowed}")]
    if row.tag == Tag.SPIKE.value and not _SPIKE_ID.search(row.price_source):
        return [report("cost.spike.id_missing", "a [SPIKE] row must name a spike id (S-NN)")]
    return []


def _reconciliation(row: CostRow, report: _Reporter) -> list[Finding]:
    value = row.reconciliation
    if value == "pending":
        return []
    if value.startswith(_RECONCILED_PREFIX) and value[len(_RECONCILED_PREFIX) :].strip():
        return []
    message = f"reconciliation {value!r} must be 'pending' or 'reconciled:<bill reference>'"
    return [report("cost.reconciliation.invalid", message)]


def _stale_warning(
    row: CostRow, report: _Reporter, today: date, staleness_days: int
) -> list[Finding]:
    verified = parse_iso_date(row.price_verified_on)
    if verified is None or (age := (today - verified).days) <= staleness_days:
        return []
    message = (
        f"price verified on {row.price_verified_on} is {age} days old, "
        f"over the {staleness_days}-day staleness threshold"
    )
    return [report("cost.price.stale", message)]


def _duplicates(rows: tuple[CostRow, ...], file: str) -> list[Finding]:
    first_seen: dict[str, int] = {}
    out: list[Finding] = []
    for row in rows:
        key = row.driver.casefold()
        if not key:
            continue
        if key in first_seen:
            message = f"duplicate driver (first on line {first_seen[key]})"
            out.append(_Reporter(file, row)("cost.driver.duplicate", message))
        else:
            first_seen[key] = row.line
    return out


def check_rows(
    rows: tuple[CostRow, ...], file: str, today: date, staleness_days: int
) -> RuleResult:
    """Apply every row rule; ``today`` is injected so staleness is deterministic in tests."""
    findings = _duplicates(rows, file)
    warnings: list[Finding] = []
    for row in rows:
        report = _Reporter(file, row)
        for rule in (_identity, _numbers, _price_evidence, _provenance, _reconciliation):
            findings.extend(rule(row, report))
        warnings.extend(_stale_warning(row, report, today, staleness_days))
    return RuleResult(tuple(findings), tuple(warnings))
