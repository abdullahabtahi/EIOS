"""get_account_history answers from the warm tier, and says so plainly when it cannot."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from eios.contracts.base import DataProductEnum
from eios.ontology.omcp.port.catalogue import build_port
from eios.ontology.omcp.port.contracts import ToolErrorCode
from eios.ontology.omcp.port.readmodels import ReadModels
from eios.warm.sink import LocalWarmSink
from eios.warm.store import LocalWarmStore, WarmResult, WarmUnavailable

from .conftest import who

NOW = datetime(2026, 10, 15, 8, tzinfo=UTC)


def _txn(txn_id: str, kind: str, amount: float, days_ago: int) -> dict[str, Any]:
    return {
        "txn_id": txn_id,
        "client_id": "CR84920",
        "txn_type": kind,
        "amount": amount,
        "currency": "USD",
        "payment_method_id": "tok_1",
        "timestamp": (NOW - timedelta(days=days_ago)).isoformat(),
        "status": "COMPLETED",
        "_batch_id": "b1",
        "_loaded_at": NOW.isoformat(),
        "_source": "test",
        "_tenant_id": "DERIV_MFSA",
    }


def _port(warm: Any) -> Any:
    models = replace(ReadModels.default(), warm=warm, clock=lambda: NOW)
    return build_port(models)


@pytest.fixture
def loaded_port():
    sink = LocalWarmSink()
    sink.load(
        DataProductEnum.TRANSACTIONS_AML,
        [
            _txn("TX-000001", "DEPOSIT", 1000.0, 20),
            _txn("TX-000002", "DEPOSIT", 4000.0, 3),
            _txn("TX-000003", "WITHDRAWAL", 3500.0, 3),
            _txn("TX-000004", "DEPOSIT", 50.0, 80),  # outside a 30-day window
        ],
        batch_id="b1",
    )
    return _port(LocalWarmStore(sink.connection))


def test_the_history_is_the_window_the_warehouse_holds_with_totals_and_a_named_source(
    loaded_port,
) -> None:
    out = loaded_port.call(
        who("aml_investigator"), "get_account_history", {"entity_id": "CR84920", "days": 30}
    )
    assert out.error is None, out.error
    r = out.result
    assert (r.active_days, r.total_deposits_usd, r.total_withdrawals_usd, r.total_transactions) == (
        2,
        5000.0,
        3500.0,
        3,
    )
    assert r.busiest_day_deposits_usd == 4000.0 and r.busiest_day is not None
    assert [d.deposits_usd for d in r.days] == [1000.0, 4000.0]
    assert r.source == "warm.local:warm_aml.transactions_aml" and r.window_days == 30
    assert r.units["total_deposits_usd"] == "USD" and "total_deposits_usd" in r.fact_ids


def test_a_longer_window_reaches_the_older_rows(loaded_port) -> None:
    out = loaded_port.call(
        who("aml_investigator"), "get_account_history", {"entity_id": "CR84920", "days": 90}
    )
    assert out.result.total_deposits_usd == 5050.0


def test_an_account_with_no_activity_gets_an_empty_answer_not_zeros_pretending_to_be_data() -> None:
    port = _port(LocalWarmStore(LocalWarmSink().connection))
    out = port.call(who("aml_investigator"), "get_account_history", {"entity_id": "CR84920"})
    assert out.error is None and out.result.days == []
    assert out.result.busiest_day is None and out.result.busiest_day_deposits_usd is None


def test_no_warm_tier_configured_is_data_unavailable() -> None:
    out = _port(None).call(who("aml_investigator"), "get_account_history", {"entity_id": "CR84920"})
    assert out.error is not None and out.error.code is ToolErrorCode.DATA_UNAVAILABLE


def test_a_warehouse_failure_is_data_unavailable_with_its_reason() -> None:
    class Down:
        backend = "bigquery"

        def run(self, query: str, params: Any) -> WarmResult:
            raise WarmUnavailable("the warehouse could not answer: ServiceUnavailable")

    out = _port(Down()).call(
        who("aml_investigator"), "get_account_history", {"entity_id": "CR84920"}
    )
    assert (
        out.error.code is ToolErrorCode.DATA_UNAVAILABLE
        and "ServiceUnavailable" in out.error.message
    )


def test_only_the_aml_workstation_is_offered_it_and_the_window_is_bounded(loaded_port) -> None:
    refused = loaded_port.call(
        who("partner_manager"), "get_account_history", {"entity_id": "CR84920"}
    )
    assert refused.error is not None and refused.error.code is ToolErrorCode.FORBIDDEN_ROLE
    too_long = loaded_port.call(
        who("aml_investigator"), "get_account_history", {"entity_id": "CR84920", "days": 400}
    )
    assert too_long.error is not None and too_long.error.code is ToolErrorCode.INVALID_ARGUMENTS
