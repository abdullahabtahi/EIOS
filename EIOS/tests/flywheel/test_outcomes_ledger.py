"""Tests for User Story 1: Multi-Horizon Decision Outcomes Ledger & Reconciliation."""

import threading
import time
import uuid
from datetime import UTC, datetime

import pytest

from eios.flywheel.covariates import CovariateMatrixBuilder, clip_propensity_scores
from eios.flywheel.ledger import DecisionOutcomesLedger, compute_record_lineage_hash
from eios.flywheel.models import DecisionOutcomeRecord, MilestoneStatus
from eios.flywheel.schemas import validate_contract


def _make_dummy_record(
    decision_id: str | None = None,
    intent_id: str | None = None,
    action_type: str = "fee_tier_restructure",
    entity_id: str = "PARTNER-101",
    propensity: float = 0.65,
    treatment: bool = True,
    pred_30d: float = 5000.0,
    pred_60d: float = 10000.0,
    pred_90d: float = 15000.0,
) -> DecisionOutcomeRecord:
    did = decision_id or str(uuid.uuid4())
    iid = intent_id or f"INTENT-{uuid.uuid4().hex[:8]}"
    now = datetime.now(UTC)
    h = compute_record_lineage_hash(
        decision_id=did,
        intent_id=iid,
        timestamp=now,
        entity_id=entity_id,
        action_type=action_type,
        propensity_score=propensity,
        treatment_assigned=treatment,
    )
    return DecisionOutcomeRecord(
        decision_id=did,
        intent_id=iid,
        timestamp=now,
        service_name="churn_service",
        action_type=action_type,
        entity_type="Partner",
        entity_id=entity_id,
        propensity_score=propensity,
        treatment_assigned=treatment,
        covariates={"monthly_volume": 45000.0, "tenure_months": 18.0, "hazard_score": 0.42},
        predicted_impact_30d=pred_30d,
        actual_impact_30d=None,
        residual_30d=None,
        status_30d=MilestoneStatus.PENDING,
        predicted_impact_60d=pred_60d,
        actual_impact_60d=None,
        residual_60d=None,
        status_60d=MilestoneStatus.PENDING,
        predicted_impact_90d=pred_90d,
        actual_impact_90d=None,
        residual_90d=None,
        status_90d=MilestoneStatus.PENDING,
        provenance_hash=h,
    )


def test_ledger_append_and_retrieve():
    ledger = DecisionOutcomesLedger()
    rec = _make_dummy_record()
    appended = ledger.append_decision(rec)

    assert appended.decision_id == rec.decision_id
    assert ledger.count() == 1

    fetched = ledger.get_by_id(rec.decision_id)
    assert fetched is not None
    assert fetched.intent_id == rec.intent_id

    fetched_intent = ledger.get_by_intent_id(rec.intent_id)
    assert fetched_intent is not None
    assert fetched_intent.decision_id == rec.decision_id

    by_entity = ledger.get_by_entity(rec.entity_id)
    assert len(by_entity) == 1
    assert by_entity[0].decision_id == rec.decision_id


def test_ledger_contract_validation():
    rec = _make_dummy_record()
    dumped = rec.model_dump(mode="json")
    is_valid = validate_contract(dumped, "decision-outcome-record")
    assert is_valid is True


def test_milestone_reconciliation_residuals():
    ledger = DecisionOutcomesLedger()
    rec = _make_dummy_record(pred_30d=5000.0, pred_60d=10000.0, pred_90d=15000.0)
    ledger.append_decision(rec)

    # Reconcile 30d
    up30 = ledger.update_milestone(
        decision_id=rec.decision_id,
        horizon="30d",
        actual_impact=6200.0,
        status=MilestoneStatus.RECONCILED,
    )
    assert up30.actual_impact_30d == 6200.0
    assert up30.residual_30d == 1200.0
    assert up30.status_30d == MilestoneStatus.RECONCILED
    assert up30.status_60d == MilestoneStatus.PENDING

    # Reconcile 60d
    up60 = ledger.update_milestone(
        decision_id=rec.decision_id,
        horizon="60d",
        actual_impact=9500.0,
        status=MilestoneStatus.RECONCILED,
    )
    assert up60.actual_impact_60d == 9500.0
    assert up60.residual_60d == -500.0
    assert up60.status_60d == MilestoneStatus.RECONCILED

    # Reconcile 90d
    up90 = ledger.update_milestone(
        decision_id=rec.decision_id,
        horizon="90d",
        actual_impact=16000.0,
        status=MilestoneStatus.RECONCILED,
    )
    assert up90.actual_impact_90d == 16000.0
    assert up90.residual_90d == 1000.0
    assert up90.status_90d == MilestoneStatus.RECONCILED

    # Re-validate schema contract with reconciled data
    dumped = up90.model_dump(mode="json")
    assert validate_contract(dumped, "decision-outcome-record") is True


def test_propensity_score_clipping():
    raw_props = [0.0001, 0.05, 0.50, 0.95, 0.9999]
    clipped = clip_propensity_scores(raw_props, epsilon=0.01)

    assert clipped[0] == pytest.approx(0.01)
    assert clipped[1] == pytest.approx(0.05)
    assert clipped[2] == pytest.approx(0.50)
    assert clipped[3] == pytest.approx(0.95)
    assert clipped[4] == pytest.approx(0.99)


def test_covariate_matrix_builder():
    rec1 = _make_dummy_record()
    rec2 = _make_dummy_record()
    builder = CovariateMatrixBuilder()
    names = builder.fit_feature_names([rec1, rec2])
    assert "hazard_score" in names
    assert "monthly_volume" in names

    matrix = builder.build_matrix([rec1, rec2])
    assert matrix.shape == (2, len(names))


def test_ledger_concurrency_and_performance():
    ledger = DecisionOutcomesLedger()
    records_to_add = 1000
    records = [_make_dummy_record() for _ in range(records_to_add)]

    start_time = time.perf_counter()

    def worker(chunk):
        for r in chunk:
            ledger.append_decision(r)

    threads = []
    chunk_size = 250
    for i in range(0, records_to_add, chunk_size):
        t = threading.Thread(target=worker, args=(records[i : i + chunk_size],))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    duration = time.perf_counter() - start_time
    assert ledger.count() == 1000
    assert duration < 2.0  # Must ingest 1,000 records in < 2 seconds


def test_milestone_reconciliation_engine():
    from eios.flywheel.reconciliation import MilestoneReconciliationEngine

    ledger = DecisionOutcomesLedger()
    rec1 = _make_dummy_record(pred_30d=1000.0)
    rec2 = _make_dummy_record(pred_30d=2000.0)
    ledger.append_decision(rec1)
    ledger.append_decision(rec2)

    engine = MilestoneReconciliationEngine(ledger=ledger)
    res = engine.batch_reconcile(
        [
            {"decision_id": rec1.decision_id, "actual_impact": 1200.0, "horizon": "30d"},
            {"decision_id": rec2.decision_id, "actual_impact": 1900.0, "horizon": "30d"},
        ]
    )

    assert res.reconciled_count == 2
    assert res.failed_count == 0
    assert res.mean_residual_30d == pytest.approx(50.0)  # (200 - 100) / 2 = 50.0
