"""Live Cloud KMS signing smoke test (marker: requires_cloud)."""

import os

import pytest

from eios.ontology.actions.signer import CloudKMSActionSigner, SignatureVerificationError

pytestmark = pytest.mark.requires_cloud


@pytest.mark.skipif(
    not (os.getenv("EIOS_KMS_KEY_VERSION") and os.getenv("EIOS_TEST_CLOUD") == "1"),
    reason="set EIOS_KMS_KEY_VERSION and EIOS_TEST_CLOUD=1 to call Cloud KMS",
)
def test_kms_signature_round_trips_and_detects_tampering() -> None:
    signer = CloudKMSActionSigner(os.environ["EIOS_KMS_KEY_VERSION"])
    payload = {"intent_id": "live-smoke", "action_type": "StageAccountFreeze", "nonce": "n1"}
    signature = signer.sign_payload(payload)
    assert signer.verify_payload(payload, signature) is True
    with pytest.raises(SignatureVerificationError):
        signer.verify_payload({**payload, "nonce": "n2"}, signature)
    # A second instance (a new process or Cloud Run instance) verifies the same signature.
    assert CloudKMSActionSigner(os.environ["EIOS_KMS_KEY_VERSION"]).verify_payload(
        payload, signature
    )
