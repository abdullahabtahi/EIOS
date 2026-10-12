"""Tests for HotStateEngine pruning and storage metrics (FM-1 Countermeasure)."""

from datetime import datetime, timezone, timedelta
from eios.contracts.base import DataProductEnum
from eios.ingestion.hot_state import HotStateEngine


def test_hot_state_storage_metrics_empty():
    engine = HotStateEngine(":memory:")
    metrics = engine.get_storage_metrics()
    assert metrics["total_tables"] > 0
    assert metrics["total_rows"] == 0
    assert "trading_activity" in metrics["table_counts"]
    engine.close()


def test_hot_state_pruning_sliding_window():
    engine = HotStateEngine(":memory:")
    cursor = engine.get_cursor()

    now = datetime.now(timezone.utc)
    old_ts = now - timedelta(days=45)
    recent_ts = now - timedelta(days=10)

    # Insert old record in trading_activity
    cursor.execute("""
        INSERT INTO trading_activity (
            trade_id, client_id, symbol, side, volume, open_price, close_price, open_ts
        ) VALUES ('T-OLD', 'C-1', 'EURUSD', 'BUY', 1.0, 1.1, 1.1, ?)
    """, [old_ts])

    # Insert recent record in trading_activity
    cursor.execute("""
        INSERT INTO trading_activity (
            trade_id, client_id, symbol, side, volume, open_price, close_price, open_ts
        ) VALUES ('T-NEW', 'C-1', 'EURUSD', 'BUY', 1.0, 1.1, 1.1, ?)
    """, [recent_ts])

    # Insert old record in partner_engagement_signals (date column)
    old_date = (now - timedelta(days=50)).date()
    recent_date = (now - timedelta(days=5)).date()
    cursor.execute("""
        INSERT INTO partner_engagement_signals (
            partner_id, date, logins, referrals, ftd_count, conversion_rate, clicks
        ) VALUES ('P-OLD', ?, 10, 5, 2, 0.25, 100)
    """, [old_date])
    cursor.execute("""
        INSERT INTO partner_engagement_signals (
            partner_id, date, logins, referrals, ftd_count, conversion_rate, clicks
        ) VALUES ('P-NEW', ?, 10, 5, 2, 0.25, 100)
    """, [recent_date])

    # Verify initial storage counts
    metrics_pre = engine.get_storage_metrics()
    assert metrics_pre["table_counts"]["trading_activity"] == 2
    assert metrics_pre["table_counts"]["partner_engagement_signals"] == 2

    # Prune records older than 30 days
    pruned = engine.prune_hot_state(max_age_days=30, as_of_ts=now)
    assert pruned["trading_activity"] == 1
    assert pruned["partner_engagement_signals"] == 1

    # Verify only recent records remain
    metrics_post = engine.get_storage_metrics()
    assert metrics_post["table_counts"]["trading_activity"] == 1
    assert metrics_post["table_counts"]["partner_engagement_signals"] == 1

    remaining_trades = cursor.execute("SELECT trade_id FROM trading_activity").fetchall()
    assert remaining_trades == [("T-NEW",)]

    remaining_daily = cursor.execute("SELECT partner_id FROM partner_engagement_signals").fetchall()
    assert remaining_daily == [("P-NEW",)]

    engine.close()
