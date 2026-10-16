"""Named queries only, with the partition filter and the byte cap enforced in code."""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from eios.foundry.scenarios.aml_world import AmlWorld
from eios.warm.loader import load_transactions_history
from eios.warm.queries import CATALOGUE
from eios.warm.sink import LocalWarmSink
from eios.warm.store import (
    BigQueryWarmStore,
    LocalWarmStore,
    WarmQueryRefused,
    WarmUnavailable,
)

NOW = datetime(2026, 10, 15, tzinfo=UTC)


@pytest.fixture
def loaded(small_world: AmlWorld) -> tuple[LocalWarmSink, str, datetime]:
    sink = LocalWarmSink()
    load_transactions_history(small_world, None, sink, now=NOW)
    client = sink.connection.execute(
        "SELECT client_id FROM warm_aml.transactions_aml GROUP BY client_id ORDER BY count(*) DESC LIMIT 1"
    ).fetchone()[0]
    return sink, client, small_world.config.as_of


@pytest.mark.parametrize("query", list(CATALOGUE.values()), ids=list(CATALOGUE))
def test_every_named_query_filters_on_its_partition_column(query) -> None:
    assert query.partition_column in query.sql.split("WHERE", 1)[1]


def test_daily_activity_comes_back_per_day_with_the_totals_the_data_holds(loaded) -> None:
    sink, client, as_of = loaded
    store = LocalWarmStore(sink.connection)
    result = store.run(
        "account_daily_activity",
        {
            "client_id": client,
            "start": (as_of - timedelta(days=40)).isoformat(),
            "end": as_of.isoformat(),
        },
    )
    assert result.rows and result.source == "warm.local:warm_aml.transactions_aml"
    days = [r["day"] for r in result.rows]
    assert days == sorted(days) and len(set(days)) == len(days)
    truth = sink.connection.execute(
        "SELECT sum(amount) FROM warm_aml.transactions_aml WHERE client_id = ? AND txn_type = 'DEPOSIT' AND status IN ('COMPLETED', 'PENDING')",
        [client],
    ).fetchone()[0]
    assert sum(r["deposits"] for r in result.rows) == pytest.approx(truth)


def test_a_window_with_no_activity_is_an_empty_answer_not_zeros(loaded) -> None:
    sink, client, as_of = loaded
    store = LocalWarmStore(sink.connection)
    result = store.run(
        "account_daily_activity",
        {
            "client_id": client,
            "start": (as_of + timedelta(days=5)).isoformat(),
            "end": (as_of + timedelta(days=9)).isoformat(),
        },
    )
    assert result.rows == []


def test_the_model_cannot_name_a_query_that_is_not_in_the_catalogue(loaded) -> None:
    sink, _, _ = loaded
    with pytest.raises(WarmQueryRefused):
        LocalWarmStore(sink.connection).run("SELECT * FROM warm_aml.transactions_aml", {})


def test_a_missing_parameter_is_refused_before_running(loaded) -> None:
    sink, client, _ = loaded
    with pytest.raises(WarmQueryRefused):
        LocalWarmStore(sink.connection).run("account_daily_activity", {"client_id": client})


class _Job:
    def __init__(self, bytes_processed: int, rows: list[dict[str, Any]]) -> None:
        self.total_bytes_processed = bytes_processed
        self.total_bytes_billed = bytes_processed
        self._rows = rows

    def result(self) -> list[Any]:
        class Row:
            def __init__(self, d: dict[str, Any]) -> None:
                self._d = d

            def items(self) -> Any:
                return self._d.items()

        return [Row(r) for r in self._rows]


class _Client:
    def __init__(
        self, estimate: int, rows: list[dict[str, Any]] | None = None, fail: Exception | None = None
    ) -> None:
        self.estimate, self.rows, self.fail, self.configs = estimate, rows or [], fail, []

    def query(self, sql: str, job_config: Any = None) -> _Job:
        self.configs.append((sql, job_config))
        if self.fail:
            raise self.fail
        return _Job(self.estimate, self.rows)


PARAMS = {
    "client_id": "CR1",
    "start": "2026-09-01T00:00:00+00:00",
    "end": "2026-10-01T00:00:00+00:00",
}


def test_a_query_over_the_byte_cap_is_refused_by_the_warehouse_and_reported_as_refused() -> None:
    from google.api_core.exceptions import BadRequest

    client = _Client(
        estimate=0,
        fail=BadRequest(
            "Query exceeded limit for bytes billed: 1000. 10485760 or higher required."
        ),
    )
    store = BigQueryWarmStore("proj", client=client, max_bytes=1_000)
    with pytest.raises(WarmQueryRefused):
        store.run("account_daily_activity", PARAMS)
    assert len(client.configs) == 1 and client.configs[0][1].maximum_bytes_billed == 1_000


def test_a_real_run_carries_the_cap_the_named_parameters_and_the_qualified_table() -> None:
    client = _Client(
        estimate=500,
        rows=[{"day": "2026-09-02", "deposits": 5.0, "withdrawals": 0.0, "transactions": 1}],
    )
    result = BigQueryWarmStore("proj", client=client, max_bytes=1_000).run(
        "account_daily_activity", PARAMS
    )
    sql, config = client.configs[-1]
    assert (
        "`proj.warm_aml.transactions_aml`" in sql
        and "@client_id" in sql
        and ":client_id" not in sql
    )
    assert config.maximum_bytes_billed == 1_000
    assert (
        result.rows[0]["deposits"] == 5.0
        and result.source == "warm.bigquery:proj.warm_aml.transactions_aml"
    )
    assert result.bytes_processed == 500


def test_every_job_is_labelled_so_its_spend_can_be_attributed_to_the_named_query() -> None:
    client = _Client(estimate=500)
    BigQueryWarmStore("proj", client=client, labels={"environment": "prod-like"}).run(
        "account_daily_activity", PARAMS
    )
    labels = client.configs[-1][1].labels
    assert labels == {
        "app": "eios",
        "component": "warm-tier",
        "query": "account_daily_activity",
        "environment": "prod-like",
    }


def test_a_label_the_warehouse_would_reject_is_dropped_not_sent() -> None:
    """BigQuery labels are lowercase letters, digits, underscores and dashes, 63 characters at most."""
    client = _Client(estimate=500)
    BigQueryWarmStore(
        "proj", client=client, labels={"Environment": "Prod Like", "x" * 64: "v", "ok": "y" * 64}
    ).run("account_daily_activity", PARAMS)
    assert set(client.configs[-1][1].labels) == {"app", "component", "query"}


def test_a_warehouse_failure_is_a_labelled_unavailable_not_an_empty_answer() -> None:
    from google.api_core.exceptions import ServiceUnavailable

    store = BigQueryWarmStore("proj", client=_Client(0, fail=ServiceUnavailable("down")))
    with pytest.raises(WarmUnavailable):
        store.run("account_daily_activity", PARAMS)
