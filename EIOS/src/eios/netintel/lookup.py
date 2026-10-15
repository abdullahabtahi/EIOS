"""The in-memory snapshot: one address in, what the database and the public lists say about it out.

Country and network come from non-overlapping ranges found by binary search (IPv4 as integers, IPv6 as 16-byte keys).
The lists nest and overlap (a provider's /16 holds its own /24s), so each is a table keyed by prefix length and
network, probed from the most specific length to the least. An address in none of them is `none_listed`, which means
"not on any list we hold" and never "clean". Private and reserved addresses are not looked up at all.
"""

from __future__ import annotations

import ipaddress
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc

from eios.netintel.ranges import split128
from eios.netintel.sources import LIST_CLOUD, LIST_DATACENTER, LIST_TOR, LIST_VPN, ListEntry

# The strongest evidence first: a Tor exit says more than a cloud range does.
_PRECEDENCE = (LIST_TOR, LIST_VPN, LIST_CLOUD, LIST_DATACENTER)
VERDICT_NONE = "none_listed"
VERDICT_NOT_PUBLIC = "not_public"


@dataclass(frozen=True)
class SourceStamp:
    name: str
    as_of: str


@dataclass(frozen=True)
class ListMatch:
    list_name: str
    detail: str


@dataclass(frozen=True)
class AddressReport:
    address: str
    version: int
    scope: str  # public, or why the address is not looked up
    country: (
        tuple[str, str] | None
    )  # ISO code and name; None when the database does not know the address
    network: tuple[int, str, str] | None  # ASN, name, domain
    matches: list[ListMatch] = field(default_factory=list)
    verdict: str = VERDICT_NONE
    sources: tuple[SourceStamp, ...] = ()
    # Lists that hold no network of this address family: they cannot rule it out, so the report names them.
    uncovered: tuple[str, ...] = ()


def _scope(addr: ipaddress.IPv4Address | ipaddress.IPv6Address) -> str:
    if addr.is_unspecified:
        return "unspecified"
    if addr.is_loopback:
        return "loopback"
    if addr.is_link_local:
        return "link_local"
    if addr.is_multicast:
        return "multicast"
    if addr.is_private:
        return "private"
    return "public" if addr.is_global else "reserved"


_UNKNOWN_COUNTRY = 65535


@dataclass(frozen=True)
class Ranges:
    """One address family's non-overlapping ranges as compact arrays; the country is an index into the shared codes."""

    version: int
    start: np.ndarray
    end: np.ndarray
    country: (
        np.ndarray
    )  # uint16 index into `codes`; 65535 when the code is not in the country table
    asn: np.ndarray  # uint32; 0 when the database names no network


_SIGN = np.uint64(1 << 63)


def _keys_v6(high: np.ndarray, low: np.ndarray) -> np.ndarray:
    """128-bit keys as 16-byte big-endian strings, which sort as the numbers do, from signed INT64 halves."""
    out = np.empty(len(high), dtype="S16")
    halves = out.view(">u8").reshape(len(high), 2)  # fill the final buffer in place: no second copy
    halves[:, 0] = high.astype("int64").view("uint64") ^ _SIGN
    halves[:, 1] = low.astype("int64").view("uint64") ^ _SIGN
    return out


def ranges_from_arrow(table: pa.Table, version: int, codes: Sequence[str]) -> Ranges:
    """Sorted compact arrays from an Arrow table of ranges; no per-row Python objects are made."""
    if version == 4:
        start = table["start"].to_numpy().astype("uint32")
        end = table["end"].to_numpy().astype("uint32")
    else:
        start = _keys_v6(table["start_hi"].to_numpy(), table["start_lo"].to_numpy())
        end = _keys_v6(table["end_hi"].to_numpy(), table["end_lo"].to_numpy())
    index = pc.index_in(
        table["country_code"].cast(pa.string()), value_set=pa.array(list(codes), type=pa.string())
    )
    country = pc.fill_null(index, _UNKNOWN_COUNTRY).to_numpy().astype("uint16")
    asn = table["asn"].to_numpy().astype("uint32")
    if len(start) > 1 and bool((start[1:] < start[:-1]).any()):
        order = np.argsort(start, kind="stable")
        start, end, country, asn = start[order], end[order], country[order], asn[order]
    return Ranges(version, start, end, country, asn)


def ranges_from_frame(frame: pd.DataFrame, version: int, codes: Sequence[str]) -> Ranges:
    """The same from a pandas frame (the build's own output, and tests)."""
    return ranges_from_arrow(pa.Table.from_pandas(frame, preserve_index=False), version, codes)


