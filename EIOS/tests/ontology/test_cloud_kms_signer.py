"""CloudKMSActionSigner signs with a KMS key version and verifies against its public key."""

import hashlib
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import Prehashed

from eios.ontology.actions.signer import (
    CloudKMSActionSigner,
    LocalDevActionSigner,
    SignatureVerificationError,
    default_action_signer,
)

KEY_VERSION = "projects/p/locations/global/keyRings/r/cryptoKeys/k/cryptoKeyVersions/1"
PAYLOAD = {"intent_id": "i-1", "action_type": "StageAccountFreeze", "nonce": "n1"}


def _fake_kms() -> MagicMock:
    """A KMS client whose key lives in this process, mimicking asymmetric_sign/get_public_key."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    pem = (
        private_key.public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )

    def asymmetric_sign(request: dict) -> SimpleNamespace:
        assert request["name"] == KEY_VERSION
        digest = request["digest"]["sha256"]
        signature = private_key.sign(digest, ec.ECDSA(Prehashed(hashes.SHA256())))
        return SimpleNamespace(signature=signature, name=KEY_VERSION)

    client = MagicMock()
    client.asymmetric_sign.side_effect = asymmetric_sign
    client.get_public_key.return_value = SimpleNamespace(pem=pem, name=KEY_VERSION)
    return client


def test_sign_sends_only_the_sha256_digest_and_verifies() -> None:
    client = _fake_kms()
    signer = CloudKMSActionSigner(KEY_VERSION, client=client)
    signature = signer.sign_payload(PAYLOAD)
    sent = client.asymmetric_sign.call_args.kwargs["request"]
    assert sent["digest"]["sha256"] == hashlib.sha256(signer.canonical_json(PAYLOAD)).digest()
    assert signer.verify_payload(PAYLOAD, signature) is True


def test_tampered_payload_fails_verification() -> None:
    signer = CloudKMSActionSigner(KEY_VERSION, client=_fake_kms())
    signature = signer.sign_payload(PAYLOAD)
    with pytest.raises(SignatureVerificationError):
        signer.verify_payload({**PAYLOAD, "action_type": "Other"}, signature)


def test_signature_survives_a_new_signer_instance() -> None:
    client = _fake_kms()
    signature = CloudKMSActionSigner(KEY_VERSION, client=client).sign_payload(PAYLOAD)
    assert CloudKMSActionSigner(KEY_VERSION, client=client).verify_payload(PAYLOAD, signature)


def test_kms_failure_is_a_typed_error_not_a_fake_signature() -> None:
    client = _fake_kms()
    client.asymmetric_sign.side_effect = RuntimeError("permission denied")
    with pytest.raises(SignatureVerificationError, match="KMS signing failed"):
        CloudKMSActionSigner(KEY_VERSION, client=client).sign_payload(PAYLOAD)


def test_public_key_is_fetched_once() -> None:
    client = _fake_kms()
    signer = CloudKMSActionSigner(KEY_VERSION, client=client)
    signature = signer.sign_payload(PAYLOAD)
    signer.verify_payload(PAYLOAD, signature)
    signer.verify_payload(PAYLOAD, signature)
    assert client.get_public_key.call_count == 1


def test_factory_uses_kms_when_key_version_is_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EIOS_KMS_KEY_VERSION", KEY_VERSION)
    monkeypatch.setattr("eios.ontology.actions.signer._kms_client", lambda: _fake_kms())
    assert isinstance(default_action_signer(), CloudKMSActionSigner)


def test_factory_allows_local_signer_only_in_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EIOS_KMS_KEY_VERSION", raising=False)
    monkeypatch.setenv("EIOS_ENVIRONMENT", "dev")
    assert isinstance(default_action_signer(), LocalDevActionSigner)


@pytest.mark.parametrize("environment", ["stage", "prod-like"])
def test_factory_refuses_local_signer_outside_dev(
    monkeypatch: pytest.MonkeyPatch, environment: str
) -> None:
    monkeypatch.delenv("EIOS_KMS_KEY_VERSION", raising=False)
    monkeypatch.setenv("EIOS_ENVIRONMENT", environment)
    with pytest.raises(RuntimeError, match="EIOS_KMS_KEY_VERSION"):
        default_action_signer()
