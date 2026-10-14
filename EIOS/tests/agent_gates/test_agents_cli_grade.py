"""The faithfulness judge runs as a native `agents-cli eval` metric and agrees with our own suite (T-US6)."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from eios.agent_gates.core.faithfulness import judge
from eios.agent_gates.records import TurnRecord, to_agents_cli_case
from evals.agent.metrics.faithfulness import evaluate

EVALS = Path(__file__).resolve().parents[2] / "evals"
PINNED = json.loads(
    (EVALS / "recorded" / "pinned" / "pinned_cases.json").read_text(encoding="utf-8")
)


def _case(raw: dict[str, object]) -> dict[str, object]:
    record = {k: v for k, v in raw.items() if k != "eval"}
    return to_agents_cli_case(TurnRecord.model_validate(record))


def test_the_metric_shim_agrees_with_the_judge_on_every_pinned_case() -> None:
    for raw in PINNED:
        score = evaluate(_case(raw))["score"]
        assert (score == 1.0) is judge(raw).passed, raw["case_id"]


@pytest.mark.skipif(shutil.which("agents-cli") is None, reason="agents-cli is not installed")
def test_agents_cli_grades_the_pinned_cases_with_the_same_verdicts(tmp_path: Path) -> None:
    traces = tmp_path / "traces.json"
    traces.write_text(json.dumps({"eval_cases": [_case(r) for r in PINNED]}), encoding="utf-8")
    out = tmp_path / "out"
    subprocess.run(  # noqa: S603
        [
            str(shutil.which("agents-cli")),
            "eval",
            "grade",
            "--traces",
            str(traces),
            "--config",
            str(EVALS / "agent" / "eval_config.yaml"),
            "--output",
            str(out),
        ],
        check=True,
        capture_output=True,
        cwd=EVALS.parent,
        env={**os.environ, "AGENTS_CLI_TELEMETRY": "0"},
    )
    result = json.loads(next(out.glob("results_*.json")).read_text(encoding="utf-8"))
    scores = [
        r["response_candidate_results"][0]["metric_results"]["figure_faithfulness"]["score"]
        for r in result["eval_case_results"]
    ]
    assert [s == 1.0 for s in scores] == [judge(r).passed for r in PINNED]
