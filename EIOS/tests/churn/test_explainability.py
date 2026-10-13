"""Unit tests for feature contribution calculations and citations across 5 signal families (T014)."""

import pandas as pd

from eios.churn.explainer import ChurnSignalExplainer
from eios.churn.models import SignalFamily


def test_signal_contributions_all_families():
    """Verify that ChurnSignalExplainer calculates contributions with citations across all 5 families."""
    explainer = ChurnSignalExplainer()

    row = pd.Series(
        {
            "partner_id": "P-CHURN-DRIFT",
            "logins_recent": 12,
            "logins_prior": 20,
            "login_velocity_decay_3w": 0.40,
            "negative_tickets": 2,
            "sentiment_negative_ratio": 0.67,
            "tenure_months": 18,
            "tenure_months_log": 2.94,
            "comm_recent": 36900.0,
            "comm_prior": 45000.0,
            "commission_velocity_30d": -0.18,
            "competitor_mention_flag": 1.0,
        }
    )

    contributions = explainer.compute_contributions(row)
    assert len(contributions) == 5

    families_present = {c.signal_family for c in contributions}
    expected_families = {
        SignalFamily.BEHAVIORAL,
        SignalFamily.COMMUNICATION,
        SignalFamily.RELATIONSHIP,
        SignalFamily.FINANCIAL,
        SignalFamily.COMPETITIVE,
    }
    assert families_present == expected_families

    # Check that citations are present and properly formatted
    for c in contributions:
        assert c.citation_ref.startswith("DP"), f"Citation {c.citation_ref} must start with DP"
        assert isinstance(c.hazard_weight, float)
        assert isinstance(c.relative_delta, float)

    # Top driver should be behavioral or competitive
    top = explainer.get_top_driver(contributions)
    assert top.signal_family in [SignalFamily.BEHAVIORAL, SignalFamily.COMPETITIVE]
