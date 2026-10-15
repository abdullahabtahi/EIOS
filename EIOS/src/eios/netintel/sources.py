"""The public lists behind the address check, parsed from the files' own formats.

[EXTERNAL] Tor exit relays (Tor Project bulk exit list), cloud provider ranges (AWS `ip-ranges.json`, Google Cloud
`cloud.json`), and the community-maintained VPN and datacenter ranges of X4BNet/lists_vpn (MIT). Every parser returns
the entries and the number of lines it could not read, so a malformed feed is reported, never dropped quietly. These
are lists of networks, not verdicts: an address missing from all of them is "not on any list we hold".
"""

from __future__ import annotations

import ipaddress
import json
import time
import urllib.request
from dataclasses import dataclass

LIST_TOR = "tor_exit"
LIST_VPN = "vpn"
LIST_CLOUD = "cloud"
LIST_DATACENTER = "datacenter"

TOR_URL = "https://check.torproject.org/torbulkexitlist"
AWS_URL = "https://ip-ranges.amazonaws.com/ip-ranges.json"
GCP_URL = "https://www.gstatic.com/ipranges/cloud.json"
VPN_URL = "https://raw.githubusercontent.com/X4BNet/lists_vpn/main/output/vpn/ipv4.txt"
DATACENTER_URL = (
    "https://raw.githubusercontent.com/X4BNet/lists_vpn/main/output/datacenter/ipv4.txt"
)
_ATTEMPTS = 3
_TIMEOUT_S = 60


@dataclass(frozen=True)
class ListEntry:
    list_name: str
    network: str  # CIDR, host bits cleared
    detail: (
        str  # what the list says about it (provider, service, region); empty when it says nothing
    )


def _network(text: str) -> str | None:
    try:
        return str(ipaddress.ip_network(text.strip(), strict=False))
    except ValueError:
        return None


def parse_tor(text: str) -> tuple[list[ListEntry], int]:
    entries: list[ListEntry] = []
    skipped = 0
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        network = _network(line) if "/" not in line else None
        if network is None:
            skipped += 1
            continue
        entries.append(ListEntry(LIST_TOR, network, ""))
    return entries, skipped


def parse_cidr_list(text: str, list_name: str) -> tuple[list[ListEntry], int]:
    entries: list[ListEntry] = []
    skipped = 0
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        network = _network(line)
        if network is None:
            skipped += 1
            continue
        entries.append(ListEntry(list_name, network, ""))
    return entries, skipped


def parse_aws(text: str) -> tuple[list[ListEntry], int]:
    data = json.loads(text)
    entries: list[ListEntry] = []
    skipped = 0
    for key, field in (("prefixes", "ip_prefix"), ("ipv6_prefixes", "ipv6_prefix")):
        for row in data.get(key, []):
            network = _network(str(row.get(field, "")))
            if network is None:
                skipped += 1
                continue
            detail = f"Amazon Web Services, {row.get('service', '')}, {row.get('region', '')}"
            entries.append(ListEntry(LIST_CLOUD, network, detail))
    return entries, skipped


def parse_gcp(text: str) -> tuple[list[ListEntry], int]:
    data = json.loads(text)
    entries: list[ListEntry] = []
    skipped = 0
    for row in data.get("prefixes", []):
        network = _network(str(row.get("ipv4Prefix") or row.get("ipv6Prefix") or ""))
        if network is None:
            skipped += 1
            continue
        entries.append(
            ListEntry(LIST_CLOUD, network, f"{row.get('service', '')}, {row.get('scope', '')}")
        )
    return entries, skipped


def fetch_text(url: str) -> str:
    """One GET with a few retries: the Tor service in particular drops a connection now and then."""
    last: Exception | None = None
    for attempt in range(_ATTEMPTS):
        try:
            with urllib.request.urlopen(url, timeout=_TIMEOUT_S) as response:  # noqa: S310 (fixed https URLs above)
                return str(response.read().decode("utf-8"))
        except OSError as exc:
            last = exc
            time.sleep(2**attempt)
    raise RuntimeError(f"could not read {url}: {last}")
