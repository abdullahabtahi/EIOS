"""Write-behind sessions: a turn reads and writes the conversation in memory; the durable store catches up after.

The durable store is a fake with a deliberate delay, so "the turn did not wait for it" is checked by time, and "nothing
was lost" by comparing what the durable store holds once the writes are flushed.
"""

import asyncio
import logging
import time

import pytest
from google.adk.errors._stale_session_error import StaleSessionError
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.adk.sessions.in_memory_session_service import InMemorySessionService

from eios.assistant.session_cache import WriteBehindSessionService
from eios.llm_gateway.providers.adk_types import user_message

APP, USER, SID = "app", "alice", "aml_investigator:CR84920"
DELAY_S = 0.05


class SlowStore(InMemorySessionService):
    """A durable store that takes DELAY_S per call and can be told to fail."""

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[str] = []
        self.fail_appends = 0
        self.stale_appends = 0

    async def create_session(self, **kwargs):  # type: ignore[no-untyped-def]
        self.calls.append("create")
        await asyncio.sleep(DELAY_S)
        return await super().create_session(**kwargs)

    async def get_session(self, **kwargs):  # type: ignore[no-untyped-def]
        self.calls.append("get")
        await asyncio.sleep(DELAY_S)
        return await super().get_session(**kwargs)

    async def append_event(self, session, event):  # type: ignore[no-untyped-def]
        self.calls.append("append")
        await asyncio.sleep(DELAY_S)
        if self.stale_appends:
            self.stale_appends -= 1
            raise StaleSessionError("stale")
        if self.fail_appends:
            self.fail_appends -= 1
            raise RuntimeError("store unavailable")
        return await super().append_event(session, event)


def _event(text: str, delta: dict | None = None) -> Event:
    return Event(
        author="user",
        content=user_message(text),
        actions=EventActions(state_delta=delta or {}),
    )


async def _durable_texts(store: SlowStore) -> list[str]:
    stored = await InMemorySessionService.get_session(
        store, app_name=APP, user_id=USER, session_id=SID
    )
    assert stored is not None
    return [e.content.parts[0].text for e in stored.events]


def test_a_turn_does_not_wait_for_the_durable_store_and_nothing_is_lost() -> None:
    async def go() -> None:
        store = SlowStore()
        svc = WriteBehindSessionService(store, retry_delay_s=0.0)
        assert await svc.get_session(app_name=APP, user_id=USER, session_id=SID) is None
        started = time.perf_counter()
        session = await svc.create_session(app_name=APP, user_id=USER, session_id=SID)
        for i in range(5):
            await svc.append_event(session, _event(f"m{i}", {"k": i, "temp:t": i}))
        assert time.perf_counter() - started < DELAY_S  # five writes and a create, none waited on
        assert session.state["temp:t"] == 4  # temp state lives for the turn, in memory
        await svc.flush()
        assert await _durable_texts(store) == [f"m{i}" for i in range(5)]
        stored = await InMemorySessionService.get_session(
            store, app_name=APP, user_id=USER, session_id=SID
        )
        assert (
            stored.state["k"] == 4 and "temp:t" not in stored.state
        )  # temp state is never persisted

    asyncio.run(go())


def test_the_durable_store_is_read_once_per_session_then_memory_answers() -> None:
    async def go() -> None:
        store = SlowStore()
        await InMemorySessionService.create_session(
            store, app_name=APP, user_id=USER, session_id=SID
        )
        svc = WriteBehindSessionService(store, retry_delay_s=0.0)
        first = await svc.get_session(app_name=APP, user_id=USER, session_id=SID)
        second = await svc.get_session(app_name=APP, user_id=USER, session_id=SID)
        assert first is second and store.calls.count("get") == 1

    asyncio.run(go())


def test_a_new_service_instance_reads_the_thread_back_from_the_durable_store() -> None:
    async def go() -> None:
        store = SlowStore()
        svc = WriteBehindSessionService(store, retry_delay_s=0.0)
        session = await svc.create_session(app_name=APP, user_id=USER, session_id=SID)
        await svc.append_event(session, _event("before restart"))
        await svc.flush()
        restarted = WriteBehindSessionService(store, retry_delay_s=0.0)
        again = await restarted.get_session(app_name=APP, user_id=USER, session_id=SID)
        assert [e.content.parts[0].text for e in again.events] == ["before restart"]
        await restarted.append_event(again, _event("after restart"))
        await restarted.flush()
        assert await _durable_texts(store) == ["before restart", "after restart"]

    asyncio.run(go())


