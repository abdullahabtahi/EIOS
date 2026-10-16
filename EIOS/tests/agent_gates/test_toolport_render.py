"""The reference renderer repeats a number only when a typed field backs it (spec 023); free text with one is dropped."""

from __future__ import annotations

import pytest

from eios.agent_gates.adapters.toolport_render import render_result


def _lines(payload: dict) -> str:
    return "\n".join(render_result("T", payload))


@pytest.mark.parametrize(
    "prose",
    [
        "Platform data freshness > 60s SLA breach",  # a unit glued to the number
        "Restore must finish inside a 15-minute window",  # a hyphenated number
        "Two payout tickets from last week are still unresolved",  # a number spelled out
        "Auditor Gate rejection rate > 15% across synthesis turns",
        "Fewer than 3 clients",
    ],
)
def test_prose_with_a_figure_no_field_backs_is_not_repeated(prose: str) -> None:
    out = _lines({"capability": "x", "runbooks": [{"runbook_id": "RB-1", "trigger": prose}]})
    assert prose not in out
    assert "RB-1" in out  # the identifier stays; only the unbacked prose goes


@pytest.mark.parametrize(
    "prose",
    [
        "A rival broker is offering my sub-affiliates a higher revenue share",
        "Contract Breach & DLQ Flood Triage",
        "Ledger Chain Break / Sequence Anomaly",
        "Onerous terms and stone cold silence",  # words that merely contain a number word
    ],
)
def test_ordinary_prose_is_still_repeated(prose: str) -> None:
    out = _lines({"capability": "x", "messages": [{"message_id": "M-1", "excerpt": prose}]})
    assert prose in out
