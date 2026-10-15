"""Per-operator, per-entity conversations on ADK's own session services (spec 021 FR-007).

ADK's Firestore service stores `users/<user id>/sessions/<session id>`, so a thread belongs to the verified uid and
another operator's lookup finds nothing. In-memory sessions are refused outside dev and test, like every other store.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from google.adk.sessions.base_session_service import BaseSessionService
from google.adk.sessions.in_memory_session_service import InMemorySessionService

from eios.assistant.config import AssistantConfigError, AssistantSettings
from eios.assistant.session_cache import WriteBehindSessionService

APP_NAME = "eios-assistant"
NO_ENTITY = "-"


_ENTITY_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{1,31}")


def valid_entity_id(entity_id: str | None) -> bool:
    """An id the platform issues: bounded, no separators, no whitespace. Nothing else reaches a prompt or a session id."""
    return not entity_id or _ENTITY_ID.fullmatch(entity_id) is not None


def session_key(workstation: str, entity_id: str | None) -> str:
    """One thread per workstation and entity; the operator is the ADK user id, never part of this key."""
    if not valid_entity_id(entity_id):
        raise ValueError("entity id is not a valid identifier")
    return f"{workstation}:{entity_id or NO_ENTITY}"


def _firestore_client(database: str) -> Any:
    from google.cloud import firestore

    return firestore.AsyncClient(database=database)


def build_session_service(
    settings: AssistantSettings,
    client_factory: Callable[[str], Any] = _firestore_client,
) -> BaseSessionService:
    if settings.persistence == "firestore":
        if not settings.firestore_database:
            raise AssistantConfigError(
                "EIOS_FIRESTORE_DATABASE must name the shared database for assistant sessions"
            )
        from google.adk.integrations.firestore.firestore_session_service import (
            FirestoreSessionService,
        )

        durable = FirestoreSessionService(client=client_factory(settings.firestore_database))
        return WriteBehindSessionService(durable) if settings.session_write_behind else durable
    if not settings.local:
        raise AssistantConfigError(
            f"EIOS_PERSISTENCE=firestore must be set in the '{settings.environment}' environment; "
            "refusing to keep assistant conversations in process memory"
        )
    return InMemorySessionService()