def test_a_failed_write_is_retried_and_a_stale_session_is_reloaded() -> None:
    async def go() -> None:
        store = SlowStore()
        svc = WriteBehindSessionService(store, retry_delay_s=0.0)
        session = await svc.create_session(app_name=APP, user_id=USER, session_id=SID)
        store.fail_appends, store.stale_appends = 1, 1
        await svc.append_event(session, _event("kept"))
        await svc.flush()
        assert await _durable_texts(store) == ["kept"]

    asyncio.run(go())


def test_a_write_that_keeps_failing_is_reported_and_never_breaks_the_turn(
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def go() -> None:
        store = SlowStore()
        svc = WriteBehindSessionService(store, retry_delay_s=0.0, attempts=2)
        session = await svc.create_session(app_name=APP, user_id=USER, session_id=SID)
        await svc.flush()
        store.fail_appends = 2
        await svc.append_event(session, _event("lost"))
        await svc.append_event(session, _event("next"))
        await svc.flush()
        assert await _durable_texts(store) == ["next"]
        assert [e.content.parts[0].text for e in session.events] == [
            "lost",
            "next",
        ]  # the thread in memory is whole

    with caplog.at_level(logging.ERROR):
        asyncio.run(go())
    assert (
        "not persisted" in caplog.text and "lost" not in caplog.text
    )  # the content is never logged


def test_sessions_with_unwritten_events_are_never_evicted() -> None:
    async def go() -> None:
        store = SlowStore()
        svc = WriteBehindSessionService(store, retry_delay_s=0.0, max_sessions=1)
        a = await svc.create_session(app_name=APP, user_id=USER, session_id="s:a")
        await svc.append_event(a, _event("a1"))
        b = await svc.create_session(app_name=APP, user_id=USER, session_id="s:b")
        assert (
            await svc.get_session(app_name=APP, user_id=USER, session_id="s:a") is a
        )  # pending: kept
        await svc.flush()
        await svc.append_event(b, _event("b1"))  # touching b evicts a, now that a is written
        await svc.flush()
        reread = await svc.get_session(app_name=APP, user_id=USER, session_id="s:a")
        assert reread is not a and [e.content.parts[0].text for e in reread.events] == ["a1"]

    asyncio.run(go())


def test_drain_with_a_timeout_reports_what_is_still_unwritten() -> None:
    async def go() -> None:
        store = SlowStore()
        svc = WriteBehindSessionService(store, retry_delay_s=0.0)
        session = await svc.create_session(app_name=APP, user_id=USER, session_id=SID)
        for i in range(10):
            await svc.append_event(session, _event(f"m{i}"))
        left = await svc.drain(timeout_s=DELAY_S * 2)
        assert 0 < left <= 11
        assert await svc.drain(timeout_s=5) == 0

    asyncio.run(go())


def test_deleting_a_session_removes_it_from_memory_and_the_store() -> None:
    async def go() -> None:
        store = SlowStore()
        svc = WriteBehindSessionService(store, retry_delay_s=0.0)
        session = await svc.create_session(app_name=APP, user_id=USER, session_id=SID)
        await svc.append_event(session, _event("x"))
        await svc.delete_session(app_name=APP, user_id=USER, session_id=SID)
        assert await svc.get_session(app_name=APP, user_id=USER, session_id=SID) is None

    asyncio.run(go())


def test_a_real_two_turn_conversation_runs_from_memory_and_lands_whole_in_the_store() -> None:
    from eios.assistant.scripted_model import draft
    from eios.ontology.omcp.port.principal import principal_for

    from .conftest import make_runtime

    store = SlowStore()
    runtime, llm = make_runtime(
        [draft("First answer."), draft("Second answer.")],
        sessions=WriteBehindSessionService(store, retry_delay_s=0.0),
    )
    principal = principal_for("alice", "aml_investigator")

    async def go() -> list[str]:
        waited = []
        for question in ("first question", "second question"):
            out = await runtime.run_turn(
                principal=principal, question=question, entity_id="CR84920"
            )
            assert out.status == "ok"
            waited.append(out.timing["session"])
        # the first turn reads the store once to learn the thread is new; no write is ever waited on
        assert waited[0] < 2 * DELAY_S * 1000 and waited[1] < DELAY_S * 1000 / 2
        await runtime.flush()
        stored = await InMemorySessionService.get_session(
            store, app_name="eios-assistant", user_id="alice", session_id="aml_investigator:CR84920"
        )
        return [p.text for e in stored.events if e.content for p in e.content.parts if p.text]

    texts = asyncio.run(go())
    assert texts[0] == "first question" and "second question" in texts
    assert "First answer." in texts and "Second answer." in texts
    second_request = llm.seen[-1]
    assert any(
        "first question" in (p.text or "") for c in second_request.contents for p in c.parts or []
    )


def test_shutdown_drains_what_the_runtime_still_holds() -> None:
    from eios.assistant.scripted_model import draft
    from eios.cockpit import assistant_gateway
    from eios.ontology.omcp.port.principal import principal_for

    from .conftest import make_runtime

    store = SlowStore()
    runtime, _ = make_runtime(
        [draft("An answer.")], sessions=WriteBehindSessionService(store, retry_delay_s=0.0)
    )
    assistant_gateway.set_runtime_for_testing(runtime)

    async def go() -> int:
        await runtime.run_turn(
            principal=principal_for("alice", "aml_investigator"), question="q", entity_id="CR84920"
        )
        await assistant_gateway.drain_sessions(timeout_s=5)
        stored = await InMemorySessionService.get_session(
            store, app_name="eios-assistant", user_id="alice", session_id="aml_investigator:CR84920"
        )
        return len(stored.events)

    try:
        assert asyncio.run(go()) > 0
    finally:
        assistant_gateway.set_runtime_for_testing(None)


def test_turn_only_state_never_carries_into_the_next_turn() -> None:
    """temp: keys (the prompt-screened mark, the prefetch mark) live for one turn. A durable store never keeps them; the
    in-memory copy must not either, or the next turn would skip its own screening and prefetch."""

    async def go() -> None:
        svc = WriteBehindSessionService(SlowStore(), retry_delay_s=0.0)
        session = await svc.create_session(app_name=APP, user_id=USER, session_id=SID)
        await svc.append_event(
            session, _event("turn one", {"temp:input_screened": True, "kept": 1})
        )
        assert session.state["temp:input_screened"] is True  # visible for the rest of this turn
        next_turn = await svc.get_session(app_name=APP, user_id=USER, session_id=SID)
        assert "temp:input_screened" not in next_turn.state and next_turn.state["kept"] == 1

    asyncio.run(go())


def test_every_turn_runs_its_own_prefetch_with_write_behind_sessions() -> None:
    from dataclasses import replace

    from eios.assistant.scripted_model import draft
    from eios.ontology.omcp.port.principal import principal_for

    from .conftest import SETTINGS, make_runtime

    runtime, llm = make_runtime(
        [draft("First answer."), draft("Second answer.")],
        settings=replace(SETTINGS, prefetch=True),
        sessions=WriteBehindSessionService(SlowStore(), retry_delay_s=0.0),
    )
    principal = principal_for("alice", "aml_investigator")

    async def go() -> list[tuple[str, ...]]:
        steps = []
        for question in ("first", "second"):
            out = await runtime.run_turn(
                principal=principal, question=question, entity_id="CR84920"
            )
            steps.append(out.steps)
        return steps

    assert asyncio.run(go()) == [("get_aml_dossier",), ("get_aml_dossier",)]
    assert len(llm.seen) == 2  # one model call per turn: the second turn did not lose its prefetch


def test_a_new_turn_always_starts_unscreened_whatever_the_session_kept() -> None:
    from eios.assistant.runtime import _fresh_turn_state
    from eios.assistant.safety import SCREENED_KEY

    assert _fresh_turn_state(None, None)[SCREENED_KEY] is False


def test_the_model_client_is_built_once_per_model_and_reused_by_every_turn() -> None:
    from eios.assistant.runtime import AssistantRuntime
    from eios.assistant.sessions import build_session_service
    from eios.ontology.omcp.port.catalogue import build_port
    from eios.ontology.omcp.port.readmodels import ReadModels

    from .conftest import SETTINGS

    runtime = AssistantRuntime(
        port=build_port(ReadModels.default()),
        settings=SETTINGS,
        session_service=build_session_service(SETTINGS),
    )
    first = runtime._llm("model-a")
    assert runtime._llm("model-a") is first  # no new connection or token on the next turn
    assert runtime._llm("model-b") is not first
