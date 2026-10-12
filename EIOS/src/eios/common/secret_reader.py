"""Secret reading at call time through a pluggable source (FR-017).

Public API:
- ``SecretSource``: protocol, ``fetch(name) -> str | None`` (``None`` means the secret is absent).
- ``InMemorySecretSource``: dev and test double; ``rotate(name, value)`` simulates a rotation.
- ``SecretManagerSource(project_id)``: Secret Manager, reads the ``latest`` version; the client
  library is imported lazily, on first fetch only.
- ``SecretReader(source, refresh_seconds=..., clock=...)``: ``get(name) -> SecretValue``.
- ``SecretValue``: ``reveal()`` returns the text; ``repr``, ``str`` and ``format`` are redacted.
- ``SecretNotFoundError`` / ``SecretSourceError``: typed errors that name only the secret.
- ``DEFAULT_REFRESH_SECONDS``: default cache lifetime.

Rotation needs no code change: a value is cached for at most ``refresh_seconds``; the first read
at or after that age goes back to the source and so sees the rotated value. ``0`` disables caching.
Absent and empty secrets both raise ``SecretNotFoundError`` and are never cached. When the source
fails the reader raises rather than serving a stale value (fail closed). The cache is private
state of the reader, guarded by a lock.
"""

from __future__ import annotations

import importlib
import logging
import re
import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Protocol

from eios.common.errors import BoundaryValidationError, EiosError

# [ASSUMPTION] cache lifetime; a trade-off between rotation latency and Secret Manager calls.
DEFAULT_REFRESH_SECONDS = 300.0

_LOG = logging.getLogger(__name__)
_SECRET_NAME = re.compile(r"[A-Za-z0-9_-]{1,255}")
# Project id (lowercase letters, digits, hyphens) or a project number.
_PROJECT_ID = re.compile(r"[a-z][a-z0-9-]{4,28}[a-z0-9]|[0-9]{1,20}")
_MASKED = "SecretValue(<redacted>)"


class SecretNotFoundError(EiosError):
    """The named secret is absent or empty; the message carries only the secret name."""

    def __init__(self, secret_name: str) -> None:
        super().__init__(f"secret '{secret_name}' was not found or is empty")
        self.secret_name = secret_name


class SecretSourceError(EiosError):
    """The secret backend failed; the message carries only the secret name and a fixed reason."""

    def __init__(self, secret_name: str, reason: str = "the secret source failed") -> None:
        super().__init__(f"secret '{secret_name}': {reason}")
        self.secret_name = secret_name


class SecretSource(Protocol):
    """Where secret values live."""

    def fetch(self, name: str) -> str | None: ...


@dataclass(frozen=True, slots=True)
class SecretValue:
    """A secret that refuses to print itself."""

    _value: str = field(repr=False)

    def reveal(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return _MASKED

    def __str__(self) -> str:
        return _MASKED


class InMemorySecretSource:
    """Dev and test source. Mutable on purpose: ``rotate`` stands in for a store-side rotation."""

    def __init__(self, values: Mapping[str, str]) -> None:
        self._values = dict(values)

    def fetch(self, name: str) -> str | None:
        return self._values.get(name)

    def rotate(self, name: str, value: str) -> None:
        self._values[name] = value

    def __repr__(self) -> str:
        return f"InMemorySecretSource(names={sorted(self._values)})"


class _Payload(Protocol):
    @property
    def data(self) -> bytes: ...


class _AccessResponse(Protocol):
    @property
    def payload(self) -> _Payload: ...


class _SecretManagerClient(Protocol):
    def access_secret_version(self, request: dict[str, str]) -> _AccessResponse: ...


def _is_not_found(exc: Exception) -> bool:
    try:
        exceptions = importlib.import_module("google.api_core.exceptions")
    except ImportError:
        return False
    return isinstance(exc, exceptions.NotFound)


class SecretManagerSource:
    """Secret Manager source; reads the ``latest`` version with the caller's own identity."""

    def __init__(self, project_id: str, *, client: _SecretManagerClient | None = None) -> None:
        if not isinstance(project_id, str) or _PROJECT_ID.fullmatch(project_id) is None:
            raise BoundaryValidationError("invalid project id", ("project_id",))
        self._project_id = project_id
        self._client = client

    def _resolve_client(self, name: str) -> _SecretManagerClient:
        if self._client is not None:
            return self._client
        try:
            module = importlib.import_module("google.cloud.secretmanager")
            client: _SecretManagerClient = module.SecretManagerServiceClient()
        except ImportError:
            raise SecretSourceError(
                name, "the Secret Manager client library is not installed"
            ) from None
        except Exception:
            raise SecretSourceError(
                name, "the Secret Manager client could not be created"
            ) from None
        self._client = client
        return client

    def fetch(self, name: str) -> str | None:
        client = self._resolve_client(name)
        path = f"projects/{self._project_id}/secrets/{name}/versions/latest"
        try:
            response = client.access_secret_version(request={"name": path})
            return response.payload.data.decode("utf-8")
        except Exception as exc:
            if _is_not_found(exc):
                return None
            raise SecretSourceError(name) from None

    def __repr__(self) -> str:
        return f"SecretManagerSource(project_id={self._project_id!r})"


def _utc_now() -> datetime:
    return datetime.now(UTC)


class SecretReader:
    """Reads secrets through a source with a bounded cache; see the module docstring."""

    def __init__(
        self,
        source: SecretSource,
        *,
        refresh_seconds: float = DEFAULT_REFRESH_SECONDS,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        if (
            isinstance(refresh_seconds, bool)
            or not isinstance(refresh_seconds, int | float)
            or not refresh_seconds >= 0
        ):
            raise BoundaryValidationError(
                "refresh_seconds must be a number >= 0", ("refresh_seconds",)
            )
        self._source = source
        self._refresh = timedelta(seconds=refresh_seconds)
        self._clock = clock
        self._cache: dict[str, tuple[SecretValue, datetime]] = {}
        self._lock = threading.Lock()

    def get(self, name: str) -> SecretValue:
        """Return the secret, from the source when the cached copy is at least the interval old."""
        if not isinstance(name, str) or _SECRET_NAME.fullmatch(name) is None:
            raise BoundaryValidationError("invalid secret name", ("name",))
        now = self._clock()
        with self._lock:
            cached = self._cache.get(name)
        if cached is not None and now - cached[1] < self._refresh:
            return cached[0]
        value = self._load(name)
        with self._lock:
            self._cache[name] = (value, now)
        _LOG.debug("secret '%s' refreshed from source", name)
        return value

    def _load(self, name: str) -> SecretValue:
        try:
            raw = self._source.fetch(name)
        except SecretSourceError:
            raise
        except Exception:
            raise SecretSourceError(name) from None
        if not raw:
            raise SecretNotFoundError(name)
        return SecretValue(raw)

    def __repr__(self) -> str:
        return (
            f"SecretReader(source={type(self._source).__name__}, "
            f"refresh_seconds={self._refresh.total_seconds()})"
        )
