"""The cost model file: one immutable row per cost driver, read with line numbers."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from eios.common.errors import ConfigError
from tools.common.findings import Finding

REQUIRED_COLUMNS = (
    "driver",
    "unit",
    "quantity",
    "unit_price",
    "price_source",
    "price_verified_on",
    "tag",
)
RECONCILIATION_COLUMN = "reconciliation"
DEFAULT_RECONCILIATION = "pending"

HEADER_MISSING = "cost.header.missing_column"
HEADER_DUPLICATE = "cost.header.duplicate_column"
ROW_SHAPE = "cost.row.shape"

_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


@dataclass(frozen=True, slots=True)
class CostRow:
    """One driver line; every field is the stripped cell text, ``line`` is the file line."""

    line: int
    driver: str
    unit: str
    quantity: str
    unit_price: str
    price_source: str
    price_verified_on: str
    tag: str
    reconciliation: str


def parse_decimal(text: str) -> Decimal | None:
    """A finite decimal, or ``None`` when ``text`` is not one."""
    try:
        value = Decimal(text.strip())
    except InvalidOperation:
        return None
    return value if value.is_finite() else None


def parse_iso_date(text: str) -> date | None:
    """A strict ``YYYY-MM-DD`` date, or ``None``."""
    if not _ISO_DATE.fullmatch(text.strip()):
        return None
    try:
        return date.fromisoformat(text.strip())
    except ValueError:
        return None


def _read_text(path: Path, display: str) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        raise ConfigError(display, "$", f"cannot read cost model: {exc}") from exc


def _header_findings(header: list[str], display: str) -> list[Finding]:
    findings: list[Finding] = []
    missing = [c for c in REQUIRED_COLUMNS if c not in header]
    if missing:
        message = f"cost model is missing required columns: {', '.join(missing)}"
        findings.append(Finding(display, 1, HEADER_MISSING, message))
    repeated = sorted({c for c in header if header.count(c) > 1})
    if repeated:
        message = f"cost model repeats columns: {', '.join(repeated)}"
        findings.append(Finding(display, 1, HEADER_DUPLICATE, message))
    return findings


def _build_row(line: int, header: list[str], cells: list[str]) -> CostRow:
    by_name = dict(zip(header, (c.strip() for c in cells), strict=True))
    return CostRow(
        line=line,
        driver=by_name["driver"],
        unit=by_name["unit"],
        quantity=by_name["quantity"],
        unit_price=by_name["unit_price"],
        price_source=by_name["price_source"],
        price_verified_on=by_name["price_verified_on"],
        tag=by_name["tag"],
        reconciliation=by_name.get(RECONCILIATION_COLUMN, "") or DEFAULT_RECONCILIATION,
    )


def read_cost_model(path: Path, display: str) -> tuple[tuple[CostRow, ...], tuple[Finding, ...]]:
    """Parse the file into rows plus structural findings (bad header, wrong cell count)."""
    reader = csv.reader(_read_text(path, display).splitlines(keepends=True))
    header = [h.strip() for h in next(reader, [])]
    findings = _header_findings(header, display)
    if findings:
        return (), tuple(findings)
    rows: list[CostRow] = []
    for cells in reader:
        if not cells or not any(c.strip() for c in cells):
            continue
        if len(cells) != len(header):
            message = f"row has {len(cells)} cells but the header has {len(header)}"
            findings.append(Finding(display, reader.line_num, ROW_SHAPE, message))
            continue
        rows.append(_build_row(reader.line_num, header, cells))
    return tuple(rows), tuple(findings)
