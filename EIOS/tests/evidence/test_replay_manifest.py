"""A replay says whether the setup that produced an answer is still the setup: data equal is not the whole story."""

from eios.evidence.bundle import seal
from eios.evidence.replay import compare_manifests, replay

SEALED = {
    "schema": "eios.orchestration_manifest/v1",
    "workstation": "geospatial",
    "adk_version": "2.11.0",
    "model": {"key": "fast", "id": "m-1"},
    "instruction_sha256": "a" * 64,
    "toolset": {"count": 12, "sha256": "b" * 64},
    "assembly": {"max_attempts": 3, "plain_figures": True, "prefetch": True},
    "limits": {"turn_deadline_s": 30.0, "max_llm_calls": 20},
}


class _Port:
    def call(
        self, principal, tool, arguments
    ):  # pragma: no cover - a bundle with no calls never reaches it
        raise AssertionError


def _bundle(manifest):
    return seal(
        workstation="geospatial",
        operator_id="alice",
        question="q",
        answer={"text": "a"},
        calls=[],
        model_key="fast",
        manifest=manifest,
    )


def test_an_unchanged_setup_is_reported_unchanged() -> None:
    assert compare_manifests(SEALED, dict(SEALED)) == {"status": "unchanged", "changed": []}


def test_each_part_that_moved_is_named_by_its_path() -> None:
    now = {
        **SEALED,
        "model": {"key": "fast", "id": "m-2"},
        "instruction_sha256": "c" * 64,
        "limits": {"turn_deadline_s": 45.0, "max_llm_calls": 20},
    }
    found = compare_manifests(SEALED, now)
    assert found["status"] == "changed"
    assert found["changed"] == ["instruction_sha256", "limits.turn_deadline_s", "model.id"]


def test_a_bundle_sealed_before_manifests_cannot_be_compared() -> None:
    assert compare_manifests(None, SEALED) == {"status": "unrecorded", "changed": []}


def test_a_setup_that_cannot_be_rebuilt_now_is_not_called_unchanged() -> None:
    assert compare_manifests(SEALED, None) == {"status": "unavailable", "changed": []}


def test_the_replay_report_carries_the_comparison_and_equal_still_means_the_data() -> None:
    moved = {**SEALED, "toolset": {"count": 13, "sha256": "d" * 64}}
    report = replay(_bundle(SEALED), _Port(), object(), current_manifest=moved)  # type: ignore[arg-type]
    assert report["manifest"]["status"] == "changed"
    assert report["manifest"]["changed"] == ["toolset.count", "toolset.sha256"]
    assert "equal" in report
