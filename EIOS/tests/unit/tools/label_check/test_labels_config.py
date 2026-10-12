from __future__ import annotations

from pathlib import Path

import pytest

from eios.common.errors import ConfigError
from eios.common.provenance import Tag
from tests.support.repo_builder import build_repo
from tools.label_check.rules import LabelRules, load_rules

REPO_ROOT = Path(__file__).resolve().parents[4]
REAL = REPO_ROOT / "config" / "labels.yaml"


def test_tag_set_equals_the_tag_enum(rules: LabelRules) -> None:
    assert set(rules.evidence) == {t.value for t in Tag}


def test_evidence_rule_per_tag(rules: LabelRules) -> None:
    assert rules.evidence == {
        "[BRIEF]": "brief_citation",
        "[ASSUMPTION]": "owner_and_verify_by",
        "[ILLUSTRATIVE]": "none",
        "[TARGET]": "metric_and_report",
        "[SPIKE]": "spike_id",
    }


def test_claim_scope_and_prototype_exclusions(rules: LabelRules) -> None:
    assert set(rules.claim_scope) == {"sentence", "table_row", "list_item"}
    assert {"FEIOS/", "DESIGN.MD", "DESIGN_PLAN.md"} <= set(rules.prototype_excluded)


def _mutated(tmp_path: Path, old: str, new: str) -> Path:
    text = REAL.read_text(encoding="utf-8")
    assert old in text
    build_repo(tmp_path, {"labels.yaml": text.replace(old, new, 1)})
    return tmp_path / "labels.yaml"


def test_extra_tag_fails_to_load(tmp_path: Path) -> None:
    path = _mutated(tmp_path, "tags:\n", "tags:\n  '[EXTRA]': {evidence: none, description: x}\n")
    with pytest.raises(ConfigError, match="EXTRA"):
        load_rules(path)


def test_missing_tag_fails_to_load(tmp_path: Path) -> None:
    text = REAL.read_text(encoding="utf-8").replace("'[BRIEF]'", "'[BRIEFX]'", 1)
    build_repo(tmp_path, {"labels.yaml": text})
    with pytest.raises(ConfigError, match="BRIEF"):
        load_rules(tmp_path / "labels.yaml")


def test_unknown_evidence_kind_fails_to_load(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        load_rules(_mutated(tmp_path, "evidence: spike_id", "evidence: vibes"))


def test_bad_claim_scope_fails_to_load(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="claim_scope"):
        load_rules(_mutated(tmp_path, "- sentence", "- paragraph"))


def test_invalid_non_claim_regex_fails_to_load(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="non_claim_patterns"):
        load_rules(_mutated(tmp_path, "non_claim_patterns:\n", "non_claim_patterns:\n  - '('\n"))


def test_missing_file_is_a_config_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        load_rules(tmp_path / "absent.yaml")
