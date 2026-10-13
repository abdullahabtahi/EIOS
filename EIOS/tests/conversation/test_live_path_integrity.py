"""The copilot must never present a replay as a live answer (RL-7) and must target a real endpoint."""

from types import SimpleNamespace
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


def _reply(text=None, calls=()):
    reply = MagicMock()
    reply.text = text
    reply.function_calls = [SimpleNamespace(name=n, args=a) for n, a in calls]
    return reply


def test_engine_disables_sdk_automatic_function_calling() -> None:
    client = MagicMock()
    chat = client.chats.create.return_value
    chat.send_message.return_value = _reply("Nothing numeric to report.")
    CopilotEngine(client_manager=_manager_with(client)).process_query(
        query="Say hello", role=OperatorRole.EXECUTIVE
    )
    config = client.chats.create.call_args.kwargs["config"]
    assert config.automatic_function_calling.disable is True


def test_tools_requested_over_several_rounds_are_run_and_cited() -> None:
    client = MagicMock()
    chat = client.chats.create.return_value
    chat.send_message.side_effect = [
        _reply(calls=[("get_governed_metric", {"metric_id": "net_revenue_usd"})]),
        _reply(calls=[("get_governed_metric", {"metric_id": "net_revenue_usd"})]),
        _reply("Enterprise net revenue is anchored at $3,820,000 USD."),
    ]
    res = CopilotEngine(client_manager=_manager_with(client)).process_query(
        query="Check net revenue", role=OperatorRole.EXECUTIVE
    )
    assert res.is_replay_fallback is False
    assert chat.send_message.call_count == 3
    assert res.citations.count("get_governed_metric") == 2


def test_unknown_tool_requests_are_refused_not_executed() -> None:
    from eios.conversation.copilot_engine import run_omcp_tool

    assert "unknown tool" in run_omcp_tool("drop_everything", {})["error"]


def test_a_failing_tool_is_reported_to_the_model_not_raised() -> None:
    from eios.conversation.copilot_engine import run_omcp_tool

    assert "error" in run_omcp_tool("get_governed_metric", {"wrong_argument": 1})


def test_tool_rounds_are_bounded() -> None:
    client = MagicMock()
    chat = client.chats.create.return_value
    chat.send_message.return_value = _reply(
        calls=[("get_governed_metric", {"metric_id": "net_revenue_usd"})]
    )
    CopilotEngine(client_manager=_manager_with(client)).process_query(
        query="Check net revenue", role=OperatorRole.EXECUTIVE
    )
    assert chat.send_message.call_count <= 1 + 4


def test_a_blocked_answer_is_corrected_once_with_the_auditors_findings() -> None:
    client = MagicMock()
    chat = client.chats.create.return_value
    chat.send_message.side_effect = [
        _reply(calls=[("get_governed_metric", {"metric_id": "net_revenue_usd"})]),
        _reply("Enterprise net revenue is $3,900,000 USD."),  # wrong figure: blocked
        _reply("Enterprise net revenue is $3,820,000 USD."),  # corrected
    ]
    res = CopilotEngine(client_manager=_manager_with(client)).process_query(
        query="Check net revenue", role=OperatorRole.EXECUTIVE
    )
    assert res.is_replay_fallback is False
    assert "3,820,000" in res.response_markdown
    assert res.reflection_cycles_used == 1
    correction = chat.send_message.call_args_list[2].args[0]
    assert "Metric Auditor blocked" in correction and "3,900,000" in correction


def test_correction_is_bounded_then_falls_back_honestly() -> None:
    client = MagicMock()
    chat = client.chats.create.return_value
    chat.send_message.side_effect = [
        _reply(calls=[("get_governed_metric", {"metric_id": "net_revenue_usd"})]),
        *[_reply("Enterprise net revenue is $3,900,000 USD.") for _ in range(5)],
    ]
    res = CopilotEngine(client_manager=_manager_with(client)).process_query(
        query="Check net revenue", role=OperatorRole.EXECUTIVE
    )
    assert res.is_replay_fallback is True
    assert "audit" in (res.fallback_reason or "")
    assert chat.send_message.call_count == 1 + 1 + 2  # tool round + first answer + two corrections
