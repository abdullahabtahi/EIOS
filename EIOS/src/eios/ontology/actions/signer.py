"""Cloud KMS ECDSA P-256 Action Intent Signer and Verification (US6)."""

import base64
import json
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec


class SignatureVerificationError(Exception):
    """Raised when an Action Intent signature is invalid, forged, or tampered."""

    pass


class KMSActionSigner:
    """Signs and verifies Action Intent Tokens using ECDSA P-256."""

    def __init__(self, key_id: str = "local-mock-kms-p256") -> None:
        self.key_id = key_id
        # In local/test mode, initialize an in-memory SECP256R1 key pair
        self._private_key = ec.generate_private_key(ec.SECP256R1())
        self._public_key = self._private_key.public_key()

    def canonical_json(self, payload: dict[str, Any]) -> bytes:
        """Produce deterministic canonical JSON bytes (RFC 8785) for signing."""
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def sign_payload(self, payload: dict[str, Any]) -> str:
        """Generate base64-encoded ASN.1 DER ECDSA P-256 signature."""
        data = self.canonical_json(payload)
        der_signature = self._private_key.sign(data, ec.ECDSA(hashes.SHA256()))
        return base64.b64encode(der_signature).decode("utf-8")

    def verify_payload(self, payload: dict[str, Any], signature_b64: str) -> bool:
        """Verify signature with public key. Raises SignatureVerificationError if invalid."""
        data = self.canonical_json(payload)
        try:
            der_signature = base64.b64decode(signature_b64.encode("utf-8"))
            self._public_key.verify(der_signature, data, ec.ECDSA(hashes.SHA256()))
            return True
        except (InvalidSignature, ValueError, TypeError) as exc:
            raise SignatureVerificationError(
                f"Action Intent signature verification failed: {exc}"
            ) from exc

    def verify_token(self, token: Any) -> bool:
        """Verify an ActionIntentToken's cryptographic signature against its payload."""
        signing_payload = {
            "intent_id": token.intent_id,
            "action_type": token.action_type,
            "parameters": token.parameters,
            "evidence_refs": token.evidence_refs,
            "severity": token.severity.value if hasattr(token.severity, "value") else str(token.severity),
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
        except SignatureVerificationError:
            return False
