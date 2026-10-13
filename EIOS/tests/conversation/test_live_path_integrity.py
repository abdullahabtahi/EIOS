"""The copilot must never present a replay as a live answer (RL-7) and must target a real endpoint."""

from unittest.mock import MagicMock

import pytest

from eios.conversation.client import GeminiClientManager
from eios.conversation.copilot_engine import CopilotEngine
from eios.conversation.models import OperatorRole


def _manager_with(client: MagicMock) -> GeminiClientManager:
    manager = GeminiClientManager(project="example-project", offline_mode=False)
    manager._client = client
    return manager


def test_location_defaults_to_global_when_env_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GOOGLE_CLOUD_LOCATION", raising=False)
    assert GeminiClientManager(project="example-project").location == "global"


def test_missing_project_degrades_to_offline_with_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    manager = GeminiClientManager()
    assert manager.get_client() is None
    assert manager.offline_mode is True
    assert "GOOGLE_CLOUD_PROJECT" in (manager.offline_reason or "")


def test_offline_answer_is_labelled_replay() -> None:
    res = CopilotEngine(offline_mode=True).process_query(
        query="Provide current enterprise net revenue status", role=OperatorRole.EXECUTIVE
    )
    assert res.is_replay_fallback is True
    assert res.fallback_reason


def test_live_failure_is_labelled_replay_with_reason() -> None:
    client = MagicMock()
    client.chats.create.side_effect = RuntimeError("404 model not found")
    engine = CopilotEngine(client_manager=_manager_with(client))
    res = engine.process_query(
        query="Provide current enterprise net revenue status", role=OperatorRole.EXECUTIVE
    )
    assert res.is_replay_fallback is True
    assert "404 model not found" in (res.fallback_reason or "")


def test_live_success_is_not_labelled_replay() -> None:
    client = MagicMock()
    chat = MagicMock()
    client.chats.create.return_value = chat
    reply = MagicMock()
    reply.function_calls = []
    reply.text = "Nothing numeric to report."
    chat.send_message.return_value = reply
    res = CopilotEngine(client_manager=_manager_with(client)).process_query(
        query="Say hello", role=OperatorRole.EXECUTIVE
    )
    assert res.is_replay_fallback is False
    assert res.fallback_reason is None
