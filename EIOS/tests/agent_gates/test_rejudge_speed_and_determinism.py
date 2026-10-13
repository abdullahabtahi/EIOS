"""Re-judging a stored run is deterministic, offline and fast (T028; spec 022 SC-002, SC-003)."""

import socket
import time
from pathlib import Path

import pytest

from evals.agent.faithfulness_suite import fingerprint, judge_all, load_records

RECORDED = Path(__file__).resolve().parents[2] / "evals" / "recorded"
MAX_SECONDS = 120.0  # [ASSUMPTION] SC-003


def test_the_recorded_corpus_is_at_least_two_hundred_turns() -> None:
    assert len(load_records(RECORDED)) >= 200


def test_two_judgements_of_the_same_run_are_identical_and_offline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def no_network(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("the judge must not touch the network")

    monkeypatch.setattr(socket, "socket", no_network)
    records = load_records(RECORDED)
    assert fingerprint(judge_all(records)) == fingerprint(judge_all(records))


def test_the_recorded_corpus_is_judged_correctly_and_quickly() -> None:
    records = load_records(RECORDED)
    start = time.perf_counter()
    results = judge_all(records)
    elapsed = time.perf_counter() - start
    wrong = [r["record_id"] for r in results if not r["ok"]]
    assert not wrong, wrong[:10]
    assert elapsed < MAX_SECONDS
