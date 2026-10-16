"""The prepared brief: the assistant's own "brief me" turn for a top alert, run ahead of time and kept.

The turn is the one an operator would run, so the assembler's guarantee holds for the kept text: every figure came from
a tool result of that turn, and the answer carries its sources. It runs as a system identity over a port restricted to
evidence tools, so nothing here can propose, draft or write. A turn that did not assemble (timeout, outage, screened,
failed closed) is never kept: no brief is better than a wrong one.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from eios.assistant.answer import Answer
from eios.assistant.runtime import AssistantRuntime, TurnOutcome
from eios.common.validation import StrictModel
from eios.ontology.actions.record_store import ModelStore, RecordStore
from eios.ontology.omcp.port.principal import Principal, Workstation
from eios.ontology.omcp.port.service import GovernedToolPort

logger = logging.getLogger(__name__)

SYSTEM_UID = "system:ambient"  # a service identity; never an operator's uid, so threads and limits stay apart
QUESTION = "Brief me on this case."
EVIDENCE_KINDS = frozenset({"evidence", "compute", "knowledge"})  # no draft, no propose
DEFAULT_TTL_S = (
    3600.0  # [ASSUMPTION] an hour: alerts re-rank as the engines refresh, and a stale brief says so
)
MIN_SCORE = 50


def system_principal() -> Principal:
    return Principal(uid=SYSTEM_UID, workstation=Workstation.AML_INVESTIGATOR)


def evidence_only(port: GovernedToolPort) -> GovernedToolPort:
    return port.restricted_to(EVIDENCE_KINDS)


class PreparedBrief(StrictModel):
    entity_id: str
    question: str
    prepared_at: datetime
    expires_at: datetime
    answer: Answer
    steps: tuple[str, ...]
    latency_ms: float
    model_key: str | None


class BriefView(StrictModel):
    """What the route returns: the brief and whether it is past its time to live."""

    brief: PreparedBrief
    stale: bool


def keepable(outcome: TurnOutcome) -> bool:
    a = outcome.answer
    return bool(
        outcome.status == "ok"
        and a.text.strip()
        and not (a.blocked or a.failed_closed or a.is_replay_fallback or a.fallback_reason)
    )


class BriefStore:
    def __init__(
        self, records: RecordStore, clock: Callable[[], datetime] = lambda: datetime.now(UTC)
    ) -> None:
        self._briefs = ModelStore(records, PreparedBrief)
        self._clock = clock

    def put(self, brief: PreparedBrief) -> None:
        self._briefs.put(brief.entity_id, brief)

    def get(self, entity_id: str) -> BriefView | None:
        found = self._briefs.get(entity_id)
        if found is None:
            return None
        return BriefView(brief=found, stale=found.expires_at <= self._clock())


@dataclass(frozen=True)
class Preparation:
    prepared: tuple[str, ...]
    skipped: tuple[str, ...]  # entities whose turn did not assemble, so nothing was kept
    seconds: float


async def prepare_brief(
    runtime: AssistantRuntime,
    store: BriefStore,
    entity_id: str,
    *,
    ttl_s: float = DEFAULT_TTL_S,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> PreparedBrief | None:
    outcome = await runtime.run_turn(
        principal=system_principal(), question=QUESTION, entity_id=entity_id
    )
    if not keepable(outcome):
        logger.warning("ambient brief for %s not kept: %s", entity_id, outcome.status)
        return None
    prepared_at = now()
    brief = PreparedBrief(
        entity_id=entity_id,
        question=QUESTION,
        prepared_at=prepared_at,
        expires_at=prepared_at + timedelta(seconds=ttl_s),
        answer=outcome.answer,
        steps=outcome.steps,
        latency_ms=outcome.latency_ms,
        model_key=outcome.model_key,
    )
    store.put(brief)
    return brief


async def prepare_top(
    runtime: AssistantRuntime,
    store: BriefStore,
    entity_ids: list[str],
    *,
    ttl_s: float = DEFAULT_TTL_S,
) -> Preparation:
    """One at a time, so the model endpoint is not flooded and a failure costs one entity, not the batch."""
    started = time.perf_counter()
    prepared: list[str] = []
    skipped: list[str] = []
    for entity_id in entity_ids:
        try:
            kept = await prepare_brief(runtime, store, entity_id, ttl_s=ttl_s)
        except Exception:
            logger.exception("ambient brief for %s failed", entity_id)
            kept = None
        (prepared if kept else skipped).append(entity_id)
    return Preparation(tuple(prepared), tuple(skipped), time.perf_counter() - started)
