"""``python -m tools.gates.run_gate <gate-id>``: run one gate from config/gates.yaml.

CI runs this once per gate so each gate is its own status check. Exit 0 pass, 1 gate failed,
2 tool or configuration error.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from eios.common.errors import ToolError
from tools.common.cli import build_parser
from tools.gates.entry import (
    add_common_arguments,
    execute_gates,
    load_config,
    require_directory,
    run_entry,
)
from tools.gates.run_record import Workflow
from tools.gates.runner import RunSettings

PROG = "python -m tools.gates.run_gate"


def _build_parser() -> argparse.ArgumentParser:
    parser = build_parser("gates.run_gate", "Run one blocking gate from config/gates.yaml.")
    parser.add_argument("gate_id", help="id of a row in config/gates.yaml")
    add_common_arguments(parser)
    return parser


def _handle(args: argparse.Namespace) -> int:
    repo_root = require_directory(args.repo_root, "repo root")
    gates, quarantine = load_config(args.tool_root)
    selected = tuple(g for g in gates if g.id == args.gate_id)
    if not selected:
        known = ", ".join(g.id for g in gates)
        raise ToolError(f"unknown gate {args.gate_id!r}; known gates: {known}")
    settings = RunSettings(
        repo_root=repo_root, tool_root=args.tool_root, workflow=Workflow(args.workflow)
    )
    return execute_gates(selected, quarantine, settings)


def main(argv: Sequence[str] | None = None) -> int:
    return run_entry(PROG, _build_parser(), _handle, argv)


if __name__ == "__main__":
    sys.exit(main())
