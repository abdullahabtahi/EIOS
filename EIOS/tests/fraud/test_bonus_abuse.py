"""Unit tests for Client Quality & Bonus Abuse Scorer (T019 / US3).

Authoritative References:
- docs/brief/fraud [BRIEF fraud]
- specs/009-partner-fraud/spec.md (US3, FR-006, FR-007)
- specs/009-partner-fraud/research.md §3
"""

from eios.fraud.bonus_abuse import BonusAbuseScorer


def test_bonus_abuse_scorer_flags_rapid_withdrawal_syndicate(
    synthetic_client_lifecycles: list[dict],
) -> None:
    scorer = BonusAbuseScorer()
    profile = scorer.score_partner_portfolio("P-ABUSE-100", synthetic_client_lifecycles)

    assert profile.partner_id == "P-ABUSE-100"
    assert profile.total_referred_clients == 100
    assert profile.fast_withdrawal_count_72h >= 80
    assert profile.client_quality_index < 0.20
    assert profile.abuse_probability >= 0.80
    assert profile.status == "HIGH_BONUS_ABUSE_RISK"
    assert profile.cpa_bounty_collected_usd > 0


def test_bonus_abuse_scorer_passes_healthy_organic_portfolio(
    synthetic_client_lifecycles: list[dict],
) -> None:
    scorer = BonusAbuseScorer()
    profile = scorer.score_partner_portfolio("P-ORGANIC-50", synthetic_client_lifecycles)

    assert profile.partner_id == "P-ORGANIC-50"
    assert profile.total_referred_clients == 50
    assert profile.fast_withdrawal_count_72h == 0
    assert profile.client_quality_index >= 0.70
    assert profile.abuse_probability <= 0.30
    assert profile.status == "NORMAL"
