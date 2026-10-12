"""Tests for synthetic PII anonymity and real competitor name suppression (SC-003)."""

import pytest
from eios.foundry.rng import DeterministicRNG
from eios.foundry.universe import GlobalEntityUniverse
from eios.foundry.generators.client import ClientDataGenerator


REAL_BROKER_BLACKLIST = [
    "etoro",
    "plus500",
    "interactive brokers",
    "robinhood",
    "xm",
    "exness",
    "oanda",
    "ig group",
    "cmc markets",
    "saxo bank",
]


def test_pii_anonymity_and_name_generation():
    """Confirms all generated client profiles contain purely synthetic PII without real broker leaks."""
    rng = DeterministicRNG(master_seed=42)
    universe = GlobalEntityUniverse(rng=rng, client_count=200)
    generator = ClientDataGenerator(universe=universe, rng=rng)

    client_records = generator.generate_client_360()
    assert len(client_records) == 200

    for client in client_records:
        email = client["email"].lower()
        # Ensure email uses safe synthetic domains
        assert any(
            email.endswith(d)
            for d in ["@example.com", "@testmail.org", "@synthetic-mail.net", "@foundry.local"]
        ), f"Unsafe email domain detected: {email}"

        # Ensure no real broker competitor names leaked into email or IDs
        for broker in REAL_BROKER_BLACKLIST:
            assert broker not in email, f"Real broker name leaked into email: {email}"
            assert broker not in client["client_id"].lower()
            assert broker not in client["person_id"].lower()

        # Check account format
        assert client["account_id"].startswith("CR")
        assert len(client["account_id"]) >= 5
        assert isinstance(client["mt5_login_id"], int)
        assert client["mt5_login_id"] >= 10000000
