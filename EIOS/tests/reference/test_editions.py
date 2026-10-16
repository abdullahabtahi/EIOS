"""Editions of the published lists, so the geo agent can say what a list change does to the book."""

from __future__ import annotations

import pytest

from eios.reference import eu_list, fatf
from eios.reference.editions import ListId, changes, curated_reference, editions


def test_the_current_fatf_edition_is_the_curated_june_table() -> None:
    pair = editions(ListId.FATF)
    assert dict(pair.after.members) == {r["iso2"]: r["list_name"] for r in fatf.FATF_ROWS}
    assert pair.after.source == fatf.SOURCE


def test_the_february_fatf_edition_differs_by_exactly_the_changes_june_named() -> None:
    diff = changes(editions(ListId.FATF))
    assert {c.iso2 for c in diff.added} == {"IQ", "BA"}
    assert {c.iso2 for c in diff.removed} == {"DZ", "NA"}
    assert diff.relisted == ()  # no country moved between the two FATF lists in June
    assert all(c.after == "increased_monitoring" for c in diff.added)


def test_the_eu_edition_before_january_2026_differs_by_the_two_amending_regulations() -> None:
    pair = editions(ListId.EU)
    assert set(pair.after.members) == {r["iso2"] for r in eu_list.EU_ROWS}
    diff = changes(pair)
    assert {c.iso2 for c in diff.added} == {"RU", "BO", "VG"}
    assert {c.iso2 for c in diff.removed} == {"BF", "ML", "MZ", "NG", "ZA", "TZ"}


def test_every_edition_says_where_it_comes_from_and_when_it_applied() -> None:
    for list_id in ListId:
        pair = editions(list_id)
        for edition in (pair.before, pair.after):
            assert edition.source and edition.in_force and edition.label
        assert pair.before.label != pair.after.label


def test_an_unknown_list_is_refused() -> None:
    with pytest.raises(ValueError):
        editions("ofac")  # type: ignore[arg-type]


def test_the_curated_reference_has_every_listed_or_scored_country_with_its_standing() -> None:
    ref = curated_reference()
    by_code = {c["iso2"]: c for c in ref["countries"]}
    assert by_code["MM"]["fatf_list"] == "call_for_action"
    assert by_code["MM"]["basel"]["score"] == 8.18 and by_code["MM"]["basel"]["band"] == "higher"
    assert by_code["RU"]["eu_high_risk"] is True and by_code["RU"]["fatf_list"] is None
    assert by_code["VG"]["basel"] is None  # not in the public edition: unrated, never low
    assert by_code["NG"]["name"] == "Nigeria"
    # nothing the code tables do not hold is invented: no offshore counts, no positions
    assert all(c["entities_incorporated"] is None for c in ref["countries"])
    assert set(ref["sources"]) >= {"fatf", "eu_list", "basel_aml"}


def test_a_country_on_no_list_and_unscored_is_absent_not_low() -> None:
    by_code = {c["iso2"]: c for c in curated_reference()["countries"]}
    assert "AQ" not in by_code  # Antarctica: on no list, not scored
