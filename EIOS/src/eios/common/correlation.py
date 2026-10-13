"""Correlation identifiers (FR-036): generated at the edge, validated, carried by header and context.

Public API:
- ``CORRELATION_HEADER``: the one header name used between services.
- ``MAX_ID_LENGTH``: length bound for an accepted identifier ``[ASSUMPTION]``.
- ``new_correlation_id()``: opaque random identifier (no host, user or clock data).
- ``is_valid_correlation_id(value)`` / ``resolve_inbound_id(value)``: an inbound value is kept
  only if it is 1..MAX_ID_LENGTH characters of ASCII letters, digits and hyphen; anything else
  (absent, empty, over-long, control characters, other alphabets) is replaced by a fresh id and
  never reflected into logs, spans or headers.
- ``correlation_scope(id)``: context manager binding the id to the current task (``ContextVar``,
  so concurrent tasks stay isolated); ``current_id()`` reads it.
- ``outbound_headers(headers)``: copy of ``headers`` plus the header for the current id.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar

from eios.common.errors import EiosError

CORRELATION_HEADER = "X-Correlation-ID"
MAX_ID_LENGTH = 64  # [ASSUMPTION] generous for UUIDs and common trace-id shapes

_VALID_ID = re.compile(rf"[A-Za-z0-9-]{{1,{MAX_ID_LENGTH}}}")
_CURRENT: ContextVar[str | None] = ContextVar("eios_correlation_id", default=None)


class MissingCorrelationError(EiosError):
    """An outbound call was attempted with no correlation id bound to the current task."""

    def __init__(self) -> None:
        super().__init__("no correlation id is bound to the current task")


def new_correlation_id() -> str:
    """Return a fresh random identifier (UUID version 4: no MAC address, user or time inside)."""
    return str(uuid.uuid4())


def is_valid_correlation_id(value: object) -> bool:
    """True only for a string that fully matches the accepted pattern."""
    return isinstance(value, str) and _VALID_ID.fullmatch(value) is not None


def resolve_inbound_id(value: str | None) -> str:
    """Keep a valid inbound identifier, otherwise return a new one (the input is dropped)."""
    if value is not None and is_valid_correlation_id(value):
        return value
    return new_correlation_id()


def current_id() -> str | None:
    """The id bound to the current task, or ``None`` outside any scope."""
    return _CURRENT.get()


@contextmanager
def correlation_scope(correlation_id: str) -> Iterator[None]:
    """Bind ``correlation_id`` for the duration of the block; always restores the previous one."""
    if not is_valid_correlation_id(correlation_id):
        raise ValueError("correlation id does not match the accepted pattern")
    token = _CURRENT.set(correlation_id)
    try:
        yield
    finally:
        _CURRENT.reset(token)


def outbound_headers(headers: Mapping[str, str] | None = None) -> dict[str, str]:
    """Return a new header mapping with the current correlation id added."""
    bound = current_id()
    if bound is None:
        raise MissingCorrelationError
    return {**(headers or {}), CORRELATION_HEADER: bound}