class NetSnapshot:
    def __init__(
        self,
        v4: Ranges,
        v6: Ranges,
        codes: Sequence[str],
        asns: Mapping[int, tuple[str, str]],
        countries: Mapping[str, str],
        entries: Iterable[ListEntry],
        stamps: Sequence[SourceStamp],
    ) -> None:
        self._asns, self._countries, self._stamps = dict(asns), dict(countries), tuple(stamps)
        self._codes = tuple(codes)
        self._ranges = {4: v4, 6: v6}
        self._lists: dict[int, dict[tuple[int, int], list[ListMatch]]] = {4: {}, 6: {}}
        self._plens: dict[int, list[int]] = {4: [], 6: []}
        for entry in entries:
            net = ipaddress.ip_network(entry.network, strict=False)
            table = self._lists[net.version]
            table.setdefault((net.prefixlen, int(net.network_address)), []).append(
                ListMatch(entry.list_name, entry.detail)
            )
        for version, table in self._lists.items():
            self._plens[version] = sorted({plen for plen, _ in table}, reverse=True)
        self._uncovered = {
            v: tuple(n for n in _PRECEDENCE if n not in self.covered_lists(v)) for v in (4, 6)
        }

    @classmethod
    def from_rows(
        cls,
        v4: Sequence[tuple[int, int, str, int]],
        v6: Sequence[tuple[int, int, str, int]],
        asns: Mapping[int, tuple[str, str]],
        countries: Mapping[str, str],
        entries: Iterable[ListEntry],
        stamps: Sequence[SourceStamp],
    ) -> NetSnapshot:
        cols = ["start", "end", "country_code", "asn"]
        codes = sorted(countries)
        six = pd.DataFrame(
            [(*split128(a), *split128(b), c, n) for a, b, c, n in v6],
            columns=["start_hi", "start_lo", "end_hi", "end_lo", "country_code", "asn"],
        ).astype(
            {
                "start_hi": "int64",
                "start_lo": "int64",
                "end_hi": "int64",
                "end_lo": "int64",
                "asn": "int64",
            }
        )
        return cls(
            ranges_from_frame(
                pd.DataFrame(list(v4), columns=cols).astype(
                    {"start": "int64", "end": "int64", "asn": "int64"}
                ),
                4,
                codes,
            ),
            ranges_from_frame(six, 6, codes),
            codes,
            asns,
            countries,
            entries,
            stamps,
        )

    def covered_lists(self, version: int) -> set[str]:
        """The lists that hold at least one network of this family: a list with none cannot rule an address out."""
        return {m.list_name for matches in self._lists[version].values() for m in matches}

    def _find(self, addr: ipaddress.IPv4Address | ipaddress.IPv6Address) -> int | None:
        cols = self._ranges[addr.version]
        key = (
            np.uint32(int(addr)) if addr.version == 4 else np.bytes_(int(addr).to_bytes(16, "big"))
        )
        i = int(np.searchsorted(cols.start, key, side="right")) - 1
        return i if i >= 0 and key <= cols.end[i] else None

    def _matches(self, addr: ipaddress.IPv4Address | ipaddress.IPv6Address) -> list[ListMatch]:
        bits, value = (32, int(addr)) if addr.version == 4 else (128, int(addr))
        found: list[ListMatch] = []
        for plen in self._plens[addr.version]:
            shift = bits - plen
            found.extend(self._lists[addr.version].get((plen, (value >> shift) << shift), []))
        return found

    def lookup(self, text: str) -> AddressReport:
        addr = ipaddress.ip_address(text.strip())
        if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
            addr = addr.ipv4_mapped
        scope = _scope(addr)
        if scope != "public":
            return AddressReport(
                str(addr), addr.version, scope, None, None, [], VERDICT_NOT_PUBLIC, self._stamps
            )
        cols = self._ranges[addr.version]
        i = self._find(addr)
        country = network = None
        if i is not None:
            at = int(cols.country[i])
            code = self._codes[at] if at != _UNKNOWN_COUNTRY else ""
            country = (code, self._countries.get(code, code)) if code else None
            asn = int(cols.asn[i])
            if asn:
                name, domain = self._asns.get(asn, ("", ""))
                network = (asn, name, domain)
        matches = self._matches(addr)
        present = {m.list_name for m in matches}
        verdict = next((name for name in _PRECEDENCE if name in present), VERDICT_NONE)
        return AddressReport(
            str(addr),
            addr.version,
            scope,
            country,
            network,
            matches,
            verdict,
            self._stamps,
            self._uncovered[addr.version],
        )
