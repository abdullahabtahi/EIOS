"""Building the snapshot into the warm tier and reading it back, with a fake warehouse (no cloud)."""

from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pytest

from eios.netintel import sources
from eios.netintel.store import NetUnavailable, SnapshotReader, build_snapshot

IPINFO_CSV = """network,country,country_code,continent,continent_code,asn,as_name,as_domain
1.0.0.0/24,Australia,AU,Oceania,OC,AS13335,"Cloudflare, Inc.",cloudflare.com
1.0.1.0/24,Australia,AU,Oceania,OC,AS13335,"Cloudflare, Inc.",cloudflare.com
1.0.2.0/23,China,CN,Asia,AS,,,
2606:4700::/32,United States,US,North America,NA,AS13335,"Cloudflare, Inc.",cloudflare.com
"""
FEEDS = {
    sources.TOR_URL: "1.0.0.7\n",
    sources.AWS_URL: '{"prefixes":[{"ip_prefix":"3.5.140.0/22","region":"r","service":"EC2"}],"ipv6_prefixes":[]}',
    sources.GCP_URL: '{"prefixes":[{"ipv4Prefix":"34.80.0.0/15","service":"Google Cloud","scope":"s"}]}',
    sources.VPN_URL: "5.5.5.0/24\n",
    sources.DATACENTER_URL: "6.6.6.0/24\n",
}


class _Job:
    def __init__(self, frame: pd.DataFrame | None = None) -> None:
        self._frame = frame

    def result(self) -> Any:
        return self

    def to_arrow(self, **_: Any) -> pa.Table:
        assert self._frame is not None
        return pa.Table.from_pandas(self._frame, preserve_index=False)


class _Client:
    def __init__(self, tables: dict[str, pd.DataFrame] | None = None) -> None:
        self.tables = tables or {}
        self.loads: dict[str, tuple[int, str]] = {}
        self.queries = 0

    def create_dataset(self, dataset: Any, exists_ok: bool = False) -> None:
        return None

    def load_table_from_dataframe(
        self, frame: pd.DataFrame, table: str, job_config: Any = None, location: str | None = None
    ) -> _Job:
        self.loads[table.split(".")[-1]] = (len(frame), job_config.write_disposition)
        self.tables[table.split(".")[-1]] = frame
        return _Job()

    def list_rows(self, ref: str) -> _Job:
        self.queries += 1
        return _Job(self.tables[ref.split(".")[-1]])


@pytest.fixture
def ipinfo(tmp_path: Path) -> Path:
    path = tmp_path / "ipinfo_lite.csv"
    path.write_text(IPINFO_CSV)
    return path


def test_build_loads_ranges_lists_and_provenance_into_the_warm_tier(ipinfo: Path) -> None:
    client = _Client()
    summary = build_snapshot(
        "p", ipinfo, client=client, fetch=FEEDS.__getitem__, today="2026-10-15"
    )
    assert summary["net_ranges_v4"] == 2  # three rows, the first two merge
    assert summary["net_ranges_v6"] == 1 and summary["net_lists"] == 5
    assert set(summary) == {
        "net_ranges_v4",
        "net_ranges_v6",
        "net_asn",
        "net_country",
        "net_lists",
        "net_meta",
    }
    assert all(disposition == "WRITE_TRUNCATE" for _, disposition in client.loads.values())
    meta = client.tables["net_meta"]
    assert set(meta["source"]) >= {"IPinfo Lite", "Tor Project bulk exit list", "X4BNet VPN list"}
    assert set(meta["as_of"]) == {"2026-10-15"}


def test_a_list_that_parses_to_nothing_stops_the_build(ipinfo: Path) -> None:
    feeds = {**FEEDS, sources.TOR_URL: "<html>blocked</html>\n"}
    with pytest.raises(RuntimeError, match="Tor"):
        build_snapshot("p", ipinfo, client=_Client(), fetch=feeds.__getitem__, today="2026-10-15")


