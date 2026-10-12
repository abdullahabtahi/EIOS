from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from tools.common.findings import Finding
from tools.label_check.citations import Citations
from tools.label_check.rules import LabelRules
from tools.label_check.scanner import scan_text

Scan = Callable[[str], tuple[Finding, ...]]


def test_known_record_passes(scan: Scan) -> None:
    assert scan("The pilot covers 40 partners [SPIKE] pending S-01.\n") == ()


def test_missing_spike_id_is_flagged(scan: Scan) -> None:
    (finding,) = scan("The pilot covers 40 partners [SPIKE].\n")
    assert (finding.rule_id, "no spike id" in finding.message) == ("label.spike-reference", True)


def test_malformed_id_is_flagged(scan: Scan) -> None:
    (finding,) = scan("The pilot covers 40 partners [SPIKE] see S-9.\n")
    assert finding.rule_id == "label.spike-reference"


def test_unknown_record_is_flagged(scan: Scan) -> None:
    (finding,) = scan("The pilot covers 40 partners [SPIKE] see S-42.\n")
    assert "no spike record" in finding.message


def test_index_only_spike_counts_as_open(rules: LabelRules, repo: Path) -> None:
    citations = Citations(repo, rules)
    assert scan_text("d.md", "40 partners [SPIKE] see S-03.\n", rules, citations) == ()
    assert citations.spike_states == {"S-03": "open"}


def test_report_states_open_or_closed_from_the_record(rules: LabelRules, repo: Path) -> None:
    citations = Citations(repo, rules)
    scan_text("d.md", "40 partners [SPIKE] see S-01 and S-02.\n", rules, citations)
    assert citations.spike_states == {"S-01": "open", "S-02": "closed"}
