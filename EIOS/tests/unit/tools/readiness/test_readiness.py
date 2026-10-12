"""Readiness engine (FR-033, SC-008): blocked on each dependency kind, ready when all met."""

from __future__ import annotations

from pathlib import Path

import pytest

from eios.common.errors import ConfigError
from tests.support.readiness_repo import (
    DEPENDENCIES_RELATIVE,
    ReadinessScenario,
    dependencies_text,
    readiness_tree,
)
from tests.support.repo_builder import build_repo
from tools.readiness.engine import check_readiness

_BLOCKED = ReadinessScenario(
    depends_on_features=("F01",),
    depends_on_spikes=("S-02",),
    depends_on_adrs=("ADR-003",),
    spike_states={"S-02": "open"},
    adr_statuses={"ADR-003": "Proposed"},
    complete_features=(),
)
_READY = ReadinessScenario(
    depends_on_features=("F01",),
    depends_on_spikes=("S-02",),
    depends_on_adrs=("ADR-003",),
    spike_states={"S-02": "closed"},
    adr_statuses={"ADR-003": "Accepted"},
    complete_features=("F01",),
)


def _rules(tmp_path: Path, scenario: ReadinessScenario) -> dict[str, str]:
    root = build_repo(tmp_path, readiness_tree(scenario))
    return {f.rule_id: f.message for f in check_readiness(root, scenario.feature).findings}


def test_ready_when_everything_met(tmp_path: Path) -> None:
    root = build_repo(tmp_path, readiness_tree(_READY))
    result = check_readiness(root, "F03")
    assert result.findings == ()
    assert result.ready


def test_blocked_lists_each_unmet_dependency_with_state(tmp_path: Path) -> None:
    rules = _rules(tmp_path, _BLOCKED)
    assert set(rules) == {
        "readiness.spike_open",
        "readiness.adr_not_accepted",
        "readiness.feature_incomplete",
    }
    assert "S-02" in rules["readiness.spike_open"] and "open" in rules["readiness.spike_open"]
    assert "ADR-003" in rules["readiness.adr_not_accepted"]
    assert "Proposed" in rules["readiness.adr_not_accepted"]
    assert "F01" in rules["readiness.feature_incomplete"]


@pytest.mark.parametrize(
    ("override", "expected"),
    [
        ({"spike_states": {"S-02": "open"}}, {"readiness.spike_open"}),
        ({"adr_statuses": {"ADR-003": "Open"}}, {"readiness.adr_not_accepted"}),
        ({"complete_features": ()}, {"readiness.feature_incomplete"}),
    ],
)
def test_blocked_on_exactly_one_kind(
    tmp_path: Path, override: dict[str, object], expected: set[str]
) -> None:
    values = {**vars(_READY), **override}
    assert set(_rules(tmp_path, ReadinessScenario(**values))) == expected


def test_closing_spike_and_accepting_adr_flips_to_ready(tmp_path: Path) -> None:
    root = build_repo(tmp_path, readiness_tree(_BLOCKED))
    assert not check_readiness(root, "F03").ready
    flipped = ReadinessScenario(
        **{**vars(_BLOCKED), **vars(_READY)},
    )
    build_repo(tmp_path, readiness_tree(flipped))
    assert check_readiness(root, "F03").ready


def test_spike_without_record_file_is_open_via_index(tmp_path: Path) -> None:
    scenario = ReadinessScenario(depends_on_spikes=("S-04",), index_only_spikes=("S-04",))
    rules = _rules(tmp_path, scenario)
    assert "open" in rules["readiness.spike_open"]


def test_unknown_dependencies_are_blocked_as_not_found(tmp_path: Path) -> None:
    scenario = ReadinessScenario(depends_on_spikes=("S-07",), depends_on_adrs=("ADR-008",))
    rules = _rules(tmp_path, scenario)
    assert len(rules) == 2
    assert all("not found" in message for message in rules.values())


def test_unknown_feature_in_register_is_not_found(tmp_path: Path) -> None:
    files = readiness_tree(ReadinessScenario(depends_on_features=("F01",)))
    files["docs/feature_register.yaml"] = "features:\n  - {id: F00, name: x, complete: true}\n"
    root = build_repo(tmp_path, files)
    findings = check_readiness(root, "F03").findings
    assert [f.rule_id for f in findings] == ["readiness.feature_incomplete"]
    assert "not found" in findings[0].message


def test_no_declaration_is_a_config_error_naming_the_feature(tmp_path: Path) -> None:
    root = build_repo(tmp_path, readiness_tree(_READY))
    with pytest.raises(ConfigError, match="F07"):
        check_readiness(root, "F07")


def test_schema_violating_declaration_is_a_config_error(tmp_path: Path) -> None:
    files = readiness_tree(_READY)
    files[DEPENDENCIES_RELATIVE] = "feature: F03\ndepends_on_spikes: [spike-two]\n"
    root = build_repo(tmp_path, files)
    with pytest.raises(ConfigError):
        check_readiness(root, "F03")


def test_duplicate_declarations_are_a_config_error(tmp_path: Path) -> None:
    files = readiness_tree(_READY)
    files["specs/other/dependencies.yaml"] = dependencies_text("F03", [], [], [])
    root = build_repo(tmp_path, files)
    with pytest.raises(ConfigError, match="F03"):
        check_readiness(root, "F03")


def test_specs_beside_the_repo_root_are_found(tmp_path: Path) -> None:
    files = readiness_tree(_BLOCKED)
    declaration = files.pop(DEPENDENCIES_RELATIVE)
    build_repo(tmp_path / "ws", {DEPENDENCIES_RELATIVE: declaration})
    root = build_repo(tmp_path / "ws" / "FEIOS", files)
    assert not check_readiness(root, "F03").ready


def test_missing_register_is_a_config_error(tmp_path: Path) -> None:
    files = readiness_tree(_READY)
    del files["docs/feature_register.yaml"]
    root = build_repo(tmp_path, files)
    with pytest.raises(ConfigError):
        check_readiness(root, "F03")


def test_malformed_register_is_a_config_error(tmp_path: Path) -> None:
    files = readiness_tree(_READY)
    files["docs/feature_register.yaml"] = "features:\n  - {id: F00, complete: yes-please}\n"
    root = build_repo(tmp_path, files)
    with pytest.raises(ConfigError):
        check_readiness(root, "F03")
