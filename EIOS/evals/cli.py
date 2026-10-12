"""``python -m evals.cli run --tier <tier>``: run one tier of the gate hook registry.

Reads ``evals/registry.yaml`` of the target repo (cwd, or ``--repo-root``) and runs the tier
through the shared runner. Exit 0 pass (including "no suites registered"), 1 a suite failed
or produced no report, 2 registry or tool error.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from tools.common.cli import build_parser
from tools.gates.entry import require_directory, run_entry
from tools.gates.registry import Tier, load_registry
from tools.gates.run_record import GateResult, Workflow
from tools.gates.runner import RunSettings, format_footer, format_result_line, run_suites
from tools.gates.sbom import generate_sbom, sbom_ref

PROG = "python -m evals.cli"
REGISTRY = Path("evals") / "registry.yaml"


def _build_parser() -> argparse.ArgumentParser:
    parser = build_parser("evals.cli", "Run evaluation suites from the gate hook registry.")
    parser.prog = PROG
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="run every suite of one tier")
    run.add_argument("--tier", required=True, choices=[t.value for t in Tier])
    run.add_argument(
        "--workflow",
        choices=[w.value for w in Workflow],
        default=Workflow.PR.value,
        help="workflow identity (default: pr); decides which tiers may run",
    )
    sbom = run.add_mutually_exclusive_group()
    sbom.add_argument(
        "--sbom-ref",
        default=None,
        help="repo-relative SBOM path recorded on the run (required by release-candidate runs)",
    )
    sbom.add_argument(
        "--generate-sbom",
        action="store_true",
        help="build the SBOM from uv.lock and record its path (release-candidate gate)",
    )
    run.add_argument(
        "--id-prefix",
        default="",
        help="run only suites whose id starts with this prefix (e.g. resilience-)",
    )
    run.add_argument("--repo-root", type=Path, default=argparse.SUPPRESS)
    return parser


def _handle(args: argparse.Namespace) -> int:
    repo_root = require_directory(args.repo_root, "repo root")
    entries = tuple(
        e for e in load_registry(repo_root / REGISTRY) if e.id.startswith(args.id_prefix)
    )
    ref = sbom_ref(repo_root, generate_sbom(repo_root)) if args.generate_sbom else args.sbom_ref
    settings = RunSettings(repo_root=repo_root, workflow=Workflow(args.workflow), sbom_ref=ref)

    def show(result: GateResult) -> None:
        print(format_result_line(result), flush=True)

    outcome = run_suites(entries, settings, frozenset({Tier(args.tier)}), on_result=show)
    for line in format_footer(outcome, show_quarantine=False):
        print(line)
    return outcome.exit_code


def main(argv: Sequence[str] | None = None) -> int:
    return run_entry(PROG, _build_parser(), _handle, argv)


if __name__ == "__main__":
    sys.exit(main())
