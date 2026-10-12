"""The open-decision engine: scan the repository against every still-open decision's rules.

A decision's rules apply to every scanned file outside its ``allowed_paths`` unless the decision
is lifted. A decision is lifted only when ``config/open_decisions.yaml`` says so AND the ADR
index in ``docs/spikes_and_adrs.md`` shows the status the config names (``Accepted``). Nothing
about any one decision is written in this tool.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from pathlib import Path

from eios.common.errors import ConfigError
from tools.common.cli import run_tool
from tools.common.findings import Finding
from tools.open_decision_check.config import (
    CONFIG_PATH,
    Decision,
    OpenDecisionsConfig,
    load_config,
)
from tools.open_decision_check.report import (
    DecisionState,
    decision_states,
    report_extra,
    state_line,
)
from tools.open_decision_check.rules import CompiledRule, SourceFile, build_rule
from tools.open_decision_check.scan import read_files, select
from tools.records.index import DEFAULT_SOURCE, parse_adr_index
from tools.repo_checks._walk import is_under

TOOL_NAME = "open_decision_check"
RULE_PREFIX = "open_decision"
LIFT_RULE = "lift_without_acceptance"


def adr_status(repo_root: Path, adr: str) -> str:
    """The status the ADR index shows for ``adr``; ``ConfigError`` if unreadable or absent."""
    path = repo_root / DEFAULT_SOURCE
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ConfigError(DEFAULT_SOURCE, "ADR index", f"cannot read the ADR index: {exc}") from exc
    for row in parse_adr_index(text, DEFAULT_SOURCE):
        if row.adr_id == adr:
            return row.status
    raise ConfigError(DEFAULT_SOURCE, "ADR index", f"{adr} is not listed in the ADR index")


def _is_lifted(repo_root: Path, decision: Decision) -> tuple[bool, tuple[Finding, ...]]:
    """Whether ``decision`` is lifted, plus a finding when the config lifts it unsupported."""
    if not decision.lift.lifted:
        return False, ()
    status = adr_status(repo_root, decision.adr)
    if status == decision.lift.adr_status:
        return True, ()
    message = (
        f"{decision.adr} is marked lifted but the ADR index shows {status!r}, "
        f"not {decision.lift.adr_status!r}; the rules stay enforced"
    )
    rule = f"{RULE_PREFIX}.{decision.adr}.{LIFT_RULE}"
    return False, (Finding(CONFIG_PATH, decision.line, rule, message),)


def _evaluate(
    decision: Decision,
    rules: Sequence[tuple[str, CompiledRule]],
    files: Sequence[SourceFile],
    config: OpenDecisionsConfig,
) -> list[Finding]:
    findings: list[Finding] = []
    for rule_id, rule in rules:
        rule_files = select(files, config.scan, rule)
        in_scope = [f for f in rule_files if not is_under(f.path, decision.allowed_paths)]
        name = f"{RULE_PREFIX}.{decision.adr}.{rule_id}"
        for hit in rule.check(in_scope):
            message = f"{hit.message} ({decision.adr} is still open)"
            findings.append(Finding(hit.file, hit.line, name, message))
    return findings


def _compile(decision: Decision) -> tuple[tuple[str, CompiledRule], ...]:
    return tuple((rule.rule_id, build_rule(rule)) for rule in decision.rules)


def check_config(repo_root: Path, config: OpenDecisionsConfig) -> tuple[Finding, ...]:
    """Apply every decision in ``config`` to the tree under ``repo_root``."""
    compiled = [(decision, _compile(decision)) for decision in config.decisions]
    every_rule = [rule for _, rules in compiled for _, rule in rules]
    files = read_files(repo_root, config.scan, every_rule)
    findings: list[Finding] = []
    for decision, rules in compiled:
        lifted, notes = _is_lifted(repo_root, decision)
        findings.extend(notes)
        if not lifted:
            findings.extend(_evaluate(decision, rules, files, config))
    return tuple(sorted(findings, key=lambda f: (f.file, f.line, f.rule_id, f.message)))


def run_checks(repo_root: Path) -> tuple[Finding, ...]:
    """Load the config under ``repo_root`` and return every open-decision finding."""
    root = repo_root.resolve()
    return check_config(root, load_config(root))


def main(argv: Sequence[str]) -> int:
    holder: list[tuple[OpenDecisionsConfig, tuple[DecisionState, ...]]] = []

    def tool(args: argparse.Namespace) -> Sequence[Finding]:
        root = args.repo_root.resolve()
        config = load_config(root)
        findings = check_config(root, config)
        states = decision_states(root, config)
        holder.append((config, states))
        for state in states:
            print(state_line(state))
        for path in config.scan.prototype_paths:
            print(f"excluded prototype path: {path}")
        return findings

    def extra() -> Mapping[str, object]:
        return report_extra(*holder[0])

    return run_tool(TOOL_NAME, tool, argv, report_extra=extra)
