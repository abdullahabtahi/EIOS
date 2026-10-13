"""Action Intent signing: Cloud KMS ECDSA P-256 in deployed environments, a local key in dev."""

import base64
import hashlib
import json
import logging
import os
from typing import Any, Protocol

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

_LOG = logging.getLogger("eios.ontology.actions.signer")

KMS_KEY_VERSION_ENV = "EIOS_KMS_KEY_VERSION"
ENVIRONMENT_ENV = "EIOS_ENVIRONMENT"
LOCAL_SIGNER_ENVIRONMENTS = frozenset({"dev", "test"})


class SignatureVerificationError(Exception):
    """Raised when an Action Intent signature is invalid, forged, tampered or cannot be produced."""

    pass


class ActionSigner(Protocol):
    key_id: str

    def canonical_json(self, payload: dict[str, Any]) -> bytes: ...
    def sign_payload(self, payload: dict[str, Any]) -> str: ...
    def verify_payload(self, payload: dict[str, Any], signature_b64: str) -> bool: ...
    def verify_token(self, token: Any) -> bool: ...


class _TokenVerifyMixin:
    """Shared canonicalisation and token verification for every signer."""

    def canonical_json(self, payload: dict[str, Any]) -> bytes:
        """Produce deterministic canonical JSON bytes (RFC 8785) for signing."""
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def verify_payload(
        self, payload: dict[str, Any], signature_b64: str
    ) -> bool:  # pragma: no cover
        raise NotImplementedError

    def verify_token(self, token: Any) -> bool:
        """Verify an ActionIntentToken's cryptographic signature against its payload."""
        signing_payload = {
            "intent_id": token.intent_id,
            "action_type": token.action_type,
            "parameters": token.parameters,
            "evidence_refs": token.evidence_refs,
            "severity": token.severity.value
            if hasattr(token.severity, "value")
            else str(token.severity),
            "nonce": token.nonce,
            "issued_at": token.issued_at.isoformat(),
            "expires_at": token.expires_at.isoformat(),
            "requester_agent_id": token.requester_agent_id,
        }
        if getattr(token, "propensity_score", None) is not None:
            signing_payload["propensity_score"] = token.propensity_score
        if getattr(token, "causal_context", None):
            signing_payload["causal_context"] = token.causal_context

        try:
            return self.verify_payload(signing_payload, token.signature)
        except SignatureVerificationError as exc:
            _LOG.warning("action intent %s failed signature verification: %s", token.intent_id, exc)
            return False


def _verify_with_public_key(
    public_key: ec.EllipticCurvePublicKey, data: bytes, signature_b64: str
) -> bool:
    try:
        der_signature = base64.b64decode(signature_b64.encode("utf-8"))
        public_key.verify(der_signature, data, ec.ECDSA(hashes.SHA256()))
        return True
    except (InvalidSignature, ValueError, TypeError) as exc:
        raise SignatureVerificationError(
            f"Action Intent signature verification failed: {exc}"
        ) from exc


class LocalDevActionSigner(_TokenVerifyMixin):
    """In-memory P-256 key for dev and tests only. It is NOT Cloud KMS: the key dies with the process."""

    def __init__(self, key_id: str = "local-dev-p256") -> None:
        self.key_id = key_id
        self._private_key = ec.generate_private_key(ec.SECP256R1())
        self._public_key = self._private_key.public_key()

    def sign_payload(self, payload: dict[str, Any]) -> str:
        """Generate base64-encoded ASN.1 DER ECDSA P-256 signature."""
        der_signature = self._private_key.sign(
            self.canonical_json(payload), ec.ECDSA(hashes.SHA256())
        )
        return base64.b64encode(der_signature).decode("utf-8")

    def verify_payload(self, payload: dict[str, Any], signature_b64: str) -> bool:
        return _verify_with_public_key(
            self._public_key, self.canonical_json(payload), signature_b64
        )


def _kms_client() -> Any:
    from google.cloud import kms

    return kms.KeyManagementServiceClient()


class CloudKMSActionSigner(_TokenVerifyMixin):
    """Signs with a Cloud KMS asymmetric key version (EC_SIGN_P256_SHA256). The private key never leaves KMS."""

    def __init__(self, key_version_name: str, client: Any = None) -> None:
        self.key_id = key_version_name
        self._client = client if client is not None else _kms_client()
        self._public_key: ec.EllipticCurvePublicKey | None = None

    def sign_payload(self, payload: dict[str, Any]) -> str:
        digest = hashlib.sha256(self.canonical_json(payload)).digest()
        try:
            response = self._client.asymmetric_sign(
                request={"name": self.key_id, "digest": {"sha256": digest}}
            )
        except Exception as exc:
            raise SignatureVerificationError(f"KMS signing failed: {type(exc).__name__}") from exc
        return base64.b64encode(response.signature).decode("utf-8")

    def _get_public_key(self) -> ec.EllipticCurvePublicKey:
        if self._public_key is None:
            try:
                pem = self._client.get_public_key(request={"name": self.key_id}).pem
                key = serialization.load_pem_public_key(pem.encode("utf-8"))
            except Exception as exc:
                raise SignatureVerificationError(
                    f"KMS public key unavailable: {type(exc).__name__}"
                ) from exc
            if not isinstance(key, ec.EllipticCurvePublicKey):
                raise SignatureVerificationError("KMS key is not an elliptic-curve key")
            self._public_key = key
        return self._public_key

    def verify_payload(self, payload: dict[str, Any], signature_b64: str) -> bool:
        return _verify_with_public_key(
            self._get_public_key(), self.canonical_json(payload), signature_b64
        )


def default_action_signer() -> ActionSigner:
    """Cloud KMS when EIOS_KMS_KEY_VERSION is set; a local key only in dev or test; otherwise fail startup."""
    key_version = os.getenv(KMS_KEY_VERSION_ENV)
    if key_version:
        return CloudKMSActionSigner(key_version, client=_kms_client())
    environment = os.getenv(ENVIRONMENT_ENV, "dev")
    if environment not in LOCAL_SIGNER_ENVIRONMENTS:
        raise RuntimeError(
            f"{KMS_KEY_VERSION_ENV} must be set in the '{environment}' environment; "
            "refusing to sign Action Intents with a local key"
        )
    return LocalDevActionSigner()
