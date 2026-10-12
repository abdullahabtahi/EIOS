"""T027 (FR-012): quarantine entries need an owner and an expiry; they are always visible."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest
import yaml

from eios.common.errors import ConfigError
from tests.support.clock import FixedClock
from tests.support.repo_builder import build_repo
from tools.gates.gate_config import GateSpec
from tools.gates.quarantine import QuarantineEntry, load_quarantine, partition
from tools.gates.run_record import Outcome, RunState
from tools.gates.runner import RunOutcome, RunSettings, format_summary, run_gates

REPO = Path(__file__).resolve().parents[4]
SHA = "sha256:" + "d" * 64
TODAY = date(2026, 1, 1)  # FixedClock default instant is 2026-01-01T12:00Z


def _entry(**overrides: Any) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "gate_id": "beta",
        "owner": "team-data",
        "expires": "2026-02-01",
        "reason": "flaky upstream advisory feed",
    }
    entry.update(overrides)
    return entry


def _file(tmp_path: Path, entries: object) -> Path:
    text = entries if isinstance(entries, str) else yaml.safe_dump(entries)
    return build_repo(tmp_path, {"config/quarantine.yaml": text}) / "config" / "quarantine.yaml"


def _gate(gate_id: str, code: str) -> GateSpec:
    return GateSpec(
        id=gate_id,
        blocking=True,
        stage="pr",
        threshold=None,
        proof_fixture=f"tests/fixtures/faulty_changes/{gate_id}",
        command=(("python", "-c", code),),
    )


def _run(repo: Path, entries: tuple[QuarantineEntry, ...], gates: list[GateSpec]) -> RunOutcome:
    settings = RunSettings(repo_root=repo, tool_root=REPO, commit_ref=SHA, clock=FixedClock())
    return run_gates(gates, settings, quarantine=entries)


def _marker(name: str) -> str:
    return f"open('{name}', 'w').write('ran')"


# --- loading ------------------------------------------------------------------------------


def test_the_shipped_quarantine_is_an_empty_list() -> None:
    path = REPO / "config" / "quarantine.yaml"
    assert load_quarantine(path) == ()


@pytest.mark.parametrize("text", ["[]\n", "# nothing quarantined\n"])
def test_an_empty_quarantine_loads_as_no_entries(tmp_path: Path, text: str) -> None:
    assert load_quarantine(_file(tmp_path, text)) == ()


def test_a_valid_entry_loads_as_a_frozen_model(tmp_path: Path) -> None:
    (entry,) = load_quarantine(_file(tmp_path, [_entry()]))
    assert entry == QuarantineEntry(
        gate_id="beta",
        owner="team-data",
        expires=date(2026, 2, 1),
        reason="flaky upstream advisory feed",
    )
    with pytest.raises(Exception, match="frozen"):
        entry.owner = "someone"


def test_native_yaml_dates_are_accepted(tmp_path: Path) -> None:
    (entry,) = load_quarantine(
        _file(tmp_path, "- {gate_id: beta, owner: o, expires: 2026-02-01, reason: r}\n")
    )
    assert entry.expires == date(2026, 2, 1)


@pytest.mark.parametrize("missing", ["gate_id", "owner", "expires", "reason"])
def test_every_field_is_required(tmp_path: Path, missing: str) -> None:
    entry = _entry()
    del entry[missing]
    with pytest.raises(ConfigError):
        load_quarantine(_file(tmp_path, [entry]))


@pytest.mark.parametrize(
    "overrides",
    [
        {"owner": ""},
        {"owner": "   "},
        {"reason": ""},
        {"reason": "  "},
        {"expires": "soon"},
        {"expires": "2026-13-45"},
        {"expires": ""},
        {"expires": "2026-02-01T10:00:00"},
        {"gate_id": ""},
        {"extra": "x"},
    ],
)
def test_invalid_entries_are_rejected(tmp_path: Path, overrides: dict[str, Any]) -> None:
    with pytest.raises(ConfigError):
        load_quarantine(_file(tmp_path, [_entry(**overrides)]))


def test_duplicate_gate_entries_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="beta"):
        load_quarantine(_file(tmp_path, [_entry(), _entry(owner="other")]))


def test_unknown_gate_ids_are_rejected_when_known_ids_are_given(tmp_path: Path) -> None:
    path = _file(tmp_path, [_entry(gate_id="nope")])
    with pytest.raises(ConfigError, match="nope"):
        load_quarantine(path, known_gate_ids=frozenset({"alpha", "beta"}))
    assert load_quarantine(path)  # without known ids the file alone is valid


def test_a_non_list_or_missing_file_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        load_quarantine(_file(tmp_path, "gate_id: beta\n"))
    with pytest.raises(ConfigError):
        load_quarantine(tmp_path / "missing.yaml")


def test_errors_name_the_file_and_entry_path(tmp_path: Path) -> None:
    with pytest.raises(ConfigError) as excinfo:
        load_quarantine(_file(tmp_path, [_entry(), _entry(gate_id="gamma", owner="")]))
    assert excinfo.value.file.endswith("quarantine.yaml")
    assert "[1]" in excinfo.value.path


# --- expiry -------------------------------------------------------------------------------


def test_partition_splits_active_from_expired_and_the_expiry_day_is_still_active() -> None:
    day = QuarantineEntry(gate_id="a", owner="o", expires=TODAY, reason="r")
    past = QuarantineEntry(gate_id="b", owner="o", expires=date(2025, 12, 31), reason="r")
    future = QuarantineEntry(gate_id="c", owner="o", expires=date(2026, 6, 1), reason="r")
    active, expired = partition((day, past, future), TODAY)
    assert active == (day, future)
    assert expired == (past,)


# --- runner integration -------------------------------------------------------------------


def test_a_quarantined_gate_is_skipped_with_a_reason_citing_the_quarantine(tmp_path: Path) -> None:
    repo = build_repo(tmp_path, {})
    gates = [_gate("alpha", _marker("alpha.txt")), _gate("beta", _marker("beta.txt"))]
    entry = QuarantineEntry(
        gate_id="beta", owner="team-data", expires=date(2026, 2, 1), reason="flaky feed"
    )
    outcome = _run(repo, (entry,), gates)
    assert (repo / "alpha.txt").exists()
    assert not (repo / "beta.txt").exists()
    by_id = {r.gate_id: r for r in outcome.record.gate_results}
    skipped = by_id["beta"]
    assert skipped.outcome is Outcome.SKIPPED_WITH_REASON
    assert skipped.reason is not None
    for fragment in ("quarantine", "team-data", "2026-02-01", "flaky feed"):
        assert fragment in skipped.reason
    assert outcome.record.state is RunState.PASSED
    assert outcome.exit_code == 0


def test_the_quarantined_count_is_on_the_outcome_the_record_reason_and_the_summary(
    tmp_path: Path,
) -> None:
    repo = build_repo(tmp_path, {})
    gates = [_gate("alpha", "pass"), _gate("beta", "pass"), _gate("gamma", "pass")]
    entries = (
        QuarantineEntry(gate_id="beta", owner="o", expires=date(2026, 2, 1), reason="r1"),
        QuarantineEntry(gate_id="gamma", owner="o", expires=date(2026, 2, 1), reason="r2"),
    )
    outcome = _run(repo, entries, gates)
    assert outcome.quarantined_count == 2
    reasons = [
        r.reason for r in outcome.record.gate_results if r.outcome is Outcome.SKIPPED_WITH_REASON
    ]
    assert len(reasons) == 2
    assert all(r is not None and "2 quarantined" in r for r in reasons)
    assert any("quarantined gates: 2" in line for line in format_summary(outcome))


def test_the_count_is_printed_even_when_nothing_is_quarantined(tmp_path: Path) -> None:
    outcome = _run(build_repo(tmp_path, {}), (), [_gate("alpha", "pass")])
    assert outcome.quarantined_count == 0
    assert any("quarantined gates: 0" in line for line in format_summary(outcome))


def test_an_expired_entry_fails_the_run_even_when_the_gate_passes(tmp_path: Path) -> None:
    repo = build_repo(tmp_path, {})
    entry = QuarantineEntry(
        gate_id="beta", owner="team-data", expires=date(2025, 12, 31), reason="old"
    )
    outcome = _run(repo, (entry,), [_gate("alpha", "pass"), _gate("beta", "pass")])
    assert outcome.record.state is RunState.FAILED
    assert outcome.exit_code == 1
    by_id = {r.gate_id: r for r in outcome.record.gate_results}
    assert by_id["beta"].outcome is Outcome.PASS  # the gate really ran
    expired = by_id["quarantine_expired:beta"]
    assert expired.outcome is Outcome.FAIL
    assert expired.reason is not None
    assert "team-data" in expired.reason
    assert "2025-12-31" in expired.reason
    assert outcome.quarantined_count == 0


def test_an_expired_entry_for_a_gate_outside_this_run_is_ignored(tmp_path: Path) -> None:
    entry = QuarantineEntry(gate_id="elsewhere", owner="o", expires=date(2020, 1, 1), reason="r")
    outcome = _run(build_repo(tmp_path, {}), (entry,), [_gate("alpha", "pass")])
    assert outcome.record.state is RunState.PASSED


def test_expiry_uses_the_clock_not_the_wall_time(tmp_path: Path) -> None:
    entry = QuarantineEntry(gate_id="alpha", owner="o", expires=date(2026, 1, 1), reason="r")
    repo = build_repo(tmp_path, {})
    on_day = RunSettings(repo_root=repo, tool_root=REPO, commit_ref=SHA, clock=FixedClock())
    assert run_gates([_gate("alpha", "pass")], on_day, quarantine=(entry,)).exit_code == 0
    later = FixedClock(datetime(2026, 1, 2, 0, 0, tzinfo=UTC))
    after = RunSettings(repo_root=repo, tool_root=REPO, commit_ref=SHA, clock=later)
    assert run_gates([_gate("alpha", "pass")], after, quarantine=(entry,)).exit_code == 1
