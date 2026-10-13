"""Unit and integration test for PartnerFraudPipeline (T041).

Authoritative References:
- specs/009-partner-fraud/spec.md
- specs/009-partner-fraud/plan.md §4
"""

import pandas as pd

from eios.fraud.pipeline import PartnerFraudPipeline
from eios.ingestion.hot_state import HotStateEngine


def test_partner_fraud_pipeline_end_to_end(
    synthetic_trade_log: pd.DataFrame,
    synthetic_referral_tree: list[dict],
    synthetic_client_lifecycles: list[dict],
    synthetic_clickstream_funnels: list[dict],
) -> None:
    hs = HotStateEngine()
    pipeline = PartnerFraudPipeline(hot_state=hs)

    summary = pipeline.run_pipeline(
        trade_df=synthetic_trade_log,
        tree_records=synthetic_referral_tree,
        client_records=synthetic_client_lifecycles,
        funnel_records=synthetic_clickstream_funnels,
    )

    assert summary["pairs_detected"] >= 2
    assert summary["scores_inserted"] >= 4
    assert summary["cases_inserted"] >= 1

    # Verify DuckDB table contents
    cursor = hs.get_cursor()
    scores = cursor.execute("SELECT * FROM partner_fraud_scores").fetchall()
    assert len(scores) >= 4

    cases = cursor.execute("SELECT * FROM partner_fraud_cases").fetchall()
    assert len(cases) >= 1
