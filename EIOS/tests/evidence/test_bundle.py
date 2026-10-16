"""Sealing a decision turn: the id is the hash of the content, so any change after sealing is seen."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from eios.evidence.bundle import (
    MAX_BYTES,
    REF_PREFIX,
    BundleTooLarge,
    intact,
    is_decision,
    ref,
    seal,
)
from eios.evidence.store import EvidenceStore, Tampered
from eios.ontology.actions.record_store import InMemoryRecordStore

WHEN = datetime(2026, 10, 16, 9, 0, tzinfo=UTC)


def _bundle(**overrides: Any) -> dict[str, Any]:
    parts: dict[str, Any] = {
        "workstation": "geospatial",
        "operator_id": "alice",
        "question": "Put a hold on CR84920.",
        "answer": {"text": "A hold is proposed.", "figures": []},
        "calls": [
            {"name": "propose_hold", "arguments": {"entity_id": "CR84920"}, "result": {"x": 1}}
        ],
        "model_key": "fast",
        "sealed_at": WHEN,
    }
    return seal(**{**parts, **overrides})


def test_the_same_content_seals_to_the_same_id_and_any_change_to_another() -> None:
    assert _bundle()["bundle_id"] == _bundle()["bundle_id"]
    assert _bundle()["bundle_id"] != _bundle(question="Put a hold on CR84921.")["bundle_id"]
    assert len(_bundle()["bundle_id"]) == 64


def test_a_byte_changed_after_sealing_breaks_the_seal() -> None:
    bundle = _bundle()
    assert intact(bundle)
    tampered = {**bundle, "calls": [{**bundle["calls"][0], "result": {"x": 2}}]}
    assert not intact(tampered)


def test_only_a_proposal_or_a_sar_draft_is_a_decision_turn() -> None:
    assert is_decision(["get_geo_account", "propose_hold"])
    assert is_decision(["draft_sar"])
    assert not is_decision(["get_geo_account", "get_shared_exit"])


def test_evidence_too_large_for_one_record_is_refused_not_truncated() -> None:
    huge = [{"name": "get_geo_overview", "arguments": {}, "result": {"blob": "x" * MAX_BYTES}}]
    with pytest.raises(BundleTooLarge):
        _bundle(calls=huge)


def test_the_intent_names_the_bundle_by_its_hash() -> None:
    bundle_id = _bundle()["bundle_id"]
    assert ref(bundle_id) == f"{REF_PREFIX}{bundle_id}"


def test_the_store_keeps_a_bundle_once_and_refuses_one_that_no_longer_matches() -> None:
    records = InMemoryRecordStore()
    store = EvidenceStore(records)
    bundle = _bundle()
    bundle_id = store.put(bundle)
    assert store.put(bundle) == bundle_id  # the same content is the same bundle
    assert store.get(bundle_id) == bundle
    assert store.get("not-a-bundle-id") is None and store.get("0" * 64) is None
    records.put(bundle_id, {**bundle, "question": "something else"})
    with pytest.raises(Tampered):
        store.get(bundle_id)


def test_the_store_refuses_a_bundle_that_was_not_sealed() -> None:
    with pytest.raises(ValueError, match="only as sealed"):
        EvidenceStore(InMemoryRecordStore()).put({**_bundle(), "question": "edited"})
