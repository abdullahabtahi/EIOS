"""The operations plane is measured, not typed: real ingestion, real probes, a real restore (spec 035)."""

from typing import Any

import pytest

from eios.dataplane.ops_replay import BREACH_SHARE
from eios.dataplane.ops_service import RedriveRejectedError, UnknownRecordError
from eios.ontology.omcp.port.catalogue import build_port
from eios.ontology.omcp.port.contracts import DataOrigin
from eios.ontology.omcp.port.principal import principal_for

OPS = principal_for("uid-test", "data_operations")


@pytest.fixture(scope="module")
def models(ops_models):
    return ops_models[0]


@pytest.fixture(scope="module")
def ops(ops_models):
    return ops_models[1]


@pytest.fixture(scope="module")
def port(models):
    return build_port(models)


def _ok(port: Any, tool: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
    outcome = port.call(OPS, tool, args or {})
    assert outcome.error is None, outcome.error
    return outcome.payload()


def test_every_planted_breach_is_quarantined_and_no_healthy_event_is_refused(ops) -> None:
    r = ops.replay
    assert r.planted > 0 and r.caught == r.planted and r.false_rejects == 0
    assert r.enforcement_correct
    assert abs(r.breach_rate - BREACH_SHARE) < 0.003
    assert len(r.dlq) == r.rejected
    assert {rec["status"] for rec in ops.dlq_records()} == {"QUARANTINED"}


def test_products_are_profiled_from_their_frames_and_the_breached_one_is_flagged(ops) -> None:
    board = ops.get_board_summary()
    by = {p["product_name"]: p for p in board["products"]}
    assert by["transactions_aml"]["status"] == "DEGRADED"
    assert (
        by["transactions_aml"]["contract_validated"]
        and by["transactions_aml"]["quarantined_records"] > 0
    )
    assert all(
        not p["freshness_judged"] for p in board["products"]
    )  # a batch snapshot has no ingestion delay to judge
    assert (
        by["client_360"]["status"] == "HEALTHY"
    )  # an empty optional column is not a quality failure
    assert board["unresolved_conflicts_count"] is None  # not assessed is not zero
    assert (
        board["healthy_products"] + board["degraded_products"] + board["breached_products"]
        == board["total_products"]
    )
    assert [a["product_name"] for a in board["alerts"]] == ["transactions_aml"]


def test_an_unobserved_objective_reads_no_data_never_healthy(ops) -> None:
    rows = {b["slo_id"]: b for b in ops.error_budgets()}
    for unobserved in (
        "agent_turn_full_answer",
        "ingestion_freshness",
        "approval_service_availability",
        "hallucination_gate",
    ):
        assert rows[unobserved]["status"] == "NO_DATA" and rows[unobserved]["consumed_pct"] is None
    assert rows["contract_enforcement"]["total_events"] == ops.replay.offered
    assert rows["contract_enforcement"]["status"] == "HEALTHY"


def test_red_lines_are_measured_and_what_is_not_says_so(ops) -> None:
    gates = {g.gate_id: g for g in ops.red_lines()}
    assert [gates[i].status for i in ("RL-1", "RL-3", "RL-4", "RL-5", "RL-6")] == ["PASS"] * 5
    assert gates["RL-6"].margin is not None and gates["RL-6"].margin > 0
    assert gates["RL-2"].status == gates["RL-7"].status == "NOT_MEASURED"


def test_the_restore_drill_rehydrates_what_was_exported(ops) -> None:
    d = ops.drill
    assert d.verified and d.rows_restored == d.rows_exported > 0
    assert len(d.checkpoint_hash) == 64


def test_redrive_goes_through_the_pipeline_and_a_record_that_still_breaks_stays_quarantined(
    ops,
) -> None:
    record = ops.dlq_records()[0]
    with pytest.raises(RedriveRejectedError):
        ops.redrive(record["dlq_id"], None)  # the payload is still the breached one
    assert (
        next(r for r in ops.dlq_records() if r["dlq_id"] == record["dlq_id"])["status"]
        == "QUARANTINED"
    )
    done = ops.redrive(record["dlq_id"], {"amount": 120.5})
    assert done["status"] == "REDRIVEN_COMMITTED" and done["redrive_count"] == 2
    with pytest.raises(UnknownRecordError):
        ops.redrive("no-such-record", None)


def test_the_tools_carry_the_engine_origin_and_the_honest_gaps(port) -> None:
    board = _ok(port, "get_dq_board")
    assert (
        board["data_origin"] == DataOrigin.ENGINE.value
        and board["unresolved_conflicts_count"] is None
    )
    rel = _ok(port, "get_reliability")
    nodata = [o for o in rel["objectives"] if o["status"] == "NO_DATA"]
    assert nodata and all(
        o["compliance_percentage"] is None and o["budget_remaining_pct"] is None for o in nodata
    )
    drill = _ok(port, "get_drill_status")
    assert drill["restore_drill"]["verified"] is True and "catalogue only" in drill["scope"]
    lines = _ok(port, "get_red_lines")
    assert {g["gate_id"]: g["status"] for g in lines["gates"]}["RL-7"] == "NOT_MEASURED"


def test_calibration_is_measured_against_what_partners_then_did(port) -> None:
    got = _ok(port, "get_calibration_status")
    assert got["sample_count"] > 100 and 0.0 <= got["expected_calibration_error"] <= 1.0
    assert got["basis"] and got["data_origin"] == DataOrigin.ENGINE.value
