"""Agent port tests (T013): a runtime that is slow or crashes yields an inconclusive record."""

import time

from eios.agent_gates.port import TurnRequest, run_with_deadline
from eios.agent_gates.records import Outcome, Role, TurnRecord


def _request(deadline_s: float = 0.2) -> TurnRequest:
    return TurnRequest(
        question="q",
        role=Role.EXECUTIVE,
        operator_id="tok_op_1",
        session_id="s",
        turn_index=1,
        deadline_s=deadline_s,
    )


class _Slow:
    runtime_name = "slow"

    def run_turn(self, request: TurnRequest) -> TurnRecord:
        time.sleep(1.0)
        raise AssertionError("must not be awaited")


class _Crash:
    runtime_name = "crash"

    def run_turn(self, request: TurnRequest) -> TurnRecord:
        raise RuntimeError("boom")


def test_a_deadline_overrun_yields_an_inconclusive_record_not_an_exception() -> None:
    record = run_with_deadline(_Slow(), _request(0.1))
    assert record.outcome is Outcome.INCONCLUSIVE
    assert record.inconclusive_reason is not None
    assert "deadline" in record.inconclusive_reason


def test_a_crash_yields_an_inconclusive_record_naming_the_error() -> None:
    record = run_with_deadline(_Crash(), _request())
    assert record.outcome is Outcome.INCONCLUSIVE
    assert record.inconclusive_reason is not None
    assert "RuntimeError" in record.inconclusive_reason


def test_request_defaults_are_safe() -> None:
    request = _request()
    assert request.tool_fixtures == {}
    assert request.repeat == 0
