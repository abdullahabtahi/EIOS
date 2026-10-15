"""The drafter's instruction: a figure from an earlier answer is never valid, and a redraft is told to fetch it again."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from eios.assistant.agents import instruction_for
from eios.assistant.assembler_agent import FEEDBACK_KEY
from eios.ontology.omcp.port.principal import Workstation


def _text(plain: bool, state: dict[str, str]) -> str:
    ctx = SimpleNamespace(state=state)
    return instruction_for(Workstation.PARTNER_MANAGER, plain_figures=plain)(ctx)  # type: ignore[arg-type]


def test_plain_instruction_says_earlier_answers_do_not_count() -> None:
    text = _text(True, {})
    assert "earlier answers do not count" in text
    assert "call the tool that returns it again" in text


@pytest.mark.parametrize("plain", [True, False])
def test_redraft_never_forbids_calling_a_tool_again(plain: bool) -> None:
    text = _text(plain, {FEEDBACK_KEY: "figure x matches no figure a tool returned this turn"})
    assert "do not call those tools again" not in text
    assert "call the tool that returns it again now" in text
