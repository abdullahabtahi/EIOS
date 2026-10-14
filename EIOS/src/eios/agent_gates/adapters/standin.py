"""Trivial runtimes that prove the gates do not depend on the current implementation (spec 022, US6)."""

from eios.agent_gates.port import TurnRequest, completed_record
from eios.agent_gates.records import TurnRecord


class AlwaysAnswerStandin:
    """Answers the same text to everything and calls no tool; the gates must fail it."""

    def __init__(self, answer: str = "42") -> None:
        self.runtime_name = "standin:always"
        self._answer = answer

    def run_turn(self, request: TurnRequest) -> TurnRecord:
        return completed_record(request, self.runtime_name, self._answer)


class ScriptedStandin:
    """Returns pre-built records by question; used to test suites without a runtime."""

    def __init__(self, records: dict[str, TurnRecord]) -> None:
        self.runtime_name = "standin:scripted"
        self._records = records

    def run_turn(self, request: TurnRequest) -> TurnRecord:
        return self._records[request.question]
