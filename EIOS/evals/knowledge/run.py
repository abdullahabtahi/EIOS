"""Measure the live regulatory index: `python -m evals.knowledge.run --project <id> --data-store <id>`.

Reads only; calls the search API once per case (15 queries). Writes `evals/reports/knowledge/report.json`.
"""

import argparse
import json
from pathlib import Path

from eios.knowledge.agent_search import AgentSearchIndex
from eios.knowledge.evaluate import evaluate, load_cases

HERE = Path(__file__).resolve().parent
REPORT = HERE.parent / "reports" / "knowledge" / "report.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--data-store", required=True)
    parser.add_argument("--relevance", default="LOW", choices=["LOWEST", "LOW", "MEDIUM", "HIGH"])
    args = parser.parse_args()
    report = evaluate(
        AgentSearchIndex(args.project, args.data_store, relevance=args.relevance),
        load_cases(HERE / "cases.yaml"),
    )
    report["relevance_threshold"] = args.relevance
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2))
    for row in report["rows"]:
        print(f"{row['id']:<32} rank={row['rank']!s:<5} returned={row['returned']} {row['top']}")
    print({k: v for k, v in report.items() if k != "rows"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
