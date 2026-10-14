"""Plain-language lines for a case, built only from the case and its client's own numbers (spec 031)."""

from __future__ import annotations

import pandas as pd

from eios.dataplane.aml_cases import AmlCase

_RULE_ORDER = (
    "MULE_RING",
    "ROUND_TRIP",
    "VOLUME_VS_INCOME",
    "PASS_THROUGH",
    "DEPOSIT_BURST",
    "NEW_ACCOUNT",
    "LARGE_DEPOSIT",
)


def headline(case: AmlCase, row: pd.Series) -> str:
    """The one line on the triage card: the strongest reason first, with the numbers behind it."""
    income = max(float(row["declared_monthly_income_usd"]), 1.0)
    volume = float(row["dep_volume"])
    ordered = sorted(case.rules, key=lambda r: _RULE_ORDER.index(r) if r in _RULE_ORDER else 99)
    first = ordered[0] if ordered else ""
    if first == "MULE_RING":
        return f"{case.ring_size} linked accounts share a device and move money in matched bursts"
    if first == "ROUND_TRIP":
        return f"Round-trip: deposit, near-zero trading, withdrawal inside 72 hours ({_detail(case, 'ROUND_TRIP')})"
    if first == "VOLUME_VS_INCOME":
        asset = "USDT" if float(row["usdt_volume"]) > 0.5 * volume else "USD"
        return f"Deposits {volume / income * 100:,.0f}% > Income (${volume:,.0f} {asset} vs ${income:,.0f}/mo declared)"
    return case.reasons[0] if case.reasons else "Flagged by a surveillance rule"


def _detail(case: AmlCase, rule: str) -> str:
    index = case.rules.index(rule) if rule in case.rules else 0
    return case.reasons[index] if index < len(case.reasons) else ""
