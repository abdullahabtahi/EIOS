"""Shared plumbing for the gate command-line entry points (run_gate, local, evals.cli)."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from eios.common.errors import EiosError, ToolError
from tools.gates.gate_config import GateSpec, load_gates
from tools.gates.quarantine import QuarantineEntry, load_quarantine
from tools.gates.run_record import GateResult, Workflow
from tools.gates.runner import (
    RunSettings,
    default_tool_root,
    format_footer,
    format_result_line,
    run_gates,
)

EXIT_ERROR = 2


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--tool-root",
        type=Path,
        default=default_tool_root(),
        help="repository holding tools/, evals/, src/ and config/ (default: this repository)",
    )
    parser.add_argument(
        "--workflow",
        choices=[w.value for w in Workflow],
        default=Workflow.PR.value,
        help="workflow identity recorded on the run record (default: pr)",
    )


def require_directory(path: Path, what: str) -> Path:
    if not path.is_dir():
        raise ToolError(f"{what} is not a directory: {path}")
    return path


def load_config(tool_root: Path) -> tuple[tuple[GateSpec, ...], tuple[QuarantineEntry, ...]]:
    """Gates and quarantine entries from ``<tool_root>/config``."""
    gates = load_gates(tool_root / "config" / "gates.yaml")
    known = frozenset(g.id for g in gates)
    quarantine = load_quarantine(tool_root / "config" / "quarantine.yaml", known)
    return gates, quarantine


def execute_gates(
    gates: Sequence[GateSpec],
    quarantine: Sequence[QuarantineEntry],
    settings: RunSettings,
) -> int:
    """Run ``gates``, print one status line per gate as it finishes, then the footer."""

    def show(result: GateResult) -> None:
        print(format_result_line(result), flush=True)

    outcome = run_gates(gates, settings, quarantine, on_result=show)
    for line in format_footer(outcome):
        print(line)
    return outcome.exit_code


def run_entry(
    prog: str,
    parser: argparse.ArgumentParser,
    handler: Callable[[argparse.Namespace], int],
    argv: Sequence[str] | None,
) -> int:
    """Parse and run ``handler`` under the 0 / 1 / 2 exit-code contract."""
    try:
        args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))
        return handler(args)
    except EiosError as exc:
        print(f"{prog}: error: {exc}", file=sys.stderr)
    except Exception as exc:  # noqa: BLE001 - reported on stderr, mapped to exit code 2
        print(f"{prog}: unexpected error: {type(exc).__name__}: {exc}", file=sys.stderr)
    return EXIT_ERROR
