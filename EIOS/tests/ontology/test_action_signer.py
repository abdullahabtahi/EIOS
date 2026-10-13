"""Test Cloud KMS ECDSA P-256 Action Signer and Verification (T037)."""

import pytest

from eios.ontology.actions.signer import LocalDevActionSigner, SignatureVerificationError


def test_action_signer_generates_and_verifies_valid_signature():
    signer = LocalDevActionSigner()  # uses in-memory mock key pair by default
    payload = {
        "intent_id": "c62040b2-2974-4b47-975c-42cb1a3a3e6f",
        "action_type": "FreezeAccount",
        "parameters": {"client_id": "C-1001", "reason_code": "MIRROR_TRADING"},
        "nonce": "a1b2c3d4e5f60718",
        "expires_at": "2026-10-05T18:30:00Z",
    }

    sig_b64 = signer.sign_payload(payload)
    assert isinstance(sig_b64, str)
    assert len(sig_b64) > 30

    # Verification must succeed
    assert signer.verify_payload(payload, sig_b64) is True


def test_action_signer_detects_tampered_payload():
    signer = LocalDevActionSigner()
    payload = {
        "intent_id": "c62040b2-2974-4b47-975c-42cb1a3a3e6f",
        "action_type": "FreezeAccount",
        "parameters": {"client_id": "C-1001"},
        "nonce": "a1b2c3d4e5f60718",
    }
    sig_b64 = signer.sign_payload(payload)

    # Tamper payload
    tampered_payload = dict(payload)
    tampered_payload["parameters"] = {"client_id": "C-9999"}

    with pytest.raises(SignatureVerificationError):
        signer.verify_payload(tampered_payload, sig_b64)
