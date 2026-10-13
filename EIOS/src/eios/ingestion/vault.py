"""Deterministic HMAC-SHA256 Token Vault with AES-256-GCM encryption for Marking P fields (US5)."""

import hashlib
import hmac
import logging
import os
import threading
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from eios.contracts.base import DataProductEnum

_LOG = logging.getLogger("eios.ingestion.vault")

SALT_ENV = "EIOS_HMAC_SALT"
ENVIRONMENT_ENV = "EIOS_ENVIRONMENT"
LOCAL_ENVIRONMENTS = frozenset({"dev", "test"})
MIN_DEPLOYED_SALT_BYTES = 32
# Local development and tests only. A deployed environment must supply its own salt: a pseudonym keyed by
# a constant in source can be recomputed by anyone who can read the repository.
DEV_ONLY_SALT = b"eios-dev-only-salt-not-for-deployed-use"

MARKING_P_FIELDS: dict[DataProductEnum, set[str]] = {
    DataProductEnum.CLIENT_360: {"tax_id", "full_name", "email", "phone"},
    DataProductEnum.PARTNER_COMMS: {"text"},  # When marked as sensitive text
}


def resolve_master_salt(configured: str | None, environment: str | None = None) -> bytes:
    """The vault key material: the configured salt, or a dev-only fallback in dev/test, never otherwise."""
    env = environment if environment is not None else os.getenv(ENVIRONMENT_ENV, "dev")
    salt = (configured or "").strip()
    if env in LOCAL_ENVIRONMENTS and not salt:
        _LOG.warning("%s is not set; using the dev-only token vault salt (%s)", SALT_ENV, env)
        return DEV_ONLY_SALT
    if not salt:
        raise RuntimeError(f"{SALT_ENV} must be set in the '{env}' environment (Secret Manager).")
    if env not in LOCAL_ENVIRONMENTS and len(salt.encode()) < MIN_DEPLOYED_SALT_BYTES:
        raise RuntimeError(
            f"{SALT_ENV} must be at least {MIN_DEPLOYED_SALT_BYTES} bytes in the '{env}' environment."
        )
    return salt.encode()


class TokenVault:
    """Manages deterministic HMAC-SHA256 blind indexing and AES-256-GCM encrypted reversibility."""

    def __init__(self, master_salt: bytes | None = None) -> None:
        self.master_salt = master_salt or os.urandom(32)
        # 256-bit AES key derived from salt for reversible store
        self._aes_key = hashlib.sha256(self.master_salt + b"::aes_key::").digest()
        self._aesgcm = AESGCM(self._aes_key)

        # Token -> (nonce, ciphertext)
        self._vault_store: dict[str, tuple[bytes, bytes]] = {}
        self._lock = threading.Lock()

    def tokenize(self, field_context: str, raw_value: str) -> str:
        """Deterministically tokenize a PII value into tok_client_<hex16>."""
        if not raw_value:
            return raw_value

        norm_val = raw_value.strip()
        data = f"{field_context.lower()}:{norm_val}".encode()
        h = hmac.new(self.master_salt, data, hashlib.sha256)
        token = f"tok_client_{h.hexdigest()[:16]}"

        nonce = os.urandom(12)
        ciphertext = self._aesgcm.encrypt(nonce, norm_val.encode("utf-8"), None)

        with self._lock:
            self._vault_store[token] = (nonce, ciphertext)

        return token

    def detokenize(self, token: str) -> str:
        """Reverse token to original value using vault key."""
        with self._lock:
            if token not in self._vault_store:
                raise KeyError(f"Token {token} not found in TokenVault")
            nonce, ciphertext = self._vault_store[token]

        plaintext_bytes = self._aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext_bytes.decode("utf-8")

    def pseudonymize_payload(
        self, product_name: DataProductEnum, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Transform all Marking P fields into surrogate tokens."""
        fields_to_tokenize = MARKING_P_FIELDS.get(product_name, set())
        if not fields_to_tokenize:
            return dict(payload)

        sanitized = dict(payload)
        for field_name in fields_to_tokenize:
            if field_name in sanitized and sanitized[field_name] is not None:
                val = str(sanitized[field_name])
                # Only tokenize if not already tokenized
                if not val.startswith("tok_client_"):
                    sanitized[field_name] = self.tokenize(field_name, val)

        return sanitized
