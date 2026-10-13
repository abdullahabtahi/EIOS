"""Unit tests for Analyst Feedback Loop and Novel Typology Miner (US7 / P3).

Authoritative References:
- docs/brief/monitoring.md [BRIEF monitoring]
- specs/010-client-aml/spec.md (User Story 7, SC-009, FR-015, FR-016)
- .specify/memory/constitution.md (Principles I, VI)
"""

import pandas as pd

from eios.aml.emerging_typologies import EmergingTypologyMiner
from eios.aml.feedback_loop import AnalystDisposition, AnalystFeedbackLoop
from eios.aml.triage_scorer import AlertTriageScorer


def test_analyst_feedback_loop_recalibration() -> None:
    """Verify analyst dispositions recalibrate alert scoring threshold and weights."""
    loop = AnalystFeedbackLoop(initial_threshold=0.75)

    dispositions = []
    # 20 confirmed SARs (true positives with high score)
    for i in range(20):
        dispositions.append(
            AnalystDisposition(
                alert_id=f"ALT-TP-{i}",
                client_id=f"C-TP-{i}",
                risk_score=0.88 + (i % 5) * 0.02,
                disposition="CONFIRMED_SAR",
                analyst_id="ANALYST-01",
            )
        )
    # 80 dismissed false alarms (false positives with border scores)
    for i in range(80):
        dispositions.append(
            AnalystDisposition(
                alert_id=f"ALT-FP-{i}",
                client_id=f"C-FP-{i}",
                risk_score=0.76 + (i % 4) * 0.02,
                disposition="DISMISSED_FALSE_POSITIVE",
                analyst_id="ANALYST-02",
            )
        )

    result = loop.process_disposition_batch(dispositions)

    assert result["processed_count"] == 100
    assert result["confirmed_sars"] == 20
    assert result["dismissed_false_positives"] == 80
    assert result["new_threshold"] > result["initial_threshold"]
    assert result["recalibrated"] is True

    # Test scorer threshold update
    scorer = AlertTriageScorer()
    old_thresh = scorer.min_score_threshold
    loop.apply_to_scorer(scorer)
    assert scorer.min_score_threshold >= old_thresh


def test_emerging_typology_miner_surfaces_zero_day_scheme() -> None:
    """Verify unsupervised miner isolates novel cross-asset laundering in top-5 candidates (SC-009)."""
    miner = EmergingTypologyMiner(top_k=5)

    # Synthetic residual transactions (unexplained by standard rules)
    records = []
    # 200 normal residual transactions
    for i in range(200):
        records.append(
            {
                "client_id": f"C-NORM-{i}",
                "txn_id": f"TXN-NORM-{i}",
                "amount_usd": 150.0 + (i % 20) * 10.0,
                "distinct_instruments_count": 1,
                "rapid_turnaround_ratio": 0.1,
                "off_hours_ratio": 0.05,
                "asset_spread_entropy": 0.1,
            }
        )

    # Novel unplanted scheme: 8 coordinated clients with multi-instrument dispersion and high entropy
    for i in range(8):
        records.append(
            {
                "client_id": f"C-NOVEL-{i}",
                "txn_id": f"TXN-NOVEL-{i}",
                "amount_usd": 4850.0 + (i % 3) * 50.0,
                "distinct_instruments_count": 7,
                "rapid_turnaround_ratio": 0.95,
                "off_hours_ratio": 0.85,
                "asset_spread_entropy": 0.92,
            }
        )

    df = pd.DataFrame(records)
    candidates = miner.mine_emerging_typologies(df)

    assert len(candidates) >= 1
    assert len(candidates) <= 5

    # Check top candidate flags novel syndicate
    top_cand = candidates[0]
    assert top_cand.anomaly_score >= 0.80
    assert any("C-NOVEL" in cid for cid in top_cand.participating_clients)
    assert (
        "CROSS_ASSET" in top_cand.candidate_name
        or "MULTI_INSTRUMENT" in top_cand.candidate_name
        or "NOVEL" in top_cand.candidate_name
    )
    assert len(top_cand.participating_clients) >= 4
