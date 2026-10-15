"""History goes through the real pipeline into the warm tier, once, with its lineage and its breaches."""

from datetime import UTC, datetime
from typing import Any

import pytest
from google.api_core.exceptions import Conflict

from eios.foundry.scenarios.aml_world import AmlWorld
from eios.warm.loader import load_transactions_history
from eios.warm.sink import BigQueryWarmSink, LocalWarmSink

NOW = datetime(2026, 10, 15, tzinfo=UTC)


def _count(sink: LocalWarmSink, table: str) -> int:
    return sink.connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]  # noqa: S608


def test_the_world_history_lands_with_lineage_and_the_breaches_are_quarantined(
    small_world: AmlWorld,
) -> None:
    sink = LocalWarmSink()
    summary = load_transactions_history(small_world, None, sink, now=NOW)
    assert summary.loaded + summary.quarantined == summary.offered
    assert summary.loaded > 0
    assert _count(sink, "warm_aml.transactions_aml") == summary.loaded
    assert _count(sink, "warm_dlq.quarantined") == summary.quarantined
    row = sink.connection.execute(
        "SELECT _batch_id, _source, _tenant_id, _loaded_at = TIMESTAMPTZ '2026-10-15 00:00:00+00' "
        "FROM warm_aml.transactions_aml LIMIT 1"
    ).fetchone()
    assert row == (summary.batch_id, "foundry:aml-world", "DERIV_MFSA", True)


def test_a_history_load_plants_no_breaches_so_the_history_stays_exact(
    small_world: AmlWorld,
) -> None:
    sink = LocalWarmSink()
    summary = load_transactions_history(small_world, None, sink, now=NOW)
    assert summary.quarantined == 0 and summary.loaded == summary.offered


def test_the_history_spans_far_more_than_the_hot_window(small_world: AmlWorld) -> None:
    sink = LocalWarmSink()
    load_transactions_history(small_world, None, sink, now=NOW)
    days = sink.connection.execute(
        "SELECT count(DISTINCT CAST(timestamp AS DATE)) FROM warm_aml.transactions_aml"
    ).fetchone()[0]
    assert days >= 20  # a week of hot state could never answer this


def test_loading_the_same_history_twice_leaves_one_copy(small_world: AmlWorld) -> None:
    sink = LocalWarmSink()
    first = load_transactions_history(small_world, None, sink, now=NOW)
    again = load_transactions_history(small_world, None, sink, now=NOW)
    assert again.batch_id == first.batch_id
    assert (again.loaded, again.quarantined) == (0, 0)
    assert _count(sink, "warm_aml.transactions_aml") == first.loaded


def test_a_quarantined_row_keeps_the_reason_and_a_hash_not_the_payload(
    small_world: AmlWorld,
) -> None:
    sink = LocalWarmSink()
    load_transactions_history(small_world, None, sink, now=NOW, plant_breaches=0.05)
    cols = {r[0] for r in sink.connection.execute("DESCRIBE warm_dlq.quarantined").fetchall()}
    assert "payload_sha256" in cols and "raw_payload_bytes" not in cols
    reason = sink.connection.execute(
        "SELECT breach_type, field_paths FROM warm_dlq.quarantined LIMIT 1"
    ).fetchone()
    assert reason is not None and reason[1]


class _FakeJob:
    def __init__(self, fail: Exception | None) -> None:
        self._fail = fail

    def result(self) -> None:
        if self._fail:
            raise self._fail


class _FakeClient:
    def __init__(self, fail: Exception | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self._fail = fail

    def load_table_from_json(self, rows: Any, table: str, **kwargs: Any) -> _FakeJob:
        self.calls.append({"rows": rows, "table": table, **kwargs})
        return _FakeJob(self._fail)


def test_bigquery_gets_a_load_job_with_the_generated_schema_and_a_batch_derived_id(
    small_world: AmlWorld,
) -> None:
    client = _FakeClient()
    summary = load_transactions_history(
        small_world,
        None,
        BigQueryWarmSink("proj", client=client),
        now=NOW,
        plant_breaches=0.05,
    )
    call = next(c for c in client.calls if c["table"].endswith("warm_aml.transactions_aml"))
    assert call["table"] == "proj.warm_aml.transactions_aml"
    assert call["job_id"] == f"load_transactions_aml_{summary.batch_id}"
    assert {f.name for f in call["job_config"].schema} >= {
        "txn_id",
        "timestamp",
        "_batch_id",
        "_loaded_at",
    }
    assert call["job_config"].write_disposition == "WRITE_APPEND"
    assert any(c["table"].endswith("warm_dlq.quarantined") for c in client.calls)


def test_a_repeated_load_job_id_means_the_batch_is_already_there(small_world: AmlWorld) -> None:
    sink = BigQueryWarmSink("proj", client=_FakeClient(Conflict("Already Exists: Job")))
    summary = load_transactions_history(small_world, None, sink, now=NOW)
    assert (summary.loaded, summary.quarantined) == (0, 0)


def test_any_other_load_failure_is_not_swallowed(small_world: AmlWorld) -> None:
    sink = BigQueryWarmSink("proj", client=_FakeClient(RuntimeError("quota")))
    with pytest.raises(RuntimeError):
        load_transactions_history(small_world, None, sink, now=NOW)
