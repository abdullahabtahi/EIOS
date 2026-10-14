"""Serves the records of an earlier run so the judges can be re-run without calling a model (spec 022).

A fix to a judge can then be checked against what a live run actually produced, in seconds and for free.
A turn that was not in the earlier run is reported inconclusive, never invented.
"""

import json
from pathlib import Path

from eios.agent_gates.port import TurnRequest, inconclusive_record
from eios.agent_gates.records import TurnRecord


class RecordedRuntime:
    """Looks a record up by case id and repeat index."""

    def __init__(self, records_path: Path, runtime_name: str = "copilot") -> None:
        self.runtime_name = runtime_name
        lines = records_path.read_text(encoding="utf-8").splitlines()
        loaded = [TurnRecord.model_validate(json.loads(line)) for line in lines if line.strip()]
        self._by_key = {(r.case_id, r.repeat): r for r in loaded}

    def run_turn(self, request: TurnRequest) -> TurnRecord:
        found = self._by_key.get((request.case_id, request.repeat))
        if found is None:
            return inconclusive_record(
                request, self.runtime_name, "turn absent from the recorded run"
            )
        return found
