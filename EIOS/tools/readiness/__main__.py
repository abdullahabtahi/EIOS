"""``python -m tools.readiness <feature> [--repo-root DIR]``; exits 0 ready, 1 blocked, 2 error."""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Mapping, Sequence

from eios.common.errors import ToolError
from tools.common.cli import run_tool
from tools.common.findings import Finding
from tools.readiness.engine import ReadinessResult, check_readiness

TOOL = "readiness"
_FEATURE_ID = re.compile(r"F[0-9]{2}")


def split_feature(argv: Sequence[str]) -> tuple[list[str], list[str]]:
    """Separate positional arguments from the options the shared parser understands."""
    options: list[str] = []
    positionals: list[str] = []
    takes_value = False
    for arg in argv:
        if takes_value:
            options.append(arg)
            takes_value = False
        elif arg.startswith("-"):
            options.append(arg)
            takes_value = arg == "--repo-root"
        else:
            positionals.append(arg)
    return options, positionals


def _feature_id(positionals: Sequence[str]) -> str:
    if len(positionals) != 1:
        raise ToolError("expected exactly one feature id, e.g. `python -m tools.readiness F03`")
    if not _FEATURE_ID.fullmatch(positionals[0]):
        raise ToolError(f"not a feature id (expected F00..F99): {positionals[0]!r}")
    return positionals[0]


def _print_result(result: ReadinessResult) -> None:
    for finding in result.findings:
        print(f"  - {finding.message}")
    if result.ready:
        print(f"{result.feature} is ready: every declared dependency is met")
    else:
        print(f"{result.feature} is blocked: {len(result.findings)} unmet dependencies")


def main(argv: Sequence[str]) -> int:
    options, positionals = split_feature(argv)
    holder: list[ReadinessResult] = []

    def func(args: argparse.Namespace) -> Sequence[Finding]:
        result = check_readiness(args.repo_root, _feature_id(positionals))
        holder.append(result)
        _print_result(result)
        return result.findings

    def extra() -> Mapping[str, object]:
        result = holder[0]
        return {"feature": result.feature, "ready": result.ready, "states": dict(result.states)}

    return run_tool(TOOL, func, options, report_extra=extra)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
