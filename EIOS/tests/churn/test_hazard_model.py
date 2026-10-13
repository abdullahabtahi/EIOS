"""Unit tests for discrete-time hazard model fitting and inference (T008)."""

import numpy as np
import pandas as pd

from eios.churn.hazard_model import DiscreteTimeHazardModel


def test_hazard_model_fit_and_predict():
    """Verify hazard model can train on person-period data and output valid cumulative probabilities."""
    np.random.seed(42)
    n_partners = 100

    records = []
    for pid in range(n_partners):
        login_decay = np.random.uniform(0.0, 1.0)
        negative_sentiment = np.random.uniform(0.0, 1.0)
        comm_drop = np.random.uniform(-0.5, 0.5)

        # Higher decay & sentiment -> higher churn probability
        true_hazard = 1 / (1 + np.exp(-(-2.0 + 3.0 * login_decay + 2.0 * negative_sentiment)))

        churned = False
        for week in range(1, 5):
            event = 0
            if not churned and np.random.rand() < true_hazard:
                event = 1
                churned = True

            records.append(
                {
                    "partner_id": f"P-{pid}",
                    "period_week": week,
                    "login_velocity_decay_3w": login_decay,
                    "sentiment_negative_ratio": negative_sentiment,
                    "commission_velocity_30d": comm_drop,
                    "competitor_mention_flag": float(negative_sentiment > 0.6),
                    "churn_event": event,
                }
            )
            if churned:
                break

    df_train = pd.DataFrame(records)

    model = DiscreteTimeHazardModel()
    model.fit(
        df_train,
        feature_cols=[
            "login_velocity_decay_3w",
            "sentiment_negative_ratio",
            "commission_velocity_30d",
            "competitor_mention_flag",
        ],
        duration_col="period_week",
        event_col="churn_event",
    )

    # Test inference on test partners
    df_test = pd.DataFrame(
        [
            {
                "partner_id": "TEST-HIGH",
                "login_velocity_decay_3w": 0.85,
                "sentiment_negative_ratio": 0.90,
                "commission_velocity_30d": -0.40,
                "competitor_mention_flag": 1.0,
            },
            {
                "partner_id": "TEST-LOW",
                "login_velocity_decay_3w": 0.05,
                "sentiment_negative_ratio": 0.05,
                "commission_velocity_30d": 0.20,
                "competitor_mention_flag": 0.0,
            },
        ]
    )

    scores = model.predict_30d_hazard(df_test)
    assert len(scores) == 2
    assert "hazard_probability_30d" in scores.columns

    high_prob = scores.loc[scores["partner_id"] == "TEST-HIGH", "hazard_probability_30d"].iloc[0]
    low_prob = scores.loc[scores["partner_id"] == "TEST-LOW", "hazard_probability_30d"].iloc[0]

    assert 0.0 <= high_prob <= 1.0
    assert 0.0 <= low_prob <= 1.0
    assert high_prob > low_prob, f"Expected high_prob ({high_prob}) > low_prob ({low_prob})"
