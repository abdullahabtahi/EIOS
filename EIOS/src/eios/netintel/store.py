"""Build the address-check snapshot into the warm tier and read it back.

`build_snapshot` downloads nothing itself except the public lists (through the `fetch` it is given); the IPinfo Lite
file is passed in, so the token is used by the command line only. Each table is rebuilt whole (WRITE_TRUNCATE) in
`warm_reference`, next to the reference layer, and `net_meta` records every source with the date it was read. The
reader pulls the tables into memory once, and an empty or missing warehouse is `NetUnavailable`, never an empty
answer.
"""

from __future__ import annotations

import logging
import os
import re
import tempfile
import threading
import urllib.request
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa

from eios.netintel import sources
from eios.netintel.lookup import NetSnapshot, Ranges, SourceStamp, ranges_from_arrow
from eios.netintel.ranges import build_ranges
from eios.netintel.sources import ListEntry
from eios.reference.build import REFERENCE_DATASET, WARM_LOCATION, ensure_dataset

_LOG = logging.getLogger("eios.netintel.store")
_PROJECT_ID = re.compile(r"[a-z][a-z0-9-]{4,28}[a-z0-9]")
_IPINFO_URL = "https://ipinfo.io/data/ipinfo_lite.csv.gz"
TABLES = ("net_ranges_v4", "net_ranges_v6", "net_asn", "net_country", "net_lists", "net_meta")
IPINFO_NAME = "IPinfo Lite"

_SCHEMAS: dict[str, list[tuple[str, str]]] = {
    "net_ranges_v4": [
        ("start", "INT64"),
        ("end", "INT64"),
        ("country_code", "STRING"),
        ("asn", "INT64"),
    ],
    "net_ranges_v6": [
        ("start_hi", "INT64"),
        ("start_lo", "INT64"),
        ("end_hi", "INT64"),
        ("end_lo", "INT64"),
        ("country_code", "STRING"),
        ("asn", "INT64"),
    ],
    "net_asn": [("asn", "INT64"), ("as_name", "STRING"), ("as_domain", "STRING")],
    "net_country": [("country_code", "STRING"), ("country", "STRING")],
    "net_lists": [("list_name", "STRING"), ("network", "STRING"), ("detail", "STRING")],
    "net_meta": [("source", "STRING"), ("as_of", "STRING"), ("row_count", "INT64")],
}
# (source name shown with a verdict, URL, parser)
_FEEDS: tuple[tuple[str, str, Callable[[str], tuple[list[ListEntry], int]]], ...] = (
    ("Tor Project bulk exit list", sources.TOR_URL, sources.parse_tor),
    ("AWS ip-ranges.json", sources.AWS_URL, sources.parse_aws),
    ("Google Cloud cloud.json", sources.GCP_URL, sources.parse_gcp),
    ("X4BNet VPN list", sources.VPN_URL, lambda t: sources.parse_cidr_list(t, sources.LIST_VPN)),
    (
        "X4BNet datacenter list",
        sources.DATACENTER_URL,
        lambda t: sources.parse_cidr_list(t, sources.LIST_DATACENTER),
    ),
)


class NetUnavailable(RuntimeError):
    """The address-check snapshot is not configured or holds no rows."""


def download_ipinfo(token: str, into: Path | None = None) -> Path:
    """The Lite database to a file. The token is in the request URL, so errors here never repeat the URL."""
    target = into or Path(tempfile.mkdtemp(prefix="ipinfo-")) / "ipinfo_lite.csv.gz"
    try:
        with urllib.request.urlopen(f"{_IPINFO_URL}?token={token}", timeout=300) as response:  # noqa: S310
            target.write_bytes(response.read())
    except OSError as exc:
        raise RuntimeError(f"the IPinfo Lite download failed ({type(exc).__name__})") from None
    return target


def _load(client: Any, project: str, table: str, frame: pd.DataFrame) -> int:
    from google.cloud import bigquery

    schema = [bigquery.SchemaField(n, t) for n, t in _SCHEMAS[table]]
    config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE, schema=schema
    )
    client.load_table_from_dataframe(
        frame, f"{project}.{REFERENCE_DATASET}.{table}", job_config=config, location=WARM_LOCATION
    ).result()
    return len(frame)


