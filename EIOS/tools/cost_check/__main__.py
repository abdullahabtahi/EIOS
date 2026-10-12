"""``python -m tools.cost_check [--repo-root DIR]``: exits 0 pass, 1 findings, 2 error."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Protocol

from tools.common.cli import run_tool
from tools.common.findings import Finding
from tools.cost_check.repo import CostResult, check_repo
from tools.cost_check.totals import render_totals, totals_to_dict

TOOL = "cost_check"


class Clock(Protocol):
    def now(self) -> datetime: ...


class _SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


def _print_result(result: CostResult) -> None:
    for warning in result.warnings:
        print(f"warning: {warning.file}:{warning.line}: {warning.rule_id}: {warning.message}")
    for finding in result.findings:
        print(f"{finding.file}:{finding.line}: {finding.rule_id}: {finding.message}")
    if result.totals is not None:
        print("\n".join(render_totals(result.totals)))
    print(f"cost_check: {len(result.findings)} findings, {len(result.warnings)} warnings")


def main(argv: Sequence[str], clock: Clock | None = None) -> int:
    today = (clock or _SystemClock()).now().date()
    holder: list[CostResult] = []

    def func(args: argparse.Namespace) -> Sequence[Finding]:
        result = check_repo(args.repo_root, today)
        holder.append(result)
        _print_result(result)
        return result.findings

    def extra() -> Mapping[str, object]:
        result = holder[0]
        return {
            "warnings": [w.to_dict() for w in result.warnings],
            "totals": totals_to_dict(result.totals) if result.totals is not None else None,
            "checked_on": today.isoformat(),
        }

    return run_tool(TOOL, func, argv, report_extra=extra)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
