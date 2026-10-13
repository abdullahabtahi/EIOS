"""Re-judge stored Turn Records with the deterministic faithfulness judge (spec 022, US1).

`python -m evals.agent.faithfulness_suite --records evals/recorded [--twice] [--report PATH]`

Records may be real runs (no `eval` block: any unsupported figure fails the run, which blocks a release) or
checker-regression records (an `eval.expected_supported` label: the judge must agree with the label).
No model and no network are used, so the verdict on a stored run never changes (FR-002).
Exit 0 pass, 1 a figure or the checker failed, 2 usage or input error.
"""

import argparse
import hashlib
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from eios.agent_gates.core.faithfulness import judge

DEFAULT_REPORT = Path("evals/reports/agent_faithfulness.json")


def load_records(directory: Path) -> list[dict[str, Any]]:
    """Every Turn Record JSON object under `directory`, in a stable order."""
    records: list[dict[str, Any]] = []
    for path in sorted(directory.rglob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        records.extend(data if isinstance(data, list) else [data])
    return records


def _expected(record: dict[str, Any]) -> bool | None:
    label = record.get("eval", {}).get("expected_supported", record.get("expected_supported"))
    return None if label is None else bool(label)


def judge_all(records: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for record in records:
        aliases = record.get("eval", {}).get("aliases") or None
        verdict = judge(record, aliases)
        expected = _expected(record)
        out.append(
            {
                "record_id": record.get("record_id"),
                "passed": verdict.passed,
                "expected": expected,
                "ok": verdict.passed if expected is None else verdict.passed == expected,
                "counts": dict(verdict.counts),
                "unsupported": [
                    {"text": v.text, "reason": v.reason, "candidates": list(v.candidates)}
                    for v in verdict.unsupported()
                ],
            }
        )
    return out


def fingerprint(results: Sequence[dict[str, Any]]) -> str:
    return hashlib.sha256(json.dumps(results, sort_keys=True).encode()).hexdigest()


def summarise(results: Sequence[dict[str, Any]]) -> dict[str, Any]:
    real = [r for r in results if r["expected"] is None]
    figures = sum(r["counts"]["supported"] + r["counts"]["unsupported"] for r in real)
    supported = sum(r["counts"]["supported"] for r in real)
    return {
        "records": len(results),
        "unlabelled_records": len(real),
        "faithfulness_rate": (supported / figures) if figures else None,
        "failures": [r for r in results if not r["ok"]],
    }


def run(records_dir: Path, twice: bool, report: Path) -> int:
    records = load_records(records_dir)
    if not records:
        print(f"no records under {records_dir}", file=sys.stderr)
        return 2
    first = judge_all(records)
    deterministic = None if not twice else fingerprint(first) == fingerprint(judge_all(records))
    summary = summarise(first) | {"deterministic": deterministic, "fingerprint": fingerprint(first)}
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(summary | {"results": first}, indent=1) + "\n", encoding="utf-8")
    failed = bool(summary["failures"]) or deterministic is False
    print(
        f"agent-faithfulness: {summary['records']} records, {len(summary['failures'])} failures, "
        f"deterministic={deterministic}"
    )
    return 1 if failed else 0


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="python -m evals.agent.faithfulness_suite")
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument(
        "--twice", action="store_true", help="judge twice and require identical verdicts"
    )
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)
    return run(args.records, args.twice, args.report)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
