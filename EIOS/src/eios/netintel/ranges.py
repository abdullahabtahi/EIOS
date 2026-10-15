"""IPinfo Lite's network table as sorted, merged, non-overlapping ranges.

The table has about 4.2 million rows; contiguous rows with the same country and network are one range, which brings it
to about 2.1 million. IPv4 ranges are plain integers. An IPv6 address is 128 bits and BigQuery has no such type, so it
is stored as two INT64 halves, each shifted by 2**63 so that signed order is numeric order; `decode128` undoes it. Overlapping input is refused rather than resolved by a
guess: the lookup relies on ranges that do not overlap.
"""

from __future__ import annotations

import ipaddress

import numpy as np
import pandas as pd

COLUMNS = ["start", "end", "country_code", "asn"]
_OFFSET = 1 << 63
_HALF = (1 << 64) - 1


def split128(n: int) -> tuple[int, int]:
    """A 128-bit number as (high, low) signed INT64 halves whose order matches the number's."""
    return (n >> 64) - _OFFSET, (n & _HALF) - _OFFSET


def decode128(high: int, low: int) -> int:
    return ((high + _OFFSET) << 64) | (low + _OFFSET)


def _asn(series: pd.Series) -> np.ndarray:
    digits = series.fillna("").str.replace("AS", "", regex=False).replace("", "0")
    return np.asarray(digits.astype("int64").to_numpy(), dtype="int64")


def _v4(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame({"start": [], "end": [], "country_code": [], "asn": []}).astype(
            {"start": "int64", "end": "int64", "asn": "int64"}
        )
    parts = frame["network"].str.split("/", expand=True)
    octets = parts[0].str.split(".", expand=True).astype("uint64").to_numpy()
    start = (
        (octets[:, 0] << np.uint64(24))
        | (octets[:, 1] << np.uint64(16))
        | (octets[:, 2] << np.uint64(8))
        | octets[:, 3]
    )
    plen = (
        (parts[1] if 1 in parts else pd.Series("32", index=parts.index))
        .fillna("32")
        .astype("uint64")
        .to_numpy()
    )
    size = np.uint64(1) << (np.uint64(32) - plen)
    start = start & ~(size - np.uint64(1))  # clear host bits
    end = start + size - np.uint64(1)
    country = frame["country_code"].to_numpy()
    asn = _asn(frame["asn"])
    order = np.argsort(start, kind="stable")
    start, end, country, asn = start[order], end[order], country[order], asn[order]
    if len(start) > 1 and bool((start[1:] <= end[:-1]).any()):
        raise ValueError("IPv4 ranges overlap")
    keep = np.ones(len(start), dtype=bool)
    keep[1:] = (
        (start[1:] != end[:-1] + np.uint64(1))
        | (country[1:] != country[:-1])
        | (asn[1:] != asn[:-1])
    )
    last = np.r_[np.flatnonzero(keep)[1:] - 1, len(start) - 1]
    return pd.DataFrame(
        {
            "start": start[keep].astype("int64"),
            "end": end[last].astype("int64"),
            "country_code": country[keep],
            "asn": asn[keep],
        }
    )


def _v6(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for network, country, asn in zip(
        frame["network"], frame["country_code"], _asn(frame["asn"]), strict=True
    ):
        net = ipaddress.ip_network(network, strict=False)
        rows.append((int(net.network_address), int(net.broadcast_address), country, int(asn)))
    rows.sort(key=lambda r: r[0])
    starts: list[int] = []
    ends: list[int] = []
    countries: list[str] = []
    asns: list[int] = []
    for start, end, country, asn in rows:
        if ends:
            if start <= ends[-1]:
                raise ValueError("IPv6 ranges overlap")
            if start == ends[-1] + 1 and countries[-1] == country and asns[-1] == asn:
                ends[-1] = end
                continue
        starts.append(start)
        ends.append(end)
        countries.append(country)
        asns.append(asn)
    halves = {
        name: [split128(n) for n in values] for name, values in (("start", starts), ("end", ends))
    }
    return pd.DataFrame(
        {
            "start_hi": pd.Series([h for h, _ in halves["start"]], dtype="int64"),
            "start_lo": pd.Series([lo for _, lo in halves["start"]], dtype="int64"),
            "end_hi": pd.Series([h for h, _ in halves["end"]], dtype="int64"),
            "end_lo": pd.Series([lo for _, lo in halves["end"]], dtype="int64"),
            "country_code": countries,
            "asn": pd.Series(asns, dtype="int64"),
        }
    )


def build_ranges(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(IPv4, IPv6) range tables from a frame with `network`, `country_code` and `asn` columns."""
    is_v6 = frame["network"].str.contains(":", regex=False)
    return _v4(frame[~is_v6]), _v6(frame[is_v6])
