"""Unit and integration tests for TimeBucketedPairDetector (T008 / US1).

Authoritative References:
- docs/brief/fraud [BRIEF fraud]
- specs/009-partner-fraud/spec.md (US1, FR-001, FR-002, FR-003)
- specs/009-partner-fraud/research.md §1
"""

import pandas as pd

from eios.fraud.models import DirectionalType
from eios.fraud.pair_detector import TimeBucketedPairDetector
from eios.ingestion.hot_state import HotStateEngine


def test_time_bucketed_pair_detector_identifies_planted_opposite_pairs(
    synthetic_trade_log: pd.DataFrame,
) -> None:
    detector = TimeBucketedPairDetector(
        bucket_window_sec=30.0,
        tau_timing_sec=5.0,
        min_co_occurrences=3,
    )

    pairs = detector.detect_pairs(synthetic_trade_log)

    # Must find the planted opposite pair: ACC-OPP-A1 & ACC-OPP-B1
    opp_pair = next(
        (
            p
            for p in pairs
            if (
                p.account_a in ["ACC-OPP-A1", "ACC-OPP-B1"]
                and p.account_b in ["ACC-OPP-A1", "ACC-OPP-B1"]
            )
        ),
        None,
    )
    assert opp_pair is not None, "Planted opposite trading pair was not detected!"
    assert opp_pair.directional_type == DirectionalType.OPPOSITE
    assert opp_pair.timing_correlation_pct >= 85.0
    assert opp_pair.size_symmetry_score >= 0.95
    assert opp_pair.zero_sum_ratio >= 0.85
    assert opp_pair.collusion_confidence >= 0.80

    # Must also detect planted mirror pair: ACC-MIRR-C1 & ACC-MIRR-D1
    mirr_pair = next(
        (
            p
            for p in pairs
            if (
                p.account_a in ["ACC-MIRR-C1", "ACC-MIRR-D1"]
                and p.account_b in ["ACC-MIRR-C1", "ACC-MIRR-D1"]
            )
        ),
        None,
    )
    assert mirr_pair is not None, "Planted mirror trading pair was not detected!"
    assert mirr_pair.directional_type == DirectionalType.MIRROR
    assert mirr_pair.timing_correlation_pct >= 85.0
    assert mirr_pair.collusion_confidence >= 0.75


def test_time_bucketed_pair_detector_filters_legitimate_hedgers(
    synthetic_trade_log: pd.DataFrame,
) -> None:
    """Bounded False Positive Rate on hard-negative legitimate hedgers."""
    detector = TimeBucketedPairDetector(
        bucket_window_sec=30.0,
        tau_timing_sec=5.0,
        min_co_occurrences=3,
    )

    pairs = detector.detect_pairs(synthetic_trade_log)

    # Legitimate hedgers ACC-HEDGE-1 & ACC-HEDGE-2 should either not pass co-occurrence/timing thresholds,
    # or have low collusion confidence (< 0.60)
    hedge_pair = next(
        (
            p
            for p in pairs
            if (
                p.account_a in ["ACC-HEDGE-1", "ACC-HEDGE-2"]
                and p.account_b in ["ACC-HEDGE-1", "ACC-HEDGE-2"]
            )
        ),
        None,
    )
    if hedge_pair is not None:
        assert hedge_pair.collusion_confidence < 0.60


def test_persist_pairs_to_hot_state(synthetic_trade_log: pd.DataFrame) -> None:
    hot_state = HotStateEngine()
    detector = TimeBucketedPairDetector(bucket_window_sec=30.0, min_co_occurrences=3)

    pairs = detector.detect_pairs(synthetic_trade_log)
    assert len(pairs) >= 2

    detector.persist_pairs_to_hot_state(hot_state, pairs)

    # Query DuckDB hot state
    cursor = hot_state.get_cursor()
    rows = cursor.execute("SELECT * FROM partner_opposite_trading_pairs").fetchall()
    assert len(rows) >= 2
