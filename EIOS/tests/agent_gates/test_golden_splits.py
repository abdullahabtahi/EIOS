"""The golden cases keep a held-out set apart from the one we tune against (spec 022; eval skill: hold cases back)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from eios.agent_gates.capabilities import default_map
from eios.agent_gates.cases import GoldenCase, Split, load_golden_cases
from evals.agent.baseline import DEFAULT_SPLITS, parse_splits, select_splits

GOLDEN = Path(__file__).resolve().parents[2] / "evals" / "golden" / "agent_cases"
# Fixture-only or computed-only capabilities no operator question maps to; a case for them would test a stub.
NO_CASE_BY_DESIGN = {"calc.compare", "knowledge.sar_precedent"}


@pytest.fixture(scope="module")
def cases() -> list[GoldenCase]:
    return load_golden_cases(GOLDEN)


def _words(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def test_a_run_tunes_against_dev_and_validation_and_never_touches_sealed_by_default(
    cases: list[GoldenCase],
) -> None:
    assert DEFAULT_SPLITS == (Split.DEV, Split.VALIDATION)
    picked = select_splits(cases, DEFAULT_SPLITS)
    assert picked and all(c.split in DEFAULT_SPLITS for c in picked)
    assert not [c for c in picked if c.split is Split.SEALED]


def test_the_sealed_split_runs_only_when_named() -> None:
    assert parse_splits(None) == DEFAULT_SPLITS
    assert parse_splits("sealed") == (Split.SEALED,)
    assert parse_splits("dev, validation ,sealed") == (Split.DEV, Split.VALIDATION, Split.SEALED)
    with pytest.raises(ValueError, match="holdout"):
        parse_splits("holdout")


def test_each_split_has_cases_so_a_held_out_run_is_never_empty(cases: list[GoldenCase]) -> None:
    for split in Split:
        assert [c for c in cases if c.split is split], f"no {split.value} cases"


def test_held_out_cases_are_not_dev_questions_reworded_only_by_case(
    cases: list[GoldenCase],
) -> None:
    dev = {_words(t.user_query) for c in cases if c.split is Split.DEV for t in c.turns}
    held = {_words(t.user_query) for c in cases if c.split is not Split.DEV for t in c.turns}
    assert not dev & held


def test_scenario_ids_are_unique(cases: list[GoldenCase]) -> None:
    ids = [c.scenario_id for c in cases]
    assert len(ids) == len(set(ids))


def test_every_reachable_capability_has_a_case_so_none_is_unmeasured(
    cases: list[GoldenCase],
) -> None:
    named = {e.capability for c in cases for t in c.turns for e in t.expected_capabilities}
    reachable = {
        cap_id
        for cap_id, cap in default_map().capabilities.items()
        if not getattr(cap, "planned", None)
    }
    assert reachable - named - NO_CASE_BY_DESIGN == set()
