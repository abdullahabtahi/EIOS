"""Tests for Deterministic HMAC-SHA256 Token Vault (US5)."""

import pytest

from eios.ingestion.vault import TokenVault


def test_deterministic_tokenization():
    vault = TokenVault(master_salt=b"test-salt-secret-32bytes-01234567")

    email = "trader_john@deriv.com"
    token1 = vault.tokenize("email", email)
    token2 = vault.tokenize("email", email)

    assert token1 == token2
    assert token1.startswith("tok_client_")
    assert len(token1) == len("tok_client_") + 16


def test_distinct_tokens_for_different_inputs():
    vault = TokenVault(master_salt=b"test-salt-secret-32bytes-01234567")

    t1 = vault.tokenize("email", "trader_john@deriv.com")
    t2 = vault.tokenize("email", "trader_alice@deriv.com")
    t3 = vault.tokenize("tax_id", "trader_john@deriv.com")  # Different field context

    assert t1 != t2
    assert t1 != t3


def test_reversibility_with_vault():
    vault = TokenVault(master_salt=b"test-salt-secret-32bytes-01234567")

    original = "+60123456789"
    token = vault.tokenize("phone", original)

    recovered = vault.detokenize(token)
    assert recovered == original


def test_detokenize_nonexistent_raises_key_error():
    vault = TokenVault(master_salt=b"test-salt-secret-32bytes-01234567")
    with pytest.raises(KeyError):
        vault.detokenize("tok_client_0000000000000000")
