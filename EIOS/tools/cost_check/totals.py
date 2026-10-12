"""Totals computed by the tool over verified rows only; nothing here is typed by hand."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from tools.cost_check.model import CostRow, parse_decimal, parse_iso_date

TOTAL_BASIS = "sum of quantity x unit_price over verified rows, computed by cost_check"


@dataclass(frozen=True, slots=True)
class VerifiedLine:
    line: int
    driver: str
    unit: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal
    source: str
    verified_on: date | None
    tag: str


@dataclass(frozen=True, slots=True)
class UnverifiedLine:
    line: int
    driver: str
    reason: str
    tag: str


@dataclass(frozen=True, slots=True)
class Totals:
    verified: tuple[VerifiedLine, ...]
    unverified: tuple[UnverifiedLine, ...]
    total: Decimal | None


def _amount(text: str) -> Decimal | None:
    value = parse_decimal(text)
    return value if value is not None and value >= 0 else None


def _why_unverified(row: CostRow) -> str | None:
    """The reason a row is excluded from totals, or ``None`` when it is verified."""
    reasons = []
    for name, text in (("unit_price", row.unit_price), ("quantity", row.quantity)):
        if not text:
            reasons.append(f"{name} blank")
        elif _amount(text) is None:
            reasons.append(f"{name} invalid")
    return ", ".join(reasons) or None


def _verified(row: CostRow) -> VerifiedLine | None:
    quantity, price = _amount(row.quantity), _amount(row.unit_price)
    if quantity is None or price is None:
        return None
    return VerifiedLine(
        line=row.line,
        driver=row.driver,
        unit=row.unit,
        quantity=quantity,
        unit_price=price,
        line_total=quantity * price,
        source=row.price_source,
        verified_on=parse_iso_date(row.price_verified_on),
        tag=row.tag,
    )


def compute_totals(rows: tuple[CostRow, ...]) -> Totals:
    """Split rows into verified (quantity and unit_price set) and unverified; sum the former."""
    verified: list[VerifiedLine] = []
    unverified: list[UnverifiedLine] = []
    for row in rows:
        line = _verified(row)
        if line is not None:
            verified.append(line)
        else:
            reason = _why_unverified(row) or "not computable"
            unverified.append(UnverifiedLine(row.line, row.driver, reason, row.tag))
    total = sum((v.line_total for v in verified), Decimal(0)) if verified else None
    return Totals(tuple(verified), tuple(unverified), total)


def _plain(value: Decimal) -> str:
    return format(value, "f")


def _verified_dict(line: VerifiedLine) -> dict[str, object]:
    return {
        "line": line.line,
        "driver": line.driver,
        "unit": line.unit,
        "quantity": _plain(line.quantity),
        "unit_price": _plain(line.unit_price),
        "line_total": _plain(line.line_total),
        "source": line.source,
        "price_verified_on": line.verified_on.isoformat() if line.verified_on else None,
        "tag": line.tag,
    }


def totals_to_dict(totals: Totals) -> dict[str, object]:
    """JSON-ready form; amounts are strings so no float ever stands in for a figure."""
    return {
        "verified": [_verified_dict(v) for v in totals.verified],
        "unverified": [
            {"line": u.line, "driver": u.driver, "reason": u.reason, "tag": u.tag}
            for u in totals.unverified
        ],
        "total": _plain(totals.total) if totals.total is not None else None,
        "total_basis": TOTAL_BASIS,
    }


def render_totals(totals: Totals) -> list[str]:
    """Printed report: source, pricing date and tag beside every figure."""
    lines = ["verified rows (included in the total):"]
    for v in totals.verified:
        when = v.verified_on.isoformat() if v.verified_on else "undated"
        lines.append(
            f"  {v.driver}: {_plain(v.quantity)} x {_plain(v.unit_price)} (unit: {v.unit}) = "
            f"{_plain(v.line_total)}; source {v.source}; priced {when}; tag {v.tag}"
        )
    if not totals.verified:
        lines.append("  none")
    lines.append("unverified rows (excluded from the total):")
    lines.extend(f"  {u.driver}: unverified ({u.reason}); tag {u.tag}" for u in totals.unverified)
    if not totals.unverified:
        lines.append("  none")
    if totals.total is None:
        lines.append("total: none, no verified rows")
    else:
        lines.append(f"total over verified rows: {_plain(totals.total)} ({TOTAL_BASIS})")
    return lines
