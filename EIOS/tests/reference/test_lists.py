"""The EU high-risk list and the Basel AML Index scores: official-source tables, checked against what the sources publish."""

import pycountry
import pytest

from eios.reference.basel import BASEL_ROWS, BASEL_TOTAL, band
from eios.reference.eu_list import EU_ROWS


class TestEuList:
    def test_the_commission_page_lists_26_jurisdictions_once_each(self) -> None:
        codes = [r["iso2"] for r in EU_ROWS]
        assert len(codes) == 26 and len(set(codes)) == 26
        assert all(pycountry.countries.get(alpha_2=c) for c in codes)

    def test_the_2026_additions_are_in_and_the_2026_removals_are_out(self) -> None:
        codes = {r["iso2"] for r in EU_ROWS}
        assert {"RU", "BO", "VG"} <= codes  # added by Delegated Regulations 2026/46 and 2026/83
        assert not codes & {"NG", "ZA", "TZ", "ML", "MZ", "BF"}  # removed in the same amendment

    def test_every_row_carries_the_list_source_and_as_of(self) -> None:
        for row in EU_ROWS:
            assert row["list_name"] == "eu_high_risk"
            assert "2016/1675" in row["source"] and "finance.ec.europa.eu" in row["source"]
            assert row["as_of"] == "2026-01-29"


class TestBaselScores:
    def test_the_public_edition_ranks_177_jurisdictions_without_gaps(self) -> None:
        assert BASEL_TOTAL == len(BASEL_ROWS) == 177
        assert [r["rank"] for r in BASEL_ROWS] == list(range(1, 178))
        codes = [r["iso2"] for r in BASEL_ROWS]
        assert len(set(codes)) == 177
        assert all(pycountry.countries.get(alpha_2=c) for c in codes)

    def test_scores_fall_with_rank_and_stay_on_the_0_to_10_scale(self) -> None:
        scores = [r["value"] for r in BASEL_ROWS]
        assert all(0 <= s <= 10 for s in scores)
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.parametrize(
        ("iso2", "rank", "score"),
        [("MM", 1, 8.18), ("HT", 2, 8.12), ("MA", 100, 5.04), ("AD", 171, 3.48), ("FI", 177, 3.03)],
    )
    def test_figures_the_institute_itself_quotes(self, iso2: str, rank: int, score: float) -> None:
        row = next(r for r in BASEL_ROWS if r["iso2"] == iso2)
        assert (row["rank"], row["value"]) == (rank, score)

    def test_a_jurisdiction_outside_the_public_edition_has_no_row_not_a_zero(self) -> None:
        codes = {r["iso2"] for r in BASEL_ROWS}
        assert not codes & {"VG", "KY"}

    def test_every_row_carries_score_name_source_and_as_of(self) -> None:
        for row in BASEL_ROWS:
            assert row["score_name"] == "basel_aml_index"
            assert "Basel AML Index 2025" in row["source"]
            assert row["as_of"] == "2025-12-08"

    @pytest.mark.parametrize(
        ("score", "expected"),
        [(4.69, "lower"), (4.70, "medium"), (6.08, "medium"), (6.09, "higher"), (8.18, "higher")],
    )
    def test_bands_follow_the_institutes_published_breaks(
        self, score: float, expected: str
    ) -> None:
        assert band(score) == expected
