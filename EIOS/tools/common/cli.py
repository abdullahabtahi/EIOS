"""The tool contract: argument base, exit codes 0/1/2, and a clean error path."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Mapping, Sequence
from enum import IntEnum
from pathlib import Path
from typing import NoReturn

from eios.common.errors import EiosError, ToolError
from tools.common.findings import Finding
from tools.common.report import write_report


class ExitCode(IntEnum):
    PASS = 0
    FINDINGS = 1
    ERROR = 2


ToolFunc = Callable[[argparse.Namespace], Sequence[Finding]]
ReportExtra = Callable[[], Mapping[str, object]]


class _ToolArgumentParser(argparse.ArgumentParser):
    """Raises ``ToolError`` on bad arguments instead of exiting from inside argparse."""

    def error(self, message: str) -> NoReturn:
        raise ToolError(f"{self.prog}: {message}")


def exit_code_for(findings: Sequence[Finding]) -> ExitCode:
    return ExitCode.FINDINGS if findings else ExitCode.PASS


def build_parser(tool: str, description: str) -> argparse.ArgumentParser:
    """Argument base shared by every tool; extend it with ``add_argument``."""
    parser = _ToolArgumentParser(prog=f"python -m tools.{tool}", description=description)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="repository root (default: current directory)",
    )
    return parser


def _execute(
    name: str, func: ToolFunc, argv: Sequence[str], report_extra: ReportExtra | None = None
) -> ExitCode:
    args = build_parser(name, f"{name} tool").parse_args(list(argv))
    repo_root: Path = args.repo_root
    if not repo_root.is_dir():
        raise ToolError(f"repo root is not a directory: {repo_root}")
    findings = tuple(func(args))
    write_report(repo_root, name, findings, report_extra() if report_extra else None)
    return exit_code_for(findings)


def run_tool(
    name: str, func: ToolFunc, argv: Sequence[str], report_extra: ReportExtra | None = None
) -> int:
    """Run ``func`` under the exit-code contract and return the process exit code.

    ``report_extra`` is called after ``func`` and its mapping is merged into the report.
    """
    try:
        return int(_execute(name, func, argv, report_extra))
    except EiosError as exc:
        print(f"{name}: error: {exc}", file=sys.stderr)
    except Exception as exc:
        print(f"{name}: unexpected error: {type(exc).__name__}: {exc}", file=sys.stderr)
    return int(ExitCode.ERROR)
