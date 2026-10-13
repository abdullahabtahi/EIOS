"""Tests for Single Client View (SCV) Entity Resolution (US4)."""

from eios.ingestion.entity_resolution.coordinator import SCVCoordinator
from eios.ingestion.entity_resolution.deterministic import (
    ClientProfileRecord,
    DeterministicResolver,
)
from eios.ingestion.entity_resolution.probabilistic import (
    ProbabilisticLinker,
    jaro_winkler_similarity,
)


def test_jaro_winkler_similarity():
    """Verify string distance calculation."""
    assert jaro_winkler_similarity("Jonathan Doe", "Jonathan Doe") == 1.0
    assert jaro_winkler_similarity("Jonathan Doe", "Johnathan Doe") > 0.90
    assert jaro_winkler_similarity("Jonathan Doe", "Alice Smith") < 0.50


def test_deterministic_exact_key_merges():
    """Profiles sharing tax_id, phone, or email must resolve to same canonical_id."""
    resolver = DeterministicResolver()

    # Same client with 2 platform accounts (MT5 and Deriv Trader)
    r1 = ClientProfileRecord(
        account_id="MT5_1001",
        platform="MT5",
        tax_id="TAX_MY_987654",
        email_hash="hash_email_john",
        phone_hash="hash_phone_john",
        full_name="John Doe",
    )
    r2 = ClientProfileRecord(
        account_id="DT_2002",
        platform="DERIV_TRADER",
        tax_id="TAX_MY_987654",
        email_hash="hash_email_john",
        phone_hash="hash_phone_john",
        full_name="John Doe",
    )

    c1 = resolver.resolve(r1)
    c2 = resolver.resolve(r2)
    assert c1 == c2  # Must merge deterministically


def test_probabilistic_fellegi_sunter_linkage():
    """Profiles with high name similarity and matching birthdate/country link probabilistically."""
    linker = ProbabilisticLinker(threshold=0.85)

    p1 = {
        "full_name": "Alexander Hamilton",
        "dob": "1980-01-11",
        "country": "MYS",
        "device_id": "dev_macbook_01",
    }
    p2 = {
        "full_name": "Alex Hamilton",
        "dob": "1980-01-11",
        "country": "MYS",
        "device_id": "dev_macbook_01",
    }
    p3 = {
        "full_name": "Robert Vance",
        "dob": "1975-05-20",
        "country": "GBR",
        "device_id": "dev_win_99",
    }

    score_match, is_match = linker.evaluate_pair(p1, p2)
    assert is_match is True
    assert score_match >= 0.85

    score_diff, is_match_diff = linker.evaluate_pair(p1, p3)
    assert is_match_diff is False
    assert score_diff < 0.50


def test_coordinator_resolves_probabilistically_when_deterministic_keys_absent():
    """Coordinator links profiles with matching name/dob/country even when tax_id/email/phone are absent."""
    coordinator = SCVCoordinator()

    r1 = ClientProfileRecord(
        account_id="ACC_NO_TAX_1",
        platform="DERIV_TRADER",
        full_name="Alexander Hamilton",
        device_id="dedicated_phone_123",
    )
    r2 = ClientProfileRecord(
        account_id="ACC_NO_TAX_2",
        platform="MT5",
        full_name="Alex Hamilton",
        device_id="dedicated_phone_123",
    )

    c1 = coordinator.resolve_record(r1, profile_metadata={"dob": "1980-01-11", "country": "MYS"})
    c2 = coordinator.resolve_record(r2, profile_metadata={"dob": "1980-01-11", "country": "MYS"})

    assert c1 == c2  # Successfully resolved via Stage 2 probabilistic linkage!
