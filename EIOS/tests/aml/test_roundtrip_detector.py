"""Unit and sequence matching tests for Round-Trip Structuring Detector (US3 / P1).

Authoritative References:
- docs/brief/monitoring.md [BRIEF monitoring]
- initial_plan.md §5.4
- specs/010-client-aml/spec.md (User Story 3)
"""

import pandas as pd

from eios.aml.roundtrip_detector import RoundTripDetector
from eios.ingestion.hot_state import HotStateEngine


def test_roundtrip_detector_identifies_micro_pnl_laundering(
    synthetic_roundtrip_history: pd.DataFrame,
) -> None:
    """Test detection of deposit -> 10m micro-P&L trade -> withdraw pattern within 72h KYC."""
    detector = RoundTripDetector()
    results = detector.detect_roundtrips(synthetic_roundtrip_history, window_hours=72.0)

    # Filter by planted account
    planted_events = [r for r in results if r.client_id == "C-AML-ROUNDTRIP-01"]
    assert len(planted_events) >= 1
    event = planted_events[0]

    assert event.deposit_amount_usd == 500.0
    assert event.withdrawal_amount_usd == 499.50
    assert abs(event.net_pl_usd) <= 0.05
    assert event.market_risk_pct <= 0.001
    assert event.typology_risk_score >= 0.85
    assert event.hours_since_kyc <= 72.0


def test_roundtrip_detector_discriminates_legitimate_scalper(
    synthetic_roundtrip_history: pd.DataFrame,
) -> None:
    """Ensure legitimate retail scalper with real P&L variance is not flagged."""
    detector = RoundTripDetector()
    results = detector.detect_roundtrips(synthetic_roundtrip_history, window_hours=72.0)

    scalper_events = [r for r in results if r.client_id == "C-LEGIT-SCALPER-01"]
    # Scalper took directional variance, so either not flagged or risk score < 0.40
    for ev in scalper_events:
        assert ev.typology_risk_score < 0.40


def test_roundtrip_detector_persists_to_hot_state(
    synthetic_roundtrip_history: pd.DataFrame,
) -> None:
    """Test DuckDB hot-state persistence into aml_roundtrip_events."""
    hot_state = HotStateEngine()
    detector = RoundTripDetector(hot_state=hot_state)

    results = detector.detect_roundtrips(synthetic_roundtrip_history, window_hours=72.0)
    persisted_count = detector.persist_events(results)
    assert persisted_count >= 1

    cursor = hot_state.get_cursor()
    row = cursor.execute(
        "SELECT client_id, deposit_amount_usd, net_pl_usd, typology_risk_score FROM aml_roundtrip_events WHERE client_id = 'C-AML-ROUNDTRIP-01'"
    ).fetchone()

    assert row is not None
    assert row[0] == "C-AML-ROUNDTRIP-01"
    assert row[1] == 500.0
    assert row[2] == 0.01
    assert row[3] >= 0.85
