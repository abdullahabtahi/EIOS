"""``python -m tools.adr_check [--repo-root DIR]``: exits 0 pass, 1 findings, 2 error."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from tools.adr_check.repo import check_repo
from tools.common.cli import run_tool
from tools.common.findings import Finding

TOOL = "adr_check"


def main(argv: Sequence[str]) -> int:
    def func(args: argparse.Namespace) -> Sequence[Finding]:
        findings = check_repo(args.repo_root)
        print(f"adr_check: {len(findings)} findings")
        return findings

    return run_tool(TOOL, func, argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
