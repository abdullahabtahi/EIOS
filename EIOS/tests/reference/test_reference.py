"""The reference layer: real public sources, entity and jurisdiction level, with provenance on every row."""

from pathlib import Path

import pytest

from eios.reference.fatf import FATF_ROWS
from eios.reference.icij import aggregate_precedent
from eios.reference.iso import to_iso2

ENTITIES = """node_id,name,jurisdiction,jurisdiction_description,country_codes
1,A LTD,BAH,Bahamas,HKG
2,B LTD,BAH,Bahamas,HKG;CHE
3,C LTD,BVI,British Virgin Islands,VGB
4,D LTD,PMA,Panama,
5,E LTD,XXX,Undetermined,GBR
6,F LTD,MLT,Malta,MLT
7,G LTD,,,
"""


@pytest.fixture
def entities_csv(tmp_path: Path) -> Path:
    path = tmp_path / "nodes-entities.csv"
    path.write_text(ENTITIES)
    return path


class TestIso:
    @pytest.mark.parametrize(
        ("code", "iso2"),
        [
            ("BAH", "BS"),
            ("BVI", "VG"),
            ("PMA", "PA"),
            ("MLT", "MT"),
            ("KY", "KY"),
            ("UK", "GB"),
            ("HK", "HK"),
        ],
    )
    def test_maps_iciJ_and_iso_codes(self, code: str, iso2: str) -> None:
        assert to_iso2(code) == iso2

    @pytest.mark.parametrize("code", ["XXX", "XX", "", None, "ZZZZZ"])
    def test_undetermined_or_unknown_is_none_never_guessed(self, code: str | None) -> None:
        assert to_iso2(code) is None


class TestPrecedent:
    def test_counts_incorporated_and_linked_entities_per_country(self, entities_csv: Path) -> None:
        rows = {r["iso2"]: r for r in aggregate_precedent(entities_csv, as_of="2026-09-09")}
        assert rows["BS"]["entities_incorporated"] == 2
        assert rows["HK"]["entities_linked"] == 2
        assert rows["CH"]["entities_linked"] == 1
        assert rows["VG"]["entities_incorporated"] == 1 and rows["VG"]["entities_linked"] == 1

    def test_unmapped_entities_are_reported_not_dropped_silently(self, entities_csv: Path) -> None:
        rows = aggregate_precedent(entities_csv, as_of="2026-09-09")
        total = sum(r["entities_incorporated"] for r in rows if r["iso2"] != "UNMAPPED")
        unmapped = next(r for r in rows if r["iso2"] == "UNMAPPED")
        assert total + unmapped["entities_incorporated"] == 7

    def test_every_row_carries_source_and_as_of(self, entities_csv: Path) -> None:
        for row in aggregate_precedent(entities_csv, as_of="2026-09-09"):
            assert row["source"].startswith("ICIJ Offshore Leaks")
            assert row["as_of"] == "2026-09-09"


class TestFatf:
    def test_one_row_per_jurisdiction_with_known_lists(self) -> None:
        codes = [r["iso2"] for r in FATF_ROWS]
        assert len(codes) == len(set(codes))
        assert {r["list_name"] for r in FATF_ROWS} == {"call_for_action", "increased_monitoring"}

    def test_the_three_call_for_action_jurisdictions(self) -> None:
        cfa = {r["iso2"] for r in FATF_ROWS if r["list_name"] == "call_for_action"}
        assert cfa == {"IR", "KP", "MM"}

    def test_provenance_states_secondary_sourcing_and_date(self) -> None:
        for row in FATF_ROWS:
            assert row["as_of"] == "2026-06-19"
            assert "secondary" in row["source"]
            assert len(row["iso2"]) == 2


class _FakeJob:
    def __init__(self, rows: list[dict] | None = None) -> None:
        self._rows = rows or []

    def result(self) -> list[dict]:
        return self._rows


class _FakeClient:
    def __init__(self) -> None:
        self.datasets: list[str] = []
        self.queries: list[tuple[str, str | None]] = []
        self.loads: dict[str, tuple[int, str]] = {}

    def create_dataset(self, dataset, exists_ok: bool = False) -> None:
        self.datasets.append(dataset.dataset_id)

    def query(self, sql: str, job_config=None, location: str | None = None) -> _FakeJob:
        self.queries.append((sql, location))
        return _FakeJob(
            [{"iso2": "AA", "name": "Aland", "boundary": "POLYGON EMPTY", "centroid": "POINT(0 0)"}]
        )

    def load_table_from_json(self, rows, table, job_config=None, location=None) -> _FakeJob:
        self.loads[table] = (len(rows), job_config.write_disposition)
        return _FakeJob()


def test_build_rebuilds_four_tables_idempotently_in_the_warm_location(entities_csv: Path) -> None:
    from eios.reference.build import REFERENCE_DATASET, WARM_LOCATION, build_reference

    client = _FakeClient()
    summary = build_reference("p", entities_csv, "2026-09-09", client=client)
    assert client.datasets == [REFERENCE_DATASET]
    assert set(summary) == {
        "jurisdictions",
        "jurisdiction_risk",
        "offshore_precedent",
        "country_indicators",
    }
    assert all(f"p.{REFERENCE_DATASET}.{t}" in client.loads for t in summary)
    assert all(d == "WRITE_TRUNCATE" for _, d in client.loads.values())
    assert all(
        loc == "US" for _, loc in client.queries
    )  # the public datasets live in US; results move to WARM_LOCATION
    assert WARM_LOCATION == "us-central1"
