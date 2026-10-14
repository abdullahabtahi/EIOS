"""Run the quality gates against a runtime and write one report (spec 022, US4).

`python -m evals.agent.baseline --runtime copilot [--live] [--repeats 3] [--compare EARLIER.json]`

Offline (the default) uses the copilot's deterministic replay path: free, repeatable, and exactly the path an
outage would serve. `--live` calls the model through the existing gateway and needs `EIOS_AGENT_EVAL_MAX_TURNS`
(a hard cap, checked before the first call) and an EIOS project as quota project. The thresholds file must be
committed before any run (pre-registration). A case the runtime cannot serve is reported as such, never skipped.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from eios.agent_gates.capabilities import Availability, default_map
from eios.agent_gates.cases import (
    AttackCase,
    GoldenCase,
    GoldenTurn,
    load_attack_cases,
    load_golden_cases,
)
from eios.agent_gates.core.consistency import compare_to_payload
from eios.agent_gates.core.faithfulness import judge
from eios.agent_gates.core.safety import judge_attack, pass_all
from eios.agent_gates.core.trajectory import judge_turn
from eios.agent_gates.port import AgentPort, TurnRequest, run_with_deadline
from eios.agent_gates.records import Outcome, TurnRecord
from eios.agent_gates.report import build_report, compare_reports, render_markdown
from evals.agent.screen_payloads import load_payload

HERE = Path(__file__).resolve().parent
GOLDEN = HERE.parent / "golden"
OPERATOR = "tok_op_baseline"
_GIT = shutil.which("git") or "git"


class ThresholdsError(RuntimeError):
    pass


class SpendCapError(RuntimeError):
    pass


def load_thresholds(path: Path, require_committed: bool = True) -> dict[str, Any]:
    if not path.is_file():
        raise ThresholdsError(f"thresholds file is missing: {path}")
    if require_committed:
        tracked = subprocess.run(  # noqa: S603
            [_GIT, "ls-files", "--error-unmatch", str(path)],
            capture_output=True,
            check=False,
        )
        dirty = subprocess.run(  # noqa: S603
            [_GIT, "status", "--porcelain", "--", str(path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if tracked.returncode != 0 or dirty.stdout.strip():
            raise ThresholdsError(f"thresholds must be committed before a run: {path}")
    return dict(yaml.safe_load(path.read_text(encoding="utf-8")))


def check_spend_cap(turns: int, repeats: int, live: bool, cap_turns: int | None) -> None:
    """A live run states its budget up front and stops before it starts if the plan exceeds it."""
    if not live:
        return
    if cap_turns is None:
        raise SpendCapError("a live run needs EIOS_AGENT_EVAL_MAX_TURNS")
    if turns * repeats > cap_turns:
        raise SpendCapError(f"{turns * repeats} live turns planned, cap is {cap_turns}")


def _runtime_key(runtime_name: str) -> str:
    return "copilot" if runtime_name == "copilot" else "target"


_UNSERVED = (Availability.CAPABILITY_MISSING, Availability.PLANNED)


def _unserved(key: str, capability: str) -> bool:
    """A capability the runtime cannot serve today: missing, or planned for a later spec. Never a pass."""
    return default_map().availability(key, capability) in _UNSERVED


def _row(
    case: str, ws: str, suite: str, verdicts: Sequence[tuple[bool, str]], **extra: Any
) -> dict[str, Any]:
    failed = [e for ok, e in verdicts if not ok]
    return {
        "case_id": case,
        "workstation": ws,
        "suite": suite,
        "verdict": "fail" if failed else "pass",
        "evidence": failed[0] if failed else "",
        "pass_rate": sum(ok for ok, _ in verdicts) / len(verdicts),
        **extra,
    }


def _inconclusive(case: str, ws: str, suite: str, why: str) -> dict[str, Any]:
    return {
        "case_id": case,
        "workstation": ws,
        "suite": suite,
        "verdict": "inconclusive",
        "evidence": why,
    }


def _crashed(record: TurnRecord) -> bool:
    """A runtime exception is a failure of the runtime; only a deadline overrun is inconclusive."""
    reason = record.inconclusive_reason or ""
    return record.outcome is Outcome.INCONCLUSIVE and not reason.startswith("deadline")


def _failed_row(case: str, ws: str, suite: str, record: TurnRecord) -> dict[str, Any]:
    return {
        "case_id": case,
        "workstation": ws,
        "suite": suite,
        "verdict": "fail",
        "evidence": f"{case}: runtime crashed: {record.inconclusive_reason}",
    }


def _meta(record: TurnRecord) -> dict[str, Any]:
    return {
        "latency_ms": record.latency_ms,
        "data_origin": record.data_origin.value,
        "identity_source": record.identity_source.value,
        "cost_usd": record.cost_usd,
    }


def _detail(judged: Any) -> str:
    return "; ".join(f"'{v.text}' {v.reason}" for v in judged.unsupported())


def _diff_text(diffs: Sequence[dict[str, Any]]) -> str:
    return ", ".join(
        f"answer {x['answer_text']} vs screen {x['payload_value']} ({x['payload_path']})"
        for x in diffs
    )


def _golden_rows(
    port: AgentPort, case: GoldenCase, turn: GoldenTurn, repeats: int, records: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    cid, ws, key = (
        f"{case.scenario_id}.t{turn.turn_index}",
        case.workstation.value,
        _runtime_key(port.runtime_name),
    )
    got: list[TurnRecord] = []
    for r in range(repeats):
        request = TurnRequest(
            question=turn.user_query,
            role=case.workstation,
            operator_id=OPERATOR,
            session_id=f"{cid}.{r}",
            turn_index=1,
            case_id=cid,
            repeat=r,
            entity_context=None,
        )
        got.append(run_with_deadline(port, request))
        records.append(got[-1].to_json_dict())
    done = [g for g in got if g.outcome is Outcome.COMPLETED]
    if not done and _crashed(got[0]):
        return [_failed_row(cid, ws, s, got[0]) for s in ("faithfulness", "trajectory")]
    if not done:
        return [
            _inconclusive(cid, ws, s, got[0].inconclusive_reason or "no turn completed")
            for s in ("faithfulness", "trajectory")
        ]
    aliases = turn.aliases or None
    judged = [judge(g.to_json_dict(), aliases) for g in done]
    supported = sum(j.counts["supported"] for j in judged)
    total = supported + sum(j.counts["unsupported"] for j in judged)
    rows = [
        _row(
            cid,
            ws,
            "faithfulness",
            [(j.passed, f"{cid}: {_detail(j)}") for j in judged],
            figures_supported=supported,
            figures_total=total,
            **_meta(done[0]),
        )
    ]
    turn_dict = turn.model_dump(mode="json")
    missing = [c.capability for c in turn.expected_capabilities if _unserved(key, c.capability)]
    trajectories = [judge_turn(g.to_json_dict(), turn_dict) for g in done]
    verdicts = [
        (
            t["passed"] and not missing,
            f"{cid}: " + ("; ".join(t["reasons"]) or "capability_missing: " + ", ".join(missing)),
        )
        for t in trajectories
    ]
    rows.append(_row(cid, ws, "trajectory", verdicts, capability_missing=missing, **_meta(done[0])))
    if turn.screen_payload:
        payload = load_payload(turn.screen_payload)
        diffs = [compare_to_payload(g.to_json_dict(), payload, aliases) for g in done]
        rows.append(
            _row(
                cid,
                ws,
                "consistency",
                [(not d, f"{cid}: {_diff_text(d)}") for d in diffs],
                **_meta(done[0]),
            )
        )
    return rows


def _control_record(
    port: AgentPort, attack: AttackCase, repeat: int, records: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """The same question with no injected text, to tell what the injection caused from what the runtime does anyway."""
    request = TurnRequest(
        question=attack.setup.question,
        role=attack.setup.role,
        operator_id=OPERATOR,
        session_id=f"{attack.case_id}.control.{repeat}",
        case_id=f"{attack.case_id}.control",
        repeat=repeat,
    )
    record = run_with_deadline(port, request)
    records.append(record.to_json_dict())
    return record.to_json_dict() if record.outcome is Outcome.COMPLETED else None


def _attack_rows(
    port: AgentPort, attack: AttackCase, repeats: int, records: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    ws, key = attack.setup.role.value, _runtime_key(port.runtime_name)
    lacking = [c for c in attack.setup.tool_fixtures if _unserved(key, c)]
    if lacking:
        return [
            _inconclusive(attack.case_id, ws, "safety", f"capability_missing: {', '.join(lacking)}")
        ]
    results: list[dict[str, Any]] = []
    for r in range(max(repeats, attack.repeats)):
        request = TurnRequest(
            question=attack.setup.question,
            role=attack.setup.role,
            operator_id=OPERATOR,
            session_id=f"{attack.case_id}.{r}",
            case_id=attack.case_id,
            repeat=r,
            tool_fixtures=attack.setup.tool_fixtures,
        )
        record = run_with_deadline(port, request)
        records.append(record.to_json_dict())
        if _crashed(record):
            return [_failed_row(attack.case_id, ws, "safety", record)]
        if record.outcome is not Outcome.COMPLETED:
            return [
                _inconclusive(
                    attack.case_id,
                    ws,
                    "safety",
                    record.inconclusive_reason or "turn did not complete",
                )
            ]
        control = _control_record(port, attack, r, records) if attack.setup.tool_fixtures else None
        results.append(
            judge_attack(record.to_json_dict(), attack.model_dump(mode="json"), control)
            | {"latency_ms": record.latency_ms}
        )
    evidence = next(
        (f"{attack.case_id}: {'; '.join(x['violations'])}" for x in results if not x["passed"]), ""
    )
    defects = sorted({d for x in results for d in x["defects"]})
    row = _row(
        attack.case_id,
        ws,
        "safety",
        [(x["passed"], evidence) for x in results],
        family=attack.family.value,
        paraphrased=attack.paraphrased,
        owasp=attack.owasp.value,
        defects=defects,
        latency_ms=results[0]["latency_ms"],
    )
    return [row | {"verdict": "pass" if pass_all(results) else "fail"}]


def run_baseline(
    port: AgentPort, golden: Sequence[GoldenCase], attacks: Sequence[AttackCase], repeats: int
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    for case in golden:
        for turn in case.turns:
            rows += _golden_rows(port, case, turn, repeats, records)
    for attack in attacks:
        rows += _attack_rows(port, attack, repeats, records)
    meta = {
        "date": datetime.now(UTC).isoformat(),
        "repeats": repeats,
        "git_sha": _git_sha(),
        "live": not getattr(port, "offline", True),
    }
    return build_report(port.runtime_name, rows, meta), records


def _git_sha() -> str:
    out = subprocess.run(  # noqa: S603
        [_GIT, "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=False
    )
    return out.stdout.strip() or "unknown"


def _port(runtime: str, live: bool, records: Path | None = None) -> AgentPort:
    if runtime == "recorded":
        from eios.agent_gates.adapters.recorded import RecordedRuntime

        if records is None:
            raise SystemExit("--runtime recorded needs --records")
        return RecordedRuntime(records)
    if runtime == "toolport":
        from eios.agent_gates.adapters.toolport import ToolPortRuntime

        return ToolPortRuntime()
    if runtime == "adk":
        from eios.agent_gates.adapters.adk import AdkRuntime

        return AdkRuntime(offline=not live)
    if runtime == "copilot":
        from eios.agent_gates.adapters.copilot import CopilotAdapter

        adapter = CopilotAdapter(offline=not live)
        adapter.offline = not live  # type: ignore[attr-defined]
        return adapter
    from eios.agent_gates.adapters.standin import AlwaysAnswerStandin

    return AlwaysAnswerStandin("42")


def main(argv: Sequence[str]) -> int:
    ap = argparse.ArgumentParser(prog="python -m evals.agent.baseline")
    ap.add_argument(
        "--runtime",
        choices=["copilot", "toolport", "adk", "always42", "recorded"],
        default="copilot",
    )
    ap.add_argument("--live", action="store_true")
    ap.add_argument(
        "--records", type=Path, help="records.jsonl of an earlier run, with --runtime recorded"
    )
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--out", type=Path, default=Path("evals/reports/agent_baseline"))
    ap.add_argument("--compare", type=Path)
    args = ap.parse_args(argv)
    try:
        thresholds = load_thresholds(HERE / "thresholds.yaml")
        golden, attacks = (
            load_golden_cases(GOLDEN / "agent_cases"),
            load_attack_cases(GOLDEN / "attacks"),
        )
        turns = sum(len(c.turns) for c in golden) + len(attacks)
        cap = os.getenv("EIOS_AGENT_EVAL_MAX_TURNS")
        check_spend_cap(turns, args.repeats, args.live, int(cap) if cap else None)
    except (ThresholdsError, SpendCapError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    report, records = run_baseline(
        _port(args.runtime, args.live, args.records), golden, attacks, args.repeats
    )
    report["meta"]["thresholds_version"] = thresholds.get("version")
    markdown = render_markdown(report)
    if args.compare:
        diff = compare_reports(json.loads(args.compare.read_text(encoding="utf-8")), report)
        markdown += f"\n## Against the earlier report\n\n- improved: {diff['improved']}\n- regressed: {diff['regressed']}\n- unchanged: {len(diff['unchanged'])}\n"
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "report.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    (args.out / "report.md").write_text(markdown, encoding="utf-8")
    (args.out / "records.jsonl").write_text(
        "\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8"
    )
    print(f"{args.runtime}: {report['counts']} -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
