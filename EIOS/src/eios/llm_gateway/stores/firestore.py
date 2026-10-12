"""Firestore-backed counter and replay stores (dev uses the emulator; see docker-compose.dev.yml).

The SDK is imported lazily so that importing this module, and running without Firestore, never
needs ``google-cloud-firestore``. Authentication is ambient (application default credentials or
``FIRESTORE_EMULATOR_HOST``); these classes accept and hold no credentials.
"""

from __future__ import annotations

import importlib
import logging
from datetime import date, datetime
from types import ModuleType
from typing import Any

from eios.common.errors import BoundaryValidationError, ToolError
from eios.common.logging_redaction import redact_text
from eios.llm_gateway.replay_cache import StoredReplay
from eios.llm_gateway.stores.memory import require_aware, require_non_negative

_LOG = logging.getLogger("eios.llm_gateway")
_SDK_MODULE = "google.cloud.firestore"
DEFAULT_COUNTER_COLLECTION = "llm_gateway_counters"
DEFAULT_REPLAY_COLLECTION = "llm_gateway_replay"
TOTAL_FIELD = "tokens"


def _load_sdk() -> ModuleType:
    try:
        return importlib.import_module(_SDK_MODULE)
    except ImportError:
        raise ToolError(
            "the Firestore store needs the google-cloud-firestore package, which is not installed"
        ) from None


class _LazyClient:
    """Builds the Firestore client on first use unless one was supplied."""

    def __init__(self, project: str | None, client: Any | None) -> None:
        self._project = project
        self._client = client

    def get(self) -> Any:
        if self._client is None:
            self._client = _load_sdk().Client(project=self._project)
        return self._client


def _stored_total(snapshot: Any) -> int:
    if not snapshot.exists:
        return 0
    data = snapshot.to_dict() or {}
    total = data.get(TOTAL_FIELD, 0)
    if isinstance(total, bool) or not isinstance(total, int) or total < 0:
        raise BoundaryValidationError(
            "stored token total is not a non-negative integer", ("tokens",)
        )
    return total


def _add_in_transaction(transaction: Any, ref: Any, count: int) -> int:
    new_total = _stored_total(ref.get(transaction=transaction)) + count
    transaction.set(ref, {TOTAL_FIELD: new_total})
    return new_total


class FirestoreCounterStore:
    """Atomic daily token counter; one document per UTC day."""

    def __init__(
        self,
        project: str | None = None,
        collection: str = DEFAULT_COUNTER_COLLECTION,
        client: Any | None = None,
    ) -> None:
        self._collection = collection
        self._lazy = _LazyClient(project, client)

    def add_tokens(self, day: date, count: int) -> int:
        require_non_negative(count)
        client = self._lazy.get()
        ref = client.collection(self._collection).document(day.isoformat())
        run = _load_sdk().transactional(_add_in_transaction)
        total = run(client.transaction(), ref, count)
        if not isinstance(total, int):
            raise BoundaryValidationError("counter returned a non-integer total", ("tokens",))
        return total


class FirestoreReplayStore:
    """Last-good-response store keyed by replay key."""

    def __init__(
        self,
        project: str | None = None,
        collection: str = DEFAULT_REPLAY_COLLECTION,
        client: Any | None = None,
    ) -> None:
        self._collection = collection
        self._lazy = _LazyClient(project, client)

    def _ref(self, key: str) -> Any:
        return self._lazy.get().collection(self._collection).document(key)

    def get(self, key: str) -> StoredReplay | None:
        snapshot = self._ref(key).get()
        if not snapshot.exists:
            return None
        data = snapshot.to_dict() or {}
        content, stored_at = data.get("content"), data.get("stored_at")
        if (
            not isinstance(content, str)
            or not isinstance(stored_at, datetime)
            or not _is_aware(stored_at)
        ):
            _LOG.warning("replay document is malformed and was ignored: %s", redact_text(key))
            return None
        return StoredReplay(content=content, stored_at=stored_at)

    def put(self, key: str, content: str, stored_at: datetime) -> None:
        require_aware(stored_at)
        self._ref(key).set({"content": content, "stored_at": stored_at})


def _is_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None
