"""Unit and validation tests for seasonality-aware change-point detection (T019, T022)."""

from datetime import date, timedelta

import pandas as pd

from eios.churn.change_point import SeasonalityChangePointDetector


def test_weekend_market_pauses_masked():
    """Verify that regular weekend 0-trading pauses do not trigger false change-point alerts."""
    detector = SeasonalityChangePointDetector()

    # Generate 4 weeks of standard partner activity with weekend zeros
    records = []
    base_date = date(2026, 9, 1)
    for d in range(28):
        cur_date = base_date + timedelta(days=d)
        is_weekend = cur_date.weekday() >= 5
        records.append(
            {
                "partner_id": "P-NORMAL",
                "date": cur_date,
                "volume": 0 if is_weekend else 25,
            }
        )
    df = pd.DataFrame(records)

    result = detector.detect_change_point(df, metric_col="volume")
    assert result["is_anomaly"] is False
    assert result["confidence"] <= 0.20


def test_hard_negative_vacation_suppressed():
    """Verify that temporary 2-week vacation dip (P-HARD-NEG-VACATION) is suppressed (T022 / FPR <= 5%)."""
    detector = SeasonalityChangePointDetector()

    records = []
    base_date = date(2026, 9, 1)
    # 5 weeks: 2 weeks normal, 2 weeks holiday vacation (0 volume), 1 week recovery
    for d in range(35):
        cur_date = base_date + timedelta(days=d)
        is_weekend = cur_date.weekday() >= 5
        if is_weekend:
            vol = 0
        elif 14 <= d < 28:
            vol = 0  # 2-week vacation
        else:
            vol = 30  # Active trading

        records.append(
            {
                "partner_id": "P-HARD-NEG-VACATION",
                "date": cur_date,
                "volume": vol,
            }
        )
    df = pd.DataFrame(records)

    result = detector.detect_change_point(df, metric_col="volume")
    # Recovery in week 5 proves temporary seasonal pause, not structural disengagement
    assert result["is_anomaly"] is False
    assert result["reason"] in ["SEASONAL_DIP_RECOVERED", "NORMAL_STABLE"]


def test_structural_churn_drift_detected():
    """Verify that sustained structural decay across consecutive active trading weeks IS detected."""
    detector = SeasonalityChangePointDetector()

    records = []
    base_date = date(2026, 9, 1)
    # 5 weeks: 2 weeks normal (40 volume), followed by 3 weeks sustained decay (15, 8, 2 volume)
    for d in range(35):
        cur_date = base_date + timedelta(days=d)
        is_weekend = cur_date.weekday() >= 5
        if is_weekend:
            vol = 0
        elif d < 14:
            vol = 40
        elif d < 21:
            vol = 15
        elif d < 28:
            vol = 8
        else:
            vol = 2  # Complete decay

        records.append(
            {
                "partner_id": "P-CHURN-DRIFT",
                "date": cur_date,
                "volume": vol,
            }
        )
    df = pd.DataFrame(records)

    result = detector.detect_change_point(df, metric_col="volume")
    assert result["is_anomaly"] is True
    assert result["confidence"] >= 0.85
    assert result["reason"] == "STRUCTURAL_DISENGAGEMENT"
