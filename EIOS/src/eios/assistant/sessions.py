"""Per-operator, per-entity conversations on ADK's own session services (spec 021 FR-007).

ADK's Firestore service stores `users/<user id>/sessions/<session id>`, so a thread belongs to the verified uid and
another operator's lookup finds nothing. In-memory sessions are refused outside dev and test, like every other store.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from google.adk.sessions.base_session_service import BaseSessionService
from google.adk.sessions.in_memory_session_service import InMemorySessionService

from eios.assistant.config import AssistantConfigError, AssistantSettings

APP_NAME = "eios-assistant"
NO_ENTITY = "-"


def session_key(workstation: str, entity_id: str | None) -> str:
    """One thread per workstation and entity; the operator is the ADK user id, never part of this key."""
    entity = (entity_id or "").strip() or NO_ENTITY
    return f"{workstation}:{entity}"


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

        return FirestoreSessionService(client=client_factory(settings.firestore_database))
    if not settings.local:
        raise AssistantConfigError(
            f"EIOS_PERSISTENCE=firestore must be set in the '{settings.environment}' environment; "
            "refusing to keep assistant conversations in process memory"
        )
    return InMemorySessionService()
