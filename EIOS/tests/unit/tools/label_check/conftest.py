from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from tests.support.repo_builder import build_repo
from tools.common.findings import Finding
from tools.label_check.citations import Citations
from tools.label_check.rules import LabelRules, load_rules

REPO_ROOT = Path(__file__).resolve().parents[4]

_BRIEF = {"docs/brief/data.md": "# Data brief\n\n## 3 Section\n"}
_SPIKES = {
    "docs/adr/S-01-cost.md": "# S-01: Cost\n\n**State:** Open\n",
    "docs/adr/S-02-graph.md": "# S-02: Graph\n\n**State:** Closed\n",
    "docs/spikes_and_adrs.md": (
        "# Spikes and ADRs\n\n## Spikes\n\n"
        "| ID | Question | Why unverified | Method | Decision it unlocks | Fallback |\n"
        "|---|---|---|---|---|---|\n"
        "| S-03 | Q? | Why | Method | ADR-004 | Fallback |\n"
    ),
}


@pytest.fixture(scope="session")
def rules() -> LabelRules:
    return load_rules(REPO_ROOT / "config" / "labels.yaml")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    return build_repo(tmp_path, {**_BRIEF, **_SPIKES})


@pytest.fixture
def scan(rules: LabelRules, repo: Path) -> Callable[[str], tuple[Finding, ...]]:
    from tools.label_check.scanner import scan_text

    def run(text: str) -> tuple[Finding, ...]:
        return tuple(scan_text("doc.md", text, rules, Citations(repo, rules)))

    return run


def rule_ids(findings: tuple[Finding, ...]) -> list[str]:
    return sorted(f.rule_id for f in findings)
