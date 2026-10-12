"""``python -m tools.gates.local``: the single local entry point (``make check``).

Runs every ``pr``-stage gate from config/gates.yaml in config order, prints one status line per
gate, writes a run record with workflow ``pr`` and exits 1 if any gate failed. It runs exactly
the gates ``.github/workflows/pr.yml`` runs, in the same order.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from tools.common.cli import build_parser
from tools.gates.entry import (
    add_common_arguments,
    execute_gates,
    load_config,
    require_directory,
    run_entry,
)
from tools.gates.gate_config import GateSpec, Stage, load_gates, select_gates
from tools.gates.run_record import Workflow
from tools.gates.runner import RunSettings, default_tool_root

PROG = "python -m tools.gates.local"
LOCAL_STAGE: Stage = "pr"


def local_gates(tool_root: Path | None = None) -> tuple[GateSpec, ...]:
    root = default_tool_root() if tool_root is None else tool_root
    return select_gates(load_gates(root / "config" / "gates.yaml"), LOCAL_STAGE)


def local_gate_ids(tool_root: Path | None = None) -> tuple[str, ...]:
    """Ordered ids of the gates this entry point runs."""
    return tuple(g.id for g in local_gates(tool_root))


def _build_parser() -> argparse.ArgumentParser:
    parser = build_parser("gates.local", "Run every pr-stage gate, as the pipeline does.")
    add_common_arguments(parser)
    return parser


def _handle(args: argparse.Namespace) -> int:
    repo_root = require_directory(args.repo_root, "repo root")
    _, quarantine = load_config(args.tool_root)
    settings = RunSettings(
        repo_root=repo_root, tool_root=args.tool_root, workflow=Workflow(args.workflow)
    )
    return execute_gates(local_gates(args.tool_root), quarantine, settings)


def main(argv: Sequence[str] | None = None) -> int:
    return run_entry(PROG, _build_parser(), _handle, argv)


if __name__ == "__main__":
    sys.exit(main())
