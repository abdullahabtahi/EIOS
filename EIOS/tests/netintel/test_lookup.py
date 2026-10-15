"""The snapshot answers one address at a time, from memory, and says what it does not know."""

import pytest

from eios.netintel.lookup import NetSnapshot, SourceStamp
from eios.netintel.sources import ListEntry

STAMPS = (SourceStamp("IPinfo Lite", "2026-10-15"), SourceStamp("Tor exit list", "2026-10-15"))


def _snapshot() -> NetSnapshot:
    return NetSnapshot.from_rows(
        v4=[
            (16777216, 16777471, "AU", 13335),  # 1.0.0.0 - 1.0.0.255
            (3232235520, 3232235775, "XX", 1),  # 192.168.0.x: must never be consulted
            (3070000128, 3070000383, "NL", 205100),  # 183.xx
        ],
        v6=[(0x26064700000000000000000000000000, 0x26064700FFFFFFFFFFFFFFFFFFFFFFFF, "NL", 64500)],
        asns={
            13335: ("Cloudflare, Inc.", "cloudflare.com"),
            205100: ("Example Hosting", "example.net"),
            64500: ("Doc Net", "doc.example"),
        },
        countries={"AU": "Australia", "NL": "The Netherlands", "XX": "Nowhere"},
        entries=[
            ListEntry("tor_exit", "1.0.0.7/32", ""),
            ListEntry("cloud", "1.0.0.0/24", "Amazon Web Services, EC2, ap-southeast-2"),
            ListEntry(
                "cloud", "1.0.0.0/16", "Google Cloud, asia-southeast1"
            ),  # nested inside nothing, contains the /24
            ListEntry("datacenter", "2606:4700::/48", ""),
        ],
        stamps=STAMPS,
    )


def test_a_listed_address_reports_country_network_and_every_matching_list() -> None:
    r = _snapshot().lookup("1.0.0.7")
    assert r.country == ("AU", "Australia") and r.network == (
        13335,
        "Cloudflare, Inc.",
        "cloudflare.com",
    )
    assert [(m.list_name, m.detail) for m in r.matches] == [
        ("tor_exit", ""),
        ("cloud", "Amazon Web Services, EC2, ap-southeast-2"),
        ("cloud", "Google Cloud, asia-southeast1"),
    ]
    assert r.verdict == "tor_exit" and r.scope == "public" and r.version == 4


def test_range_edges_are_inclusive() -> None:
    snap = _snapshot()
    assert snap.lookup("1.0.0.0").country == ("AU", "Australia")
    assert snap.lookup("1.0.0.255").country == ("AU", "Australia")
    assert snap.lookup("1.0.1.0").country is None


def test_an_address_the_database_does_not_know_has_no_country_not_a_guess() -> None:
    r = _snapshot().lookup("8.8.8.8")
    assert (
        r.country is None and r.network is None and r.matches == [] and r.verdict == "none_listed"
    )


def test_ipv6_is_looked_up_in_its_own_table_and_lists() -> None:
    r = _snapshot().lookup("2606:4700::1")
    assert r.country == ("NL", "The Netherlands") and r.version == 6
    assert [m.list_name for m in r.matches] == ["datacenter"] and r.verdict == "datacenter"
    assert _snapshot().lookup("2606:4701::1").country is None


def test_private_and_reserved_addresses_are_not_looked_up_at_all() -> None:
    for text, scope in [
        ("192.168.0.9", "private"),
        ("127.0.0.1", "loopback"),
        ("169.254.1.1", "link_local"),
        ("0.0.0.0", "unspecified"),  # noqa: S104
        ("224.0.0.1", "multicast"),
    ]:
        r = _snapshot().lookup(text)
        assert (
            r.scope == scope and r.country is None and r.matches == [] and r.verdict == "not_public"
        ), text


def test_an_ipv4_mapped_ipv6_address_is_read_as_the_ipv4_address() -> None:
    r = _snapshot().lookup("::ffff:1.0.0.7")
    assert r.address == "1.0.0.7" and r.version == 4 and r.verdict == "tor_exit"


def test_the_verdict_follows_a_fixed_precedence() -> None:
    snap = NetSnapshot.from_rows(
        v4=[],
        v6=[],
        asns={},
        countries={},
        stamps=STAMPS,
        entries=[
            ListEntry("datacenter", "5.5.5.0/24", ""),
            ListEntry("cloud", "5.5.5.0/24", "x"),
            ListEntry("vpn", "5.5.5.0/24", ""),
        ],
    )
    assert snap.lookup("5.5.5.5").verdict == "vpn"  # tor_exit > vpn > cloud > datacenter


def test_garbage_is_refused() -> None:
    for bad in ["", "hello", "1.2.3", "1.2.3.4/24", "999.1.1.1"]:
        with pytest.raises(ValueError):
            _snapshot().lookup(bad)


def test_the_report_carries_the_snapshot_stamps() -> None:
    assert _snapshot().lookup("1.0.0.7").sources == STAMPS


def test_a_list_with_no_networks_of_the_family_is_named_so_it_cannot_rule_the_address_out() -> None:
    snap = _snapshot()
    # this fixture has no IPv4 network on the VPN or datacenter lists, and no IPv6 on Tor, VPN or cloud
    assert snap.lookup("1.0.0.7").uncovered == ("vpn", "datacenter")
    assert snap.lookup("2606:4700::1").uncovered == ("tor_exit", "vpn", "cloud")
