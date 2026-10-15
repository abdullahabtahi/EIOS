"""Write-behind assistant sessions: the turn reads and writes its conversation in memory, the durable store catches up.

ADK's Firestore session service writes every event of a turn as its own transaction (begin, read the session, write,
commit) and the turn waits for each one. A turn has six to eight events, so the operator waited for that many
transactions: 5 to 14 s from a laptop in the Philippines against us-central1 [MEASURED, docs/assistant-latency.md].

Here the turn talks to an in-memory copy of its session, and each session's writes go to the durable store in the same
order on a background task, after the answer has been returned. The durable store is read once per session per process.

What this gives up, on purpose: an event is durable a moment after the operator sees the answer, not before. If the
process dies in that moment, the last turn is missing from the copilot's conversation memory (never from the decision
ledger, which does not use this). `drain` is called at shutdown to write what is pending first. A write that keeps
failing is logged with the session id and dropped, never retried forever and never raised into a turn. With several
instances, each holds its own copy of a session it has served; the durable store gets every event, in the order each
instance wrote them.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections import OrderedDict, deque
from dataclasses import dataclass, field
from typing import Any

from google.adk.errors._stale_session_error import StaleSessionError
from google.adk.errors.already_exists_error import AlreadyExistsError
from google.adk.events.event import Event
from google.adk.sessions.base_session_service import (
    BaseSessionService,
    GetSessionConfig,
    ListSessionsResponse,
)
from google.adk.sessions.session import Session
from google.adk.sessions.state import State

_LOG = logging.getLogger(__name__)
DEFAULT_MAX_SESSIONS = (
    512  # [ASSUMPTION] conversations one instance keeps in memory; older written ones are dropped
)
DEFAULT_ATTEMPTS = 3
DEFAULT_RETRY_DELAY_S = 0.5

_Key = tuple[str, str, str]  # app, user, session id


@dataclass
class _Op:
    kind: str  # "create" or "append"
    state: dict[str, Any] | None = None
    event: Event | None = None


@dataclass
class _Thread:
    pending: deque[_Op] = field(default_factory=deque)
    durable: Session | None = None  # the store's own copy, which carries its revision marker
    task: asyncio.Task[None] | None = None


class WriteBehindSessionService(BaseSessionService):
    def __init__(
        self,
        durable: BaseSessionService,
        *,
        max_sessions: int = DEFAULT_MAX_SESSIONS,
        attempts: int = DEFAULT_ATTEMPTS,
        retry_delay_s: float = DEFAULT_RETRY_DELAY_S,
    ) -> None:
        self.durable = durable
        self._max_sessions, self._attempts, self._retry_delay_s = (
            max_sessions,
            attempts,
            retry_delay_s,
        )
        self._hot: OrderedDict[_Key, Session] = OrderedDict()
        self._threads: dict[_Key, _Thread] = {}

    # --- reads and writes a turn makes -------------------------------------------------------------------------

    async def get_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        config: GetSessionConfig | None = None,
    ) -> Session | None:
        key = (app_name, user_id, session_id)
        hot = self._hot.get(key)
        if hot is not None:
            self._hot.move_to_end(key)
            # A read starts a turn. temp: state belonged to the last turn and a durable store never keeps it; left here
            # it would tell this turn it was already screened or prefetched.
            for name in [k for k in hot.state if k.startswith(State.TEMP_PREFIX)]:
                del hot.state[name]
            return hot
        stored = await self.durable.get_session(
            app_name=app_name, user_id=user_id, session_id=session_id, config=config
        )
        if stored is None:
            return None
        self._thread(key).durable = stored
        return self._remember(key, stored.model_copy(deep=True))

    async def create_session(
        self,
        *,
        app_name: str,
        user_id: str,
        state: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> Session:
        key = (app_name, user_id, (session_id or "").strip() or str(uuid.uuid4()))
        session = Session(
            id=key[2],
            app_name=app_name,
            user_id=user_id,
            state=dict(state or {}),
            last_update_time=time.time(),
        )
        self._enqueue(key, _Op("create", state=dict(state or {})))
        return self._remember(key, session)

    async def append_event(self, session: Session, event: Event) -> Event:
        event = await super().append_event(
            session, event
        )  # applies temp state, trims it, commits to memory
        if event.partial:
            return event
        session.last_update_time = event.timestamp
        key = (session.app_name, session.user_id, session.id)
        self._hot.setdefault(key, session)
        self._hot.move_to_end(key)
        self._enqueue(key, _Op("append", event=event.model_copy(deep=True)))
        self._evict()
        return event

    async def list_sessions(
        self, *, app_name: str, user_id: str | None = None
    ) -> ListSessionsResponse:
        await self.drain()
        return await self.durable.list_sessions(app_name=app_name, user_id=user_id)

    async def delete_session(self, *, app_name: str, user_id: str, session_id: str) -> None:
        key = (app_name, user_id, session_id)
        await self._drain_keys([key], None)
        self._hot.pop(key, None)
        self._threads.pop(key, None)
        await self.durable.delete_session(app_name=app_name, user_id=user_id, session_id=session_id)

    # --- the background writer ----------------------------------------------------------------------------------

    async def flush(self) -> None:
        await self.drain()

    async def drain(self, timeout_s: float | None = None) -> int:
        """Write what is pending, waiting at most `timeout_s`; the number of writes still pending is returned."""
        return await self._drain_keys([k for k, t in self._threads.items() if t.pending], timeout_s)

    async def _drain_keys(self, keys: list[_Key], timeout_s: float | None) -> int:
        tasks = [
            self._start(key)
            for key in keys
            if self._threads.get(key) and self._threads[key].pending
        ]
        if tasks:
            await asyncio.wait(tasks, timeout=timeout_s)
        return sum(len(t.pending) for t in self._threads.values())

    def _thread(self, key: _Key) -> _Thread:
        return self._threads.setdefault(key, _Thread())

    def _enqueue(self, key: _Key, op: _Op) -> None:
        self._thread(key).pending.append(op)
        self._start(key)

    def _start(self, key: _Key) -> asyncio.Task[None]:
        """One writer per session, on the running loop; a writer left on a closed loop is replaced."""
        thread = self._thread(key)
        loop = asyncio.get_running_loop()
        if thread.task is None or thread.task.done() or thread.task.get_loop() is not loop:
            thread.task = loop.create_task(self._write(key, thread))
        return thread.task

    async def _write(self, key: _Key, thread: _Thread) -> None:
        while thread.pending:
            await self._apply_with_retries(key, thread, thread.pending[0])
            thread.pending.popleft()  # only after the attempt: a writer cut off mid-write leaves the op for the next

    async def _apply_with_retries(self, key: _Key, thread: _Thread, op: _Op) -> None:
        error: Exception | None = None
        for attempt in range(self._attempts):
            try:
                await self._apply(key, thread, op)
                return
            except (
                StaleSessionError
            ) as exc:  # another writer moved the stored session on: read it again, retry
                error = exc
                thread.durable = await self._load(key)
            except Exception as exc:
                error = exc
                await asyncio.sleep(self._retry_delay_s * 2**attempt)
        _LOG.error(
            "session %s: an %s was not persisted after %d attempts (%s)",
            key[2],
            op.kind,
            self._attempts,
            type(error).__name__,
        )

    async def _apply(self, key: _Key, thread: _Thread, op: _Op) -> None:
        app_name, user_id, session_id = key
        if op.kind == "create":
            try:
                thread.durable = await self.durable.create_session(
                    app_name=app_name, user_id=user_id, state=op.state, session_id=session_id
                )
            except AlreadyExistsError:
                thread.durable = await self._load(key)
            return
        if thread.durable is None:
            thread.durable = await self._load(key) or await self.durable.create_session(
                app_name=app_name, user_id=user_id, session_id=session_id
            )
        if op.event is None:
            raise ValueError("an append without an event")
        await self.durable.append_event(thread.durable, op.event.model_copy(deep=True))

    async def _load(self, key: _Key) -> Session | None:
        return await self.durable.get_session(app_name=key[0], user_id=key[1], session_id=key[2])

    # --- the in-memory copies -----------------------------------------------------------------------------------

    def _remember(self, key: _Key, session: Session) -> Session:
        self._hot[key] = session
        self._hot.move_to_end(key)
        self._evict()
        return session

    def _evict(self) -> None:
        """Drop the least recently used sessions over the limit, but only those with nothing left to write."""
        for key in list(self._hot):
            if len(self._hot) <= self._max_sessions:
                return
            thread = self._threads.get(key)
            if thread is None or not thread.pending:
                self._hot.pop(key)
                self._threads.pop(key, None)
