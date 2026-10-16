"""Prepared briefs in the cockpit: read the brief for an alert, and refresh the top ones (docs/ambient-dossiers.md).

`GET /api/cockpit/ambient/briefs/{entity_id}` returns the brief kept for an alert, or 404 when none was prepared (the
dossier then says so). `POST /api/cockpit/ambient/refresh` starts a refresh of the top alerts in the background and
answers 202 at once; Cloud Scheduler can call it, and the API starts one at boot when `EIOS_AMBIENT_TOP_N` is above zero.
"""

from __future__ import annotations

import asyncio
import functools
import logging
import os
import threading
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from eios.ambient.brief import (
    DEFAULT_TTL_S,
    MIN_SCORE,
    BriefStore,
    Preparation,
    evidence_only,
    prepare_top,
)
from eios.assistant.config import AssistantSettings
from eios.assistant.runtime import AssistantRuntime
from eios.assistant.safety import build_safety_plugins
from eios.assistant.sessions import build_session_service, valid_entity_id
from eios.cockpit.assistant_gateway import figure_views, source_views
from eios.cockpit.auth import APPROVE_ROLES, current_operator, require_roles
from eios.dataplane.plane import read_models
from eios.ontology.actions.record_store import default_record_store
from eios.ontology.omcp.port.catalogue import build_port

_LOG = logging.getLogger("eios.cockpit.ambient")
BRIEF_PATH = "/api/cockpit/ambient/briefs/{entity_id}"
REFRESH_PATH = "/api/cockpit/ambient/refresh"
TOP_N_ENV = "EIOS_AMBIENT_TOP_N"
TTL_ENV = "EIOS_AMBIENT_TTL_S"
MAX_TOP_N = 25

router = APIRouter(tags=["Cockpit Ambient Briefs"])
_lock = threading.Lock()
_running: asyncio.Task[Preparation] | None = None
_last: Preparation | None = None


def top_n() -> int:
    """How many top alerts to prepare; 0 (the default) means none, so tests and dev start quietly."""
    try:
        return max(0, min(MAX_TOP_N, int(os.environ.get(TOP_N_ENV, "0"))))
    except ValueError:
        return 0


def ttl_s() -> float:
    try:
        return float(os.environ.get(TTL_ENV, DEFAULT_TTL_S))
    except ValueError:
        return DEFAULT_TTL_S


@functools.cache
def brief_store() -> BriefStore:
    return BriefStore(default_record_store("ambient_briefs"))


@functools.cache
def _runtime() -> AssistantRuntime:
    """The assistant over evidence tools only, the same settings, screening and models as an operator's turn."""
    settings = AssistantSettings.from_env()
    return AssistantRuntime(
        port=evidence_only(build_port(read_models())),
        settings=settings,
        session_service=build_session_service(settings),
        plugins=build_safety_plugins(settings),
    )


def reset_for_testing() -> None:
    global _running, _last
    brief_store.cache_clear()
    if hasattr(_runtime, "cache_clear"):  # a test may have replaced it
        _runtime.cache_clear()
    _running, _last = None, None


def top_entities(n: int) -> list[str]:
    queue = read_models().aml.get_triage_queue(min_score=MIN_SCORE, limit=n)
    return [str(row["entity_id"]) for row in queue]


async def _refresh(n: int) -> Preparation:
    global _last
    entities = await asyncio.to_thread(top_entities, n)
    result = await prepare_top(_runtime(), brief_store(), entities, ttl_s=ttl_s())
    _last = result
    _LOG.info(
        "ambient briefs: %d prepared, %d not kept, %.1f s",
        len(result.prepared),
        len(result.skipped),
        result.seconds,
    )
    return result


def start_refresh(n: int | None = None) -> asyncio.Task[Preparation] | None:
    """Begin a refresh unless one is running or none is wanted. Returns the task, else None."""
    global _running
    count = top_n() if n is None else n
    with _lock:
        if count <= 0 or (_running is not None and not _running.done()):
            return None
        _running = asyncio.create_task(_refresh(count))
        return _running


@router.get(BRIEF_PATH, dependencies=[Depends(current_operator)])
def get_brief(entity_id: str) -> dict[str, Any]:
    if not valid_entity_id(entity_id):
        raise HTTPException(status_code=422, detail="entity id is not a valid identifier")
    view = brief_store().get(entity_id)
    if view is None:
        raise HTTPException(status_code=404, detail="no brief has been prepared for this alert")
    brief = view.brief
    return {
        "entity_id": brief.entity_id,
        "prepared_at": brief.prepared_at.isoformat(),
        "expires_at": brief.expires_at.isoformat(),
        "stale": view.stale,
        "response": brief.answer.text,
        "provenance_citations": figure_views(brief.answer),
        "sources": source_views(brief.answer),
        "steps": list(brief.steps),
        "data_origin": brief.answer.data_origin.value,
    }


@router.post(REFRESH_PATH, dependencies=[Depends(require_roles(APPROVE_ROLES))])
async def refresh(n: int | None = None) -> JSONResponse:
    wanted = max(1, min(MAX_TOP_N, n if n is not None else (top_n() or 5)))
    started = start_refresh(wanted) is not None
    return JSONResponse({"started": started, "top_n": wanted}, status_code=202)
