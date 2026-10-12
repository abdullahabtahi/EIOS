"""Unit and regression tests for ClientAMLPipeline (T046).

Authoritative References:
- docs/brief/monitoring.md [BRIEF monitoring]
- specs/010-client-aml/spec.md
- .specify/memory/constitution.md (Principles I, II, IV, VI, VII, VIII)
"""

from datetime import UTC, datetime, timedelta
import pandas as pd
import pytest

from eios.aml.pipeline import ClientAMLPipeline
from eios.ingestion.hot_state import HotStateEngine


def test_client_aml_pipeline_end_to_end() -> None:
    """Verify batch pipeline executes full detection and persistence across DuckDB hot state."""
    hot_state = HotStateEngine()
    pipeline = ClientAMLPipeline(hot_state=hot_state)

    base_dt = datetime.now(UTC) - timedelta(days=1)

    # 1. Transactions: 5 planted roundtrips
    txns = []
    trades = []
    for i in range(5):
        cid = f"C-PIPE-RT-{i}"
        t_dep = base_dt + timedelta(hours=i)
        t_tr = t_dep + timedelta(minutes=5)
        t_wth = t_dep + timedelta(minutes=20)

        txns.append({
            "transaction_id": f"TX-D-{i}",
            "client_id": cid,
            "transaction_type": "DEPOSIT",
            "amount": 500.0,
            "timestamp": t_dep,
            "kyc_approved_at": t_dep - timedelta(hours=10),
        })
        trades.append({
            "trade_id": f"TR-{i}",
            "client_id": cid,
            "symbol": "EURUSD",
            "volume": 0.01,
            "profit_loss": 0.01,
            "open_ts": t_tr,
            "close_ts": t_tr + timedelta(minutes=2),
        })
        txns.append({
            "transaction_id": f"TX-W-{i}",
            "client_id": cid,
            "transaction_type": "WITHDRAWAL",
            "amount": 499.50,
            "timestamp": t_wth,
            "kyc_approved_at": t_dep - timedelta(hours=10),
        })

    # 2. Mule Ring edges: 3 accounts sharing device token
    edges = [
        {"source_id": "C-PIPE-MULE-1", "target_id": "DEV-TOK-1", "edge_type": "DEVICE_FINGERPRINT", "is_shared_context": False},
        {"source_id": "C-PIPE-MULE-2", "target_id": "DEV-TOK-1", "edge_type": "DEVICE_FINGERPRINT", "is_shared_context": False},
        {"source_id": "C-PIPE-MULE-3", "target_id": "DEV-TOK-1", "edge_type": "DEVICE_FINGERPRINT", "is_shared_context": False},
    ]

    tx_df = pd.DataFrame(txns)
    tr_df = pd.DataFrame(trades)
    ed_df = pd.DataFrame(edges)

    metrics = pipeline.run_pipeline(
        transactions_df=tx_df,
        trading_df=tr_df,
        network_edges_df=ed_df,
    )

    assert metrics["roundtrips_detected"] == 5
    assert metrics["mule_clusters_detected"] == 1
    assert metrics["alerts_scored"] == 8
    assert metrics["top50_cases_prioritized"] == 8
    assert metrics["dossiers_created"] == 8

    # Verify DuckDB persistence
    cursor = hot_state.get_cursor()
    rt_count = cursor.execute("SELECT COUNT(*) FROM aml_roundtrip_events").fetchone()[0]
    assert rt_count == 5

    mule_count = cursor.execute("SELECT COUNT(*) FROM aml_mule_rings").fetchone()[0]
    assert mule_count == 3

    alert_count = cursor.execute("SELECT COUNT(*) FROM aml_alert_scores").fetchone()[0]
    assert alert_count == 8

    dossier_count = cursor.execute("SELECT COUNT(*) FROM aml_case_dossiers").fetchone()[0]
    assert dossier_count == 8
