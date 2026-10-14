"""The recorded runtime re-judges an earlier run without calling a model."""

import json
from pathlib import Path

from eios.agent_gates.adapters.recorded import RecordedRuntime
from eios.agent_gates.port import TurnRequest, completed_record
from eios.agent_gates.records import Outcome, Role


def _request(case_id: str, repeat: int = 0) -> TurnRequest:
    return TurnRequest(
        question="q",
        role=Role.EXECUTIVE,
        operator_id="op-1",
        session_id="s",
        case_id=case_id,
        repeat=repeat,
    )


def test_serves_the_stored_record_by_case_and_repeat(tmp_path: Path) -> None:
    stored = completed_record(_request("c1"), "copilot", "stored answer")
    path = tmp_path / "records.jsonl"
    path.write_text(json.dumps(stored.to_json_dict()) + "\n", encoding="utf-8")
    runtime = RecordedRuntime(path)
    assert runtime.run_turn(_request("c1")).answer == "stored answer"


def test_a_turn_absent_from_the_run_is_inconclusive_not_invented(tmp_path: Path) -> None:
    path = tmp_path / "records.jsonl"
    path.write_text("", encoding="utf-8")
    got = RecordedRuntime(path).run_turn(_request("missing"))
    assert got.outcome is Outcome.INCONCLUSIVE