def test_the_snapshot_reads_back_into_a_working_lookup(ipinfo: Path) -> None:
    client = _Client()
    build_snapshot("p", ipinfo, client=client, fetch=FEEDS.__getitem__, today="2026-10-15")
    reader = SnapshotReader("test-project", client=client)
    snap = reader.snapshot()
    r = snap.lookup("1.0.0.7")
    assert r.country == ("AU", "Australia") and r.network == (
        13335,
        "Cloudflare, Inc.",
        "cloudflare.com",
    )
    assert r.verdict == "tor_exit" and {s.name for s in r.sources} >= {
        "IPinfo Lite",
        "Tor Project bulk exit list",
    }
    assert snap.lookup("2606:4700::5").country == ("US", "United States")
    assert snap.lookup("1.0.3.1").country == ("CN", "China")  # the merged /23 reaches here
    assert reader.snapshot() is snap and client.queries == 6  # read once, cached


def test_an_empty_warehouse_is_unavailable_not_an_empty_answer() -> None:
    empty = pd.DataFrame({"start": [], "end": [], "country_code": [], "asn": []}).astype(
        {"start": "int64", "end": "int64", "asn": "int64"}
    )
    empty6 = pd.DataFrame(
        {k: [] for k in ("start_hi", "start_lo", "end_hi", "end_lo", "country_code", "asn")}
    ).astype({k: "int64" for k in ("start_hi", "start_lo", "end_hi", "end_lo", "asn")})
    tables = {
        "net_ranges_v4": empty,
        "net_ranges_v6": empty6,
        "net_country": pd.DataFrame({"country_code": [], "country": []}),
        "net_asn": pd.DataFrame({"asn": [], "as_name": [], "as_domain": []}),
        "net_lists": pd.DataFrame({"list_name": [], "network": [], "detail": []}),
        "net_meta": pd.DataFrame({"source": [], "as_of": [], "row_count": []}),
    }
    with pytest.raises(NetUnavailable):
        SnapshotReader("test-project", client=_Client(tables)).snapshot()


def test_a_missing_table_says_to_build_the_snapshot() -> None:
    from google.api_core.exceptions import NotFound

    class Missing(_Client):
        def list_rows(self, ref: str) -> _Job:
            raise NotFound("no such table")

    with pytest.raises(NetUnavailable, match="netintel build"):
        SnapshotReader("test-project", client=Missing()).snapshot()


def test_a_malformed_project_id_is_refused_before_it_reaches_sql() -> None:
    with pytest.raises(ValueError, match="project id"):
        SnapshotReader("x`; DROP TABLE y; --")


def test_every_table_loaded_has_exactly_the_columns_of_its_declared_schema(ipinfo: Path) -> None:
    """The fake warehouse ignores schemas, BigQuery does not: a drift here fails the real load."""
    from eios.netintel.store import _SCHEMAS

    client = _Client()
    build_snapshot("p", ipinfo, client=client, fetch=FEEDS.__getitem__, today="2026-10-15")
    for name, frame in client.tables.items():
        assert list(frame.columns) == [column for column, _ in _SCHEMAS[name]], name


@pytest.mark.requires_cloud
def test_live_snapshot_answers_from_the_warehouse() -> None:
    """Needs EIOS_TEST_CLOUD=1, EIOS_WARM_PROJECT and a built snapshot; the fake warehouse cannot catch what BigQuery rejects."""
    import os

    snap = SnapshotReader(os.environ["EIOS_WARM_PROJECT"]).snapshot()
    google_dns = snap.lookup("8.8.8.8")
    assert google_dns.country == ("US", "United States") and google_dns.network is not None
    assert google_dns.network[0] == 15169
    assert snap.lookup("2606:4700::6810:85e5").country == ("US", "United States")
    assert snap.lookup("10.0.0.1").verdict == "not_public"
    assert {s.name for s in google_dns.sources} >= {"IPinfo Lite", "Tor Project bulk exit list"}
