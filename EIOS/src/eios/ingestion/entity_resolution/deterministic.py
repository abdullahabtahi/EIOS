"""Deterministic exact key entity resolution using connected components (US4)."""

from dataclasses import dataclass, field
import threading
from uuid import uuid4


@dataclass
class ClientProfileRecord:
    """Input record from fragmented platform accounts."""
    account_id: str
    platform: str
    tax_id: str | None = None
    email_hash: str | None = None
    phone_hash: str | None = None
    full_name: str | None = None
    device_id: str | None = None
    ip_address: str | None = None


class DeterministicResolver:
    """Builds connected components over high-entropy cryptographic hashes."""

    def __init__(self) -> None:
        self._key_to_canonical: dict[str, str] = {}
        self._account_to_canonical: dict[str, str] = {}
        self._lock = threading.Lock()

    def _extract_keys(self, record: ClientProfileRecord) -> list[str]:
        keys = []
        if record.tax_id:
            keys.append(f"tax:{record.tax_id.strip().upper()}")
        if record.email_hash:
            keys.append(f"email:{record.email_hash.strip().lower()}")
        if record.phone_hash:
            keys.append(f"phone:{record.phone_hash.strip()}")
        return keys

    def resolve(self, record: ClientProfileRecord) -> str:
        """Resolve a record to a canonical ID based on exact matching keys."""
        with self._lock:
            # Check if account_id already mapped
            if record.account_id in self._account_to_canonical:
                return self._account_to_canonical[record.account_id]

            keys = self._extract_keys(record)
            existing_canonical: str | None = None

            for k in keys:
                if k in self._key_to_canonical:
                    existing_canonical = self._key_to_canonical[k]
                    break

            canonical_id = existing_canonical or f"scv_{uuid4().hex[:12]}"

            # Map all present keys to this canonical_id
            for k in keys:
                self._key_to_canonical[k] = canonical_id

            self._account_to_canonical[record.account_id] = canonical_id
            return canonical_id

    def get_canonical_for_account(self, account_id: str) -> str | None:
        """Lookup canonical ID for a specific account."""
        with self._lock:
            return self._account_to_canonical.get(account_id)
