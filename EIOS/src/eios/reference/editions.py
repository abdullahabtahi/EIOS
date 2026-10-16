"""Editions of the published jurisdiction lists, and the curated reference the code tables alone can give.

A list changes three times a year (FATF plenaries) or by delegated regulation (EU), and an MLRO's question is what the
change does to their book. Each list therefore has two editions here: the one in force and the one before it.

FATF: the June 2026 plenary edition is `fatf.py`. The February 2026 edition is derived from the changes the June statement
names (added Iraq and Bosnia and Herzegovina, removed Algeria and Namibia) [EXTERNAL, secondary; verify against
fatf-gafi.org]. EU: the edition in force since 2026-01-29 is `eu_list.py`. The edition before it is derived from the two
amending regulations (2026/46 added the Russian Federation; 2026/83 added Bolivia and the British Virgin Islands and
removed Burkina Faso, Mali, Mozambique, Nigeria, South Africa and Tanzania) [EXTERNAL].

`curated_reference` is the reference layer's shape built from the code tables only (FATF, EU, Basel): what the geo tools
read when the warehouse is not configured. It carries no boundaries, positions, indicators or offshore counts, because the
code holds none; those are `None`, never zero.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from functools import cache
from typing import Any

import pycountry

from eios.reference import basel, eu_list, fatf

_EU_LISTING = eu_list.LIST_NAME


class ListId(StrEnum):
    FATF = "fatf"
    EU = "eu"


@dataclass(frozen=True)
class Edition:
    label: str
    in_force: (
        str  # when it applied, in words: a derived edition has no single publication date to quote
    )
    source: str
    members: Mapping[str, str]  # ISO alpha-2 -> its listing on this edition


@dataclass(frozen=True)
class EditionPair:
    list_id: ListId
    before: Edition
    after: Edition


@dataclass(frozen=True)
class Change:
    iso2: str
    before: str | None  # the listing on the earlier edition; None when absent
    after: str | None


@dataclass(frozen=True)
class ListChanges:
    added: tuple[Change, ...]
    removed: tuple[Change, ...]
    relisted: tuple[Change, ...]  # on both editions under a different listing


_FATF_JUNE_ADDED = ("IQ", "BA")
_FATF_JUNE_REMOVED = ("DZ", "NA")
_EU_2026_ADDED = ("RU", "BO", "VG")
_EU_2026_REMOVED = ("BF", "ML", "MZ", "NG", "ZA", "TZ")


def _fatf() -> EditionPair:
    june = {r["iso2"]: r["list_name"] for r in fatf.FATF_ROWS}
    february = {k: v for k, v in june.items() if k not in _FATF_JUNE_ADDED}
    february.update(dict.fromkeys(_FATF_JUNE_REMOVED, "increased_monitoring"))
    return EditionPair(
        ListId.FATF,
        before=Edition(
            label="FATF lists, February 2026 plenary",
            in_force="February to June 2026",
            source=(
                "Derived from the June 2026 plenary changes (added IQ and BA, removed DZ and NA); "
                "secondary summary, verify against fatf-gafi.org"
            ),
            members=february,
        ),
        after=Edition(
            label="FATF lists, June 2026 plenary",
            in_force=f"from {fatf.AS_OF}",
            source=fatf.SOURCE,
            members=june,
        ),
    )


def _eu() -> EditionPair:
    current = {r["iso2"]: _EU_LISTING for r in eu_list.EU_ROWS}
    earlier = {k: v for k, v in current.items() if k not in _EU_2026_ADDED}
    earlier.update(dict.fromkeys(_EU_2026_REMOVED, _EU_LISTING))
    return EditionPair(
        ListId.EU,
        before=Edition(
            label="EU high-risk third countries, before the January 2026 amendments",
            in_force=f"until the day before {eu_list.AS_OF}",
            source=(
                "Derived from Delegated Regulations (EU) 2026/46 and 2026/83 (European Commission), "
                "applied in reverse to the list in force"
            ),
            members=earlier,
        ),
        after=Edition(
            label="EU high-risk third countries, as amended to 2026/83",
            in_force=f"from {eu_list.AS_OF}",
            source=eu_list.SOURCE,
            members=current,
        ),
    )


def editions(list_id: ListId) -> EditionPair:
    if list_id == ListId.FATF:
        return _fatf()
    if list_id == ListId.EU:
        return _eu()
    raise ValueError(f"no editions for list {list_id!r}")


def changes(pair: EditionPair) -> ListChanges:
    before, after = pair.before.members, pair.after.members
    return ListChanges(
        added=tuple(Change(c, None, after[c]) for c in sorted(set(after) - set(before))),
        removed=tuple(Change(c, before[c], None) for c in sorted(set(before) - set(after))),
        relisted=tuple(
            Change(c, before[c], after[c])
            for c in sorted(set(before) & set(after))
            if before[c] != after[c]
        ),
    )


def country_name(iso2: str) -> str:
    """The short English name pycountry gives, or the code itself when pycountry does not know it."""
    country = pycountry.countries.get(alpha_2=iso2)
    if country is None:
        return iso2
    return str(getattr(country, "common_name", None) or country.name)


@cache
def curated_reference() -> dict[str, Any]:
    """The reference layer's countries and sources from the code tables alone (no warehouse)."""
    fatf_lists = {r["iso2"]: r["list_name"] for r in fatf.FATF_ROWS}
    eu = {r["iso2"] for r in eu_list.EU_ROWS}
    scores = {r["iso2"]: r for r in basel.BASEL_ROWS}
    codes = sorted(set(fatf_lists) | eu | set(scores))
    countries = [
        {
            "iso2": code,
            "name": country_name(code),
            "fatf_list": fatf_lists.get(code),
            "eu_high_risk": code in eu,
            "basel": _basel(scores.get(code)),
            "entities_incorporated": None,
            "entities_linked": None,
        }
        for code in codes
    ]
    sources = {
        "fatf": {"source": fatf.SOURCE, "as_of": fatf.AS_OF},
        "eu_list": {"source": eu_list.SOURCE, "as_of": eu_list.AS_OF},
        "basel_aml": {"source": basel.SOURCE, "as_of": basel.AS_OF},
    }
    return {"countries": countries, "sources": sources}


def _basel(row: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    score = float(row["value"])
    return {
        "score": score,
        "rank": int(row["rank"]),
        "of": basel.BASEL_TOTAL,
        "band": basel.band(score),
    }
