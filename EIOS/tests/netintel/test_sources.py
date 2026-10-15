"""Parsers for the public lists behind the address check: pure functions over the files' own formats."""

import json

from eios.netintel.sources import (
    ListEntry,
    parse_aws,
    parse_cidr_list,
    parse_gcp,
    parse_tor,
)


def test_tor_list_is_one_address_per_line_and_skips_noise() -> None:
    text = "171.25.193.25\n\n# comment\n80.67.167.81\nnot-an-address\n2a0b:f4c2::1\n"
    entries, skipped = parse_tor(text)
    assert [e.network for e in entries] == [
        "171.25.193.25/32",
        "80.67.167.81/32",
        "2a0b:f4c2::1/128",
    ]
    assert all(e.list_name == "tor_exit" and e.detail == "" for e in entries)
    assert skipped == 1  # reported, never silently dropped


def test_aws_ranges_carry_the_service_and_region_of_each_prefix() -> None:
    payload = {
        "prefixes": [
            {"ip_prefix": "3.5.140.0/22", "region": "ap-northeast-2", "service": "AMAZON"}
        ],
        "ipv6_prefixes": [
            {"ipv6_prefix": "2600:1f00::/24", "region": "us-east-1", "service": "EC2"}
        ],
    }
    entries, skipped = parse_aws(json.dumps(payload))
    assert entries == [
        ListEntry("cloud", "3.5.140.0/22", "Amazon Web Services, AMAZON, ap-northeast-2"),
        ListEntry("cloud", "2600:1f00::/24", "Amazon Web Services, EC2, us-east-1"),
    ]
    assert skipped == 0


def test_google_cloud_ranges_carry_service_and_scope() -> None:
    payload = {
        "prefixes": [
            {"ipv4Prefix": "34.80.0.0/15", "service": "Google Cloud", "scope": "asia-east1"},
            {"ipv6Prefix": "2600:1900::/35", "service": "Google Cloud", "scope": "us-central1"},
        ]
    }
    entries, _ = parse_gcp(json.dumps(payload))
    assert entries == [
        ListEntry("cloud", "34.80.0.0/15", "Google Cloud, asia-east1"),
        ListEntry("cloud", "2600:1900::/35", "Google Cloud, us-central1"),
    ]


def test_cidr_lists_are_tagged_with_the_list_they_came_from() -> None:
    entries, skipped = parse_cidr_list("1.2.3.0/24\n\n9.9.9.0/24\nbogus\n", "vpn")
    assert [(e.list_name, e.network) for e in entries] == [
        ("vpn", "1.2.3.0/24"),
        ("vpn", "9.9.9.0/24"),
    ]
    assert skipped == 1


def test_a_prefix_with_host_bits_set_is_normalised_not_rejected() -> None:
    entries, skipped = parse_cidr_list("10.1.2.3/24\n", "datacenter")
    assert [e.network for e in entries] == ["10.1.2.0/24"] and skipped == 0
