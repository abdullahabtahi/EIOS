# ruff: noqa: E501
"""Aggregator: run every infra check and return the combined findings.

``python -m tools.infra_checks [--repo-root DIR]`` exits 0 on a clean tree, 1 on findings,
2 on a tool error, and writes ``evals/reports/infra_checks.json``. Nothing here needs a
network or a Terraform binary.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from eios.common.errors import ConfigError
from tools.common.cli import run_tool
from tools.common.findings import Finding
from tools.infra_checks.budget import check_budgets
from tools.infra_checks.environments import ENV_PARENT, check_environments
from tools.infra_checks.hcl import load_infra
from tools.infra_checks.identities import (
    IDENTITIES_PATH,
    ServiceIdentity,
    check_identities,
    check_identity_wiring,
    load_identities,
)
from tools.infra_checks.literals import check_literals
from tools.infra_checks.policy import check_eval_truth, check_module_structure, check_prod_like

TOOL_NAME = "infra_checks"


def _identities_or_none(repo_root: Path) -> tuple[ServiceIdentity, ...]:
    try:
        return load_identities(repo_root)
    except ConfigError:
        return ()  # check_identities reports the unusable file


def _declares_topology(root: Path) -> bool:
    """True once the tree declares environments or identities, so the policy applies to it."""
    return (root / ENV_PARENT).exists() or (root / IDENTITIES_PATH).exists()


def run_checks(repo_root: Path) -> tuple[Finding, ...]:
    """Run every infra check against ``repo_root`` and return all findings.

    A tree that declares neither ``infra/envs`` nor ``infra/identities.yaml`` (a minimal
    skeleton) has no environment topology to judge. Once either exists, every rule applies, so
    deleting one file cannot switch the policy off.
    """
    root = repo_root.resolve()
    if not _declares_topology(root):
        return ()
    tree = load_infra(root)
    return (
        *tree.parse_findings,
        *check_module_structure(tree),
        *check_environments(tree),
        *check_identities(root),
        *check_identity_wiring(tree),
        *check_prod_like(tree),
        *check_eval_truth(tree, _identities_or_none(root)),
        *check_literals(root, tree),
    )


def run_rules(repo_root: Path, rules: str) -> tuple[Finding, ...]:
    if rules == "all":
        core = run_checks(repo_root)
        budget = (
            check_budgets(repo_root, load_infra(repo_root)) if _declares_topology(repo_root) else ()
        )
        return core + budget
    elif rules == "budget":
        return (
            check_budgets(repo_root, load_infra(repo_root)) if _declares_topology(repo_root) else ()
        )
    elif rules == "core":
        return run_checks(repo_root)
    else:
        raise ValueError(f"unknown ruleset: {rules}")


def main(argv: Sequence[str]) -> int:
    rules = "core"
    clean_argv = []
    i = 0
    while i < len(argv):
        if argv[i] == "--rules":
            if i + 1 >= len(argv):
                import sys

                print("tools.infra_checks: error: --rules requires a value", file=sys.stderr)
                return 2
            rules = argv[i + 1]
            i += 2
        else:
            clean_argv.append(argv[i])
            i += 1

    if rules not in ("core", "budget", "all"):
        import sys

        print(f"tools.infra_checks: error: unknown ruleset {rules}", file=sys.stderr)
        return 2

    def _tool(args: argparse.Namespace) -> Sequence[Finding]:
        return run_rules(args.repo_root, rules)

    tool_name = "infra_checks_budget" if rules == "budget" else TOOL_NAME
    return run_tool(tool_name, _tool, clean_argv)
