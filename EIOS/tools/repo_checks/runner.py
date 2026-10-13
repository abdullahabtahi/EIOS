"""Aggregator: run every enabled repo check and return the combined findings."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from tools.common.cli import run_tool
from tools.common.findings import Finding
from tools.common.yaml_io import load_validated
from tools.repo_checks.file_size import DEFAULT_CEILING, check_file_size
from tools.repo_checks.forbidden_artifacts import check_forbidden_artifacts
from tools.repo_checks.forbidden_literals import check_forbidden_literals
from tools.repo_checks.frozen_models import check_frozen_models
from tools.repo_checks.pinned_deps import check_pinned_deps
from tools.repo_checks.service_docs import check_service_docs

TOOL_NAME = "repo_checks"
SERVICE_DOCS_COMMAND = "service-docs"  # `python -m tools.repo_checks service-docs`
SERVICE_DOCS_TOOL = "service_docs"  # its report is evals/reports/service_docs.json
CONFIG_PATH = "config/repo_checks.yaml"
CHECK_NAMES = (
    "file_size",
    "forbidden_artifacts",
    "forbidden_literals",
    "frozen_models",
    "pinned_deps",
)

_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "checks": {
            "type": "object",
            "additionalProperties": False,
            "properties": {name: {"type": "boolean"} for name in CHECK_NAMES},
        },
        "file_size": {
            "type": "object",
            "additionalProperties": False,
            "properties": {"ceiling": {"type": "integer", "minimum": 1}},
        },
        "exclude": {"type": "array", "items": {"type": "string", "minLength": 1}},
    },
}


@dataclass(frozen=True, slots=True)
class RepoChecksConfig:
    enabled: frozenset[str]
    ceiling: int
    exclude: tuple[str, ...]


def _defaults() -> RepoChecksConfig:
    return RepoChecksConfig(frozenset(CHECK_NAMES), DEFAULT_CEILING, ())


def load_config(repo_root: Path) -> RepoChecksConfig:
    """Read ``config/repo_checks.yaml``; a missing file means built-in defaults."""
    path = repo_root.resolve() / CONFIG_PATH
    if not path.is_file():
        return _defaults()
    data = load_validated(path, _SCHEMA)
    assert isinstance(data, dict)  # noqa: S101 - the schema guarantees an object
    checks = data.get("checks", {})
    enabled = frozenset(n for n in CHECK_NAMES if checks.get(n, True))
    ceiling = data.get("file_size", {}).get("ceiling", DEFAULT_CEILING)
    return RepoChecksConfig(enabled, ceiling, tuple(data.get("exclude", ())))


def _runners(config: RepoChecksConfig) -> dict[str, Callable[[Path], Sequence[Finding]]]:
    exclude = config.exclude
    return {
        "file_size": lambda r: check_file_size(r, ceiling=config.ceiling, exclude=exclude),
        "forbidden_artifacts": check_forbidden_artifacts,
        "forbidden_literals": lambda r: check_forbidden_literals(r, exclude=exclude),
        "frozen_models": lambda r: check_frozen_models(r, exclude=exclude),
        "pinned_deps": check_pinned_deps,
    }


def run_checks(repo_root: Path) -> tuple[Finding, ...]:
    """Run every enabled check against ``repo_root`` and return all findings."""
    config = load_config(repo_root)
    runners = _runners(config)
    findings: list[Finding] = []
    for name in CHECK_NAMES:
        if name in config.enabled:
            findings.extend(runners[name](repo_root))
    return tuple(findings)


def _tool(args: argparse.Namespace) -> Sequence[Finding]:
    return run_checks(args.repo_root)


def _service_docs_tool(args: argparse.Namespace) -> Sequence[Finding]:
    return check_service_docs(args.repo_root)


def main(argv: Sequence[str]) -> int:
    """Run the aggregate, or one standalone check named by a leading subcommand."""
    if argv and argv[0] == SERVICE_DOCS_COMMAND:
        return run_tool(SERVICE_DOCS_TOOL, _service_docs_tool, argv[1:])
    return run_tool(TOOL_NAME, _tool, argv)
