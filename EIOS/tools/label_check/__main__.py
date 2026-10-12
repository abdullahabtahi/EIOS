"""``python -m tools.label_check``: fail on unlabelled or mis-evidenced claims."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping, Sequence

from tools.common.cli import run_tool
from tools.common.findings import Finding
from tools.label_check.scanner import ScanResult, scan_repo

TOOL = "label_check"


def main(argv: Sequence[str]) -> int:
    holder: list[ScanResult] = []

    def func(args: argparse.Namespace) -> Sequence[Finding]:
        result = scan_repo(args.repo_root)
        holder.append(result)
        print(f"scanned {len(result.scanned)} files, {len(result.findings)} findings")
        return result.findings

    def extra() -> Mapping[str, object]:
        result = holder[0]
        return {
            "scanned_count": len(result.scanned),
            "scanned_files": list(result.scanned),
            "excluded_paths": list(result.excluded),
            "spike_states": dict(result.spike_states),
        }

    return run_tool(TOOL, func, argv, report_extra=extra)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
