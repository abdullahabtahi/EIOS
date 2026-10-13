"""Tests for User Story 5: Model Calibration Diagnostics & OMCP Integration."""

from datetime import UTC, datetime

import numpy as np

from eios.flywheel.models import CalibrationDiagnosticsReport
from eios.flywheel.schemas import validate_contract


def test_well_calibrated_diagnostics():
    from eios.flywheel.diagnostics import CalibrationDiagnosticsEngine

    # Generate well-calibrated probabilities: y ~ Bernoulli(p)
    rng = np.random.default_rng(42)
    n = 1000
    p = rng.uniform(0.0, 1.0, size=n)
    y = rng.binomial(1, p).astype(np.float64)

    engine = CalibrationDiagnosticsEngine(n_bins=10)
    report = engine.evaluate_calibration(
        predicted_probs=p,
        actual_labels=y,
        model_id="churn-hazard-model-v2",
    )

    assert isinstance(report, CalibrationDiagnosticsReport)
    assert report.sample_count == 1000
    assert report.expected_calibration_error < 0.05  # Well calibrated -> ECE < 5%
    assert report.brier_score < 0.25
    assert report.is_drift_detected is False
    assert len(report.reliability_bins) == 10


def test_drift_detection_miscalibrated():
    from eios.flywheel.diagnostics import CalibrationDiagnosticsEngine

    # Generate severely miscalibrated probabilities: predicted ~ 0.85, actual ~ 0.20
    n = 500
    p = np.full(n, 0.85)
    y = np.zeros(n)

    engine = CalibrationDiagnosticsEngine(drift_threshold=0.15)
    report = engine.evaluate_calibration(
        predicted_probs=p,
        actual_labels=y,
        model_id="overconfident-policy",
    )

    assert report.expected_calibration_error > 0.15
    assert report.is_drift_detected is True


def test_calibration_contract_validation():
    from eios.flywheel.diagnostics import CalibrationDiagnosticsEngine

    p = np.array([0.1, 0.4, 0.8, 0.9])
    y = np.array([0.0, 0.0, 1.0, 1.0])

    engine = CalibrationDiagnosticsEngine()
    report = engine.evaluate_calibration(
        predicted_probs=p,
        actual_labels=y,
        model_id="test-model",
    )

    dumped = report.model_dump(mode="json")
    assert validate_contract(dumped, "calibration-diagnostics-report") is True


def test_empty_samples_diagnostics():
    from eios.flywheel.diagnostics import CalibrationDiagnosticsEngine

    engine = CalibrationDiagnosticsEngine()
    report = engine.evaluate_calibration(
        predicted_probs=np.array([]),
        actual_labels=np.array([]),
        model_id="empty-model",
    )

    assert report.sample_count == 0
    assert report.expected_calibration_error == 0.0
    assert report.brier_score == 0.0
    assert report.is_drift_detected is False


def test_omcp_get_flywheel_calibration_status():
    from eios.ingestion.hot_state import HotStateEngine
    from eios.ontology.omcp.server import OMCPServer

    hot_state = HotStateEngine()
    server = OMCPServer(hot_state=hot_state)

    start = datetime.now(UTC)
    res = server.call_tool("get_flywheel_calibration_status", {"model_id": "churn-hazard-model-v2"})
    elapsed_ms = (datetime.now(UTC) - start).total_seconds() * 1000.0

    assert "expected_calibration_error" in res
    assert "brier_score" in res
    assert "reliability_bins" in res
    assert "is_drift_detected" in res
    assert res["model_id"] == "churn-hazard-model-v2"
    assert elapsed_ms < 200.0  # Must return under 200ms
    assert validate_contract(res, "calibration-diagnostics-report") is True
