"""IPinfo's network table becomes sorted, merged, non-overlapping ranges, exactly."""

import ipaddress

import pandas as pd
import pytest

from eios.netintel.ranges import build_ranges, decode128, split128


def _frame(rows: list[tuple[str, str, str]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["network", "country_code", "asn"])


def test_ipv4_networks_become_inclusive_integer_ranges() -> None:
    v4, v6 = build_ranges(_frame([("1.0.0.0/24", "AU", "AS13335"), ("1.0.2.0/23", "CN", "")]))
    assert v4.to_dict("records") == [
        {"start": 16777216, "end": 16777471, "country_code": "AU", "asn": 13335},
        {
            "start": 16777728,
            "end": 16778239,
            "country_code": "CN",
            "asn": 0,
        },  # no ASN is 0, not a guess
    ]
    assert v6.empty


def test_contiguous_ranges_with_the_same_country_and_network_merge() -> None:
    v4, _ = build_ranges(
        _frame(
            [("1.0.1.0/24", "AU", "AS1"), ("1.0.0.0/24", "AU", "AS1"), ("1.0.2.0/24", "AU", "AS2")]
        )
    )
    assert [(r.start, r.end, r.asn) for r in v4.itertuples()] == [
        (16777216, 16777727, 1),
        (16777728, 16777983, 2),
    ]


def test_a_gap_or_a_different_country_keeps_ranges_apart() -> None:
    v4, _ = build_ranges(
        _frame(
            [("1.0.0.0/24", "AU", "AS1"), ("1.0.2.0/24", "AU", "AS1"), ("1.0.1.0/24", "NZ", "AS1")]
        )
    )
    assert len(v4) == 3


def test_ipv6_ranges_are_two_signed_halves_that_decode_to_the_exact_addresses() -> None:
    _, v6 = build_ranges(
        _frame([("2001:db9::5", "NL", "AS64501"), ("2001:db8::/32", "NL", "AS64500")])
    )
    rows = v6.to_dict("records")
    assert decode128(rows[0]["start_hi"], rows[0]["start_lo"]) == int(
        ipaddress.ip_address("2001:db8::")
    )
    assert decode128(rows[0]["end_hi"], rows[0]["end_lo"]) == int(
        ipaddress.ip_address("2001:db8:ffff:ffff:ffff:ffff:ffff:ffff")
    )
    assert (rows[0]["country_code"], rows[0]["asn"]) == ("NL", 64500)
    assert decode128(rows[1]["start_hi"], rows[1]["start_lo"]) == int(
        ipaddress.ip_address("2001:db9::5")
    )


def test_signed_halves_keep_the_numeric_order_across_the_sign_boundary() -> None:
    low, high = 1, (1 << 127) + 5  # the high one has the top bit set
    assert split128(low) < split128(high)
    assert (
        decode128(*split128(high)) == high
        and decode128(*split128(0)) == 0
        and decode128(*split128((1 << 128) - 1)) == (1 << 128) - 1
    )


def test_overlapping_input_is_refused_not_resolved_by_guessing() -> None:
    with pytest.raises(ValueError, match="overlap"):
        build_ranges(_frame([("1.0.0.0/24", "AU", "AS1"), ("1.0.0.0/25", "AU", "AS1")]))
