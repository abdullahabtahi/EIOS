"""The token vault salt comes from configuration and fails closed outside dev/test (R2).

A vault keyed by a constant in source makes every pseudonym recomputable by anyone who reads the repo,
so the Marking P protection would be decorative.
"""

import pytest

from eios.ingestion.config import IngestionConfig
from eios.ingestion.processor import IngestionPipeline
from eios.ingestion.router import create_ingestion_app
from eios.ingestion.vault import (
    DEV_ONLY_SALT,
    MIN_DEPLOYED_SALT_BYTES,
    TokenVault,
    resolve_master_salt,
)

STRONG_SALT = "s3cr3t-" + "x" * MIN_DEPLOYED_SALT_BYTES


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EIOS_HMAC_SALT", raising=False)
    monkeypatch.delenv("EIOS_ENVIRONMENT", raising=False)


def test_configured_salt_is_used() -> None:
    assert resolve_master_salt(STRONG_SALT, environment="prod-like") == STRONG_SALT.encode()


@pytest.mark.parametrize("environment", ["prod-like", "stage", "prod"])
def test_missing_salt_refuses_outside_dev_and_test(environment: str) -> None:
    with pytest.raises(RuntimeError, match="EIOS_HMAC_SALT"):
        resolve_master_salt(None, environment=environment)


def test_blank_salt_is_treated_as_missing() -> None:
    with pytest.raises(RuntimeError, match="EIOS_HMAC_SALT"):
        resolve_master_salt("   ", environment="prod-like")


def test_short_salt_refuses_outside_dev_and_test() -> None:
    with pytest.raises(RuntimeError, match="at least"):
        resolve_master_salt("too-short", environment="prod-like")


@pytest.mark.parametrize("environment", ["dev", "test"])
def test_dev_and_test_may_fall_back_to_the_dev_salt(environment: str) -> None:
    assert resolve_master_salt(None, environment=environment) == DEV_ONLY_SALT


def test_environment_defaults_to_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    assert resolve_master_salt(None) == DEV_ONLY_SALT
    monkeypatch.setenv("EIOS_ENVIRONMENT", "prod-like")
    with pytest.raises(RuntimeError):
        resolve_master_salt(None)


def test_config_reads_the_salt_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EIOS_HMAC_SALT", STRONG_SALT)
    assert IngestionConfig().hmac_salt == STRONG_SALT


def test_pipeline_vault_is_keyed_by_the_configured_salt() -> None:
    pipeline = IngestionPipeline(config=IngestionConfig(hmac_salt=STRONG_SALT))
    expected = TokenVault(master_salt=STRONG_SALT.encode()).tokenize("email", "a@example.com")
    assert pipeline.vault.tokenize("email", "a@example.com") == expected


def test_pipeline_vault_is_not_keyed_by_a_source_literal() -> None:
    pipeline = IngestionPipeline(config=IngestionConfig(hmac_salt=STRONG_SALT))
    from_source = TokenVault(master_salt=DEV_ONLY_SALT).tokenize("email", "a@example.com")
    assert pipeline.vault.tokenize("email", "a@example.com") != from_source


def test_ingestion_app_vault_is_keyed_by_the_configured_salt() -> None:
    app = create_ingestion_app(config=IngestionConfig(hmac_salt=STRONG_SALT))
    expected = TokenVault(master_salt=STRONG_SALT.encode()).tokenize("phone", "+60123456789")
    assert app.state.pipeline.vault.tokenize("phone", "+60123456789") == expected


def test_pipeline_refuses_to_start_deployed_without_a_salt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EIOS_ENVIRONMENT", "prod-like")
    with pytest.raises(RuntimeError, match="EIOS_HMAC_SALT"):
        IngestionPipeline(config=IngestionConfig(hmac_salt=None))