def build_snapshot(
    project: str,
    ipinfo_file: Path,
    *,
    client: Any = None,
    fetch: Callable[[str], str] = sources.fetch_text,
    today: str | None = None,
) -> dict[str, int]:
    from google.cloud import bigquery

    as_of = today or datetime.now(UTC).date().isoformat()
    frame = pd.read_csv(
        ipinfo_file,
        usecols=["network", "country", "country_code", "asn", "as_name", "as_domain"],
        dtype=str,
        keep_default_na=False,
    )
    v4, v6 = build_ranges(frame)
    named = frame[frame["asn"] != ""].drop_duplicates("asn")
    asn = pd.DataFrame(
        {
            "asn": named["asn"].str.replace("AS", "", regex=False).astype("int64"),
            "as_name": named["as_name"],
            "as_domain": named["as_domain"],
        }
    )
    country = frame[frame["country_code"] != ""][["country_code", "country"]].drop_duplicates(
        "country_code"
    )
    entries: list[ListEntry] = []
    meta = [{"source": IPINFO_NAME, "as_of": as_of, "row_count": len(frame)}]
    for name, url, parse in _FEEDS:
        found, skipped = parse(fetch(url))
        if (
            not found
        ):  # an error page or an empty file must stop the build, not become "nothing is listed"
            raise RuntimeError(
                f"{name} parsed to zero entries; refusing to build a snapshot without it"
            )
        if skipped:
            _LOG.warning("%s: %d lines could not be read", name, skipped)
        entries.extend(found)
        meta.append({"source": name, "as_of": as_of, "row_count": len(found)})
    lists = pd.DataFrame(
        [{"list_name": e.list_name, "network": e.network, "detail": e.detail} for e in entries]
    )

    client = client or bigquery.Client(project=project)
    ensure_dataset(client, project)
    tables = {
        "net_ranges_v4": v4,
        "net_ranges_v6": v6,
        "net_asn": asn,
        "net_country": country,
        "net_lists": lists,
        "net_meta": pd.DataFrame(meta),
    }
    summary = {name: _load(client, project, name, table) for name, table in tables.items()}
    _LOG.info("address-check snapshot built: %s", summary)
    return summary


class SnapshotReader:
    """Reads the tables into memory once; later calls return the same snapshot.

    The small tables are read while the two big range tables are read one after the other, and each range table is
    turned into compact arrays as soon as it arrives, so the peak stays well under the sum of the tables."""

    def __init__(self, project: str, *, client: Any = None) -> None:
        if not _PROJECT_ID.fullmatch(project):
            raise ValueError(f"not a GCP project id: {project!r}")
        self._project, self._client = project, client
        self._lock = threading.Lock()
        self._cached: NetSnapshot | None = None

    def _table(self, client: Any, table: str) -> pa.Table:
        from google.api_core.exceptions import NotFound

        ref = f"{self._project}.{REFERENCE_DATASET}.{table}"
        try:  # the Storage API reads a million rows far faster than the REST pages
            return client.list_rows(ref).to_arrow(create_bqstorage_client=True)
        except NotFound as exc:
            raise NetUnavailable(
                f"{table} does not exist; run `python -m eios.netintel build`"
            ) from exc
        except (
            Exception
        ) as exc:  # not enabled or not permitted: the REST read is slower but the same rows
            _LOG.warning(
                "BigQuery Storage read failed for %s (%s); using the REST read",
                table,
                type(exc).__name__,
            )
            return client.list_rows(ref).to_arrow(create_bqstorage_client=False)

    def snapshot(self) -> NetSnapshot:
        with self._lock:
            if self._cached is None:
                self._cached = self._read()
            return self._cached

    def _read(self) -> NetSnapshot:
        from google.cloud import bigquery

        client = self._client or bigquery.Client(project=self._project)
        country = self._table(client, "net_country").to_pandas()
        codes = sorted(country["country_code"])

        def ranges(table: str, version: int) -> Ranges:
            return ranges_from_arrow(self._table(client, table), version, codes)

        def small(table: str) -> pd.DataFrame:
            return self._table(client, table).to_pandas()

        with ThreadPoolExecutor(
            max_workers=3
        ) as pool:  # the three small reads overlap the big ones
            fa, fl, fm = (pool.submit(small, t) for t in ("net_asn", "net_lists", "net_meta"))
            v4 = ranges("net_ranges_v4", 4)  # one big table at a time keeps the peak low
            v6 = ranges("net_ranges_v6", 6)
            asn, lists, meta = fa.result(), fl.result(), fm.result()
        if len(v4.start) == 0 or len(v6.start) == 0:
            raise NetUnavailable("the address-check snapshot holds no ranges")
        asns = {int(r.asn): (r.as_name, r.as_domain) for r in asn.itertuples()}
        countries = dict(country.itertuples(index=False, name=None))
        entries = [ListEntry(r.list_name, r.network, r.detail) for r in lists.itertuples()]
        stamps = tuple(SourceStamp(r.source, r.as_of) for r in meta.itertuples())
        return NetSnapshot(v4, v6, codes, asns, countries, entries, stamps)


def reader_from_env() -> SnapshotReader | None:
    """A reader only when the warehouse is the BigQuery warm tier (the same switch as the reference layer)."""
    project = os.getenv("EIOS_WARM_PROJECT")
    if os.getenv("EIOS_WARM_BACKEND") != "bigquery" or not project:
        return None
    return SnapshotReader(project)
