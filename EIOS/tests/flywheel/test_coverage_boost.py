"""Additional edge-case and branch coverage tests for eios.flywheel."""

from datetime import UTC, datetime, timedelta
import numpy as np
import pytest

from eios.flywheel.models import DecisionOutcomeRecord, MilestoneStatus
from eios.flywheel.ledger import DecisionOutcomesLedger
from eios.flywheel.covariates import CovariateMatrixBuilder
from eios.flywheel.reconciliation import MilestoneReconciliationEngine
from eios.flywheel.schemas import get_contracts_dir, load_schema
from tests.flywheel.test_outcomes_ledger import _make_dummy_record


def test_covariates_extract_aligned_arrays():
    builder = CovariateMatrixBuilder()
    
    # Empty records
    Y, W, e, X, ids = builder.extract_aligned_arrays([])
    assert len(Y) == 0
    assert len(ids) == 0

    # Records with 30d, 60d, 90d actuals
    r1 = _make_dummy_record()
    r1 = r1.model_copy(update={"actual_impact_30d": 100.0, "actual_impact_60d": 200.0, "actual_impact_90d": 300.0})
    
    r2 = _make_dummy_record(treatment=False)
    r2 = r2.model_copy(update={"actual_impact_30d": 50.0, "actual_impact_60d": 120.0, "actual_impact_90d": 180.0})

    Y30, W30, e30, X30, ids30 = builder.extract_aligned_arrays([r1, r2], target_horizon="30d")
    assert len(Y30) == 2
    assert W30[0] == 1.0 and W30[1] == 0.0

    Y60, W60, e60, X60, ids60 = builder.extract_aligned_arrays([r1, r2], target_horizon="60d")
    assert len(Y60) == 2

    Y90, W90, e90, X90, ids90 = builder.extract_aligned_arrays([r1, r2], target_horizon="90d")
    assert len(Y90) == 2

    with pytest.raises(ValueError, match="Unsupported target horizon"):
        builder.extract_aligned_arrays([r1], target_horizon="180d")


def test_ledger_query_filters_and_errors():
    ledger = DecisionOutcomesLedger()
    now = datetime.now(UTC)

    r1 = _make_dummy_record(action_type="act1", entity_id="E1")
    r1 = r1.model_copy(update={"timestamp": now - timedelta(days=10), "service_name": "srv1", "treatment_assigned": True})
    
    r2 = _make_dummy_record(action_type="act2", entity_id="E2")
    r2 = r2.model_copy(update={"timestamp": now, "service_name": "srv2", "treatment_assigned": False, "status_30d": MilestoneStatus.RECONCILED})

    ledger.append_decision(r1)
    ledger.append_decision(r2)

    # Duplicate append error
    with pytest.raises(ValueError, match="already exists"):
        ledger.append_decision(r1)

    # Query with filters
    res_srv = ledger.query_records(service_name="srv1")
    assert len(res_srv) == 1
    assert res_srv[0].service_name == "srv1"

    res_act = ledger.query_records(action_type="act2")
    assert len(res_act) == 1

    res_ent = ledger.query_records(entity_type="Partner")
    assert len(res_ent) == 2

    res_treat = ledger.query_records(treatment_assigned=True)
    assert len(res_treat) == 1

    res_time = ledger.query_records(start_time=now - timedelta(days=5), end_time=now + timedelta(days=1))
    assert len(res_time) == 1

    res_hor30 = ledger.query_records(horizon_filter="30d", horizon_status=MilestoneStatus.RECONCILED)
    assert len(res_hor30) == 1

    res_hor60 = ledger.query_records(horizon_filter="60d", horizon_status=MilestoneStatus.RECONCILED)
    assert len(res_hor60) == 0

    res_hor90 = ledger.query_records(horizon_filter="90d", horizon_status=MilestoneStatus.RECONCILED)
    assert len(res_hor90) == 0

    # Non-existent ID errors
    with pytest.raises(KeyError, match="not found in ledger"):
        ledger.update_milestone(decision_id="nonexistent", horizon="30d", actual_impact=100.0)

    # Invalid horizon
    with pytest.raises(ValueError, match="Invalid horizon"):
        ledger.update_milestone(decision_id=r1.decision_id, horizon="120d", actual_impact=100.0)

    # Clear ledger
    ledger.clear()
    assert ledger.count() == 0


def test_reconciliation_engine_horizons_and_errors():
    ledger = DecisionOutcomesLedger()
    engine = MilestoneReconciliationEngine(ledger=ledger)

    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    assert engine.determine_horizon(t0, t0 + timedelta(days=30)) == "30d"
    assert engine.determine_horizon(t0, t0 + timedelta(days=60)) == "60d"
    assert engine.determine_horizon(t0, t0 + timedelta(days=90)) == "90d"

    # Non-existent decision
    with pytest.raises(KeyError, match="not found in ledger"):
        engine.reconcile_observation(decision_id="missing", actual_impact=100.0)

    # Batch reconcile with invalid observation
    batch_res = engine.batch_reconcile([
        {"invalid": "format"},
        {"decision_id": "missing", "actual_impact": 100.0},
    ])
    assert batch_res.failed_count == 2
    assert batch_res.reconciled_count == 0


def test_schemas_utility_functions():
    cdir = get_contracts_dir()
    assert cdir.exists()

    with pytest.raises(FileNotFoundError):
        load_schema("non-existent-schema-12345")
