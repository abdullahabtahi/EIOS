"""Run every cost_check rule over a repository root."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from eios.common.errors import ConfigError
from tools.common.findings import Finding
from tools.cost_check.config import COST_MODEL_PATH, load_linkage
from tools.cost_check.linkage import check_linkage
from tools.cost_check.model import read_cost_model
from tools.cost_check.rules import check_rows
from tools.cost_check.totals import Totals, compute_totals


@dataclass(frozen=True, slots=True)
class CostResult:
    """``warnings`` never affect the exit code; ``totals`` is ``None`` when the header is broken."""

    findings: tuple[Finding, ...]
    warnings: tuple[Finding, ...]
    totals: Totals | None


def check_repo(repo_root: Path, today: date) -> CostResult:
    """Check ``docs/cost_model.csv`` and its gateway linkage. ``today`` is injected."""
    config = load_linkage(repo_root)
    path = repo_root / COST_MODEL_PATH
    if not path.is_file():
        raise ConfigError(COST_MODEL_PATH, "$", "cost model file not found")
    rows, structural = read_cost_model(path, COST_MODEL_PATH)
    if structural and not rows:
        return CostResult(structural, (), None)
    rule_result = check_rows(rows, COST_MODEL_PATH, today, config.staleness_threshold_days)
    linkage = check_linkage(repo_root, config, rows)
    findings = (*structural, *rule_result.findings, *linkage)
    return CostResult(findings, rule_result.warnings, compute_totals(rows))
