"""A figure's sign is part of what it says: a loss written as a gain must not pass, and a loss written as a loss must."""

from datetime import UTC, datetime

import pytest

from eios.assistant.assembly import Assembled, Rejected, TurnFact, assemble_draft
from eios.ontology.omcp.port.contracts import DataOrigin

AS_OF = datetime(2026, 10, 17, 9, 0, tzinfo=UTC)
_RAW = {
    "exec.what_if:-:impact": ("USD", -32500.0),
    "exec.what_if:-:interval_low": ("USD", -37375.0),
    "exec.what_if:-:deposit_delta": ("percent", -4.12),
    "exec.what_if:-:churn_delta": ("percent", 7.1),
}
FACTS = {
    fid: TurnFact(fid, value, unit, AS_OF, DataOrigin.FIXTURE, "fixture.source")
    for fid, (unit, value) in _RAW.items()
}


def _traced(draft: str):
    return assemble_draft(draft, facts=FACTS, trace_typed=True)


@pytest.mark.parametrize(
    ("draft", "fact_id"),
    [
        ("Revenue impact is -$32,500.", "exec.what_if:-:impact"),
        ("Revenue impact is $-32,500.", "exec.what_if:-:impact"),
        ("Revenue impact is −$32,500.", "exec.what_if:-:impact"),  # a true minus sign
        ("The low end is -$37,375.", "exec.what_if:-:interval_low"),
        ("First deposits move -4.12%.", "exec.what_if:-:deposit_delta"),
        ("Churn rises 7.1%.", "exec.what_if:-:churn_delta"),
    ],
)
def test_a_negative_figure_written_with_its_sign_is_shown_and_cited(
    draft: str, fact_id: str
) -> None:
    out = _traced(draft)
    assert isinstance(out, Assembled), out
    assert [f.fact_id for f in out.figures] == [fact_id]


@pytest.mark.parametrize(
    "draft",
    [
        "Revenue impact is $32,500.",  # a loss written as a gain
        "First deposits move 4.12%.",
        "Churn falls -7.1%.",  # a rise written as a fall
    ],
)
def test_a_figure_with_the_wrong_sign_is_rejected(draft: str) -> None:
    assert isinstance(_traced(draft), Rejected)
