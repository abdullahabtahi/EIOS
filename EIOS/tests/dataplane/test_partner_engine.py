"""The partner engines over the seeded world (spec 032 FR-004 to FR-006): measured against what was planted."""

from datetime import timedelta

from eios.dataplane import partner_engine
from eios.dataplane.partner_engine import PartnerSnapshot, expected_days_to_churn


def test_quality_against_the_planted_truth(partner_snapshot: PartnerSnapshot) -> None:
    """Floors under the measured values in spec 032; a regression in any engine shows here."""
    q = partner_snapshot.quality
    assert q.partners == 240
    assert q.hazard_auc >= 0.95
    assert q.precision_at_k >= 0.8
    assert q.seasonal_false_alarms == 0 < q.seasonal_partners
    assert q.cohort_found and q.false_cohorts == 0
    assert q.pairs_found == q.pairs_planted and q.false_pairs == 0


def test_hazard_is_scored_at_three_dates_without_seeing_the_future(
    partner_snapshot: PartnerSnapshot,
) -> None:
    world = partner_snapshot.world
    assert set(partner_snapshot.history) == {14, 30}
    cutoff = world.config.as_of.date() - timedelta(days=30)
    hs = partner_engine._load(world, cutoff)
    latest = hs.get_cursor().execute("SELECT max(date) FROM partner_engagement_signals").fetchone()
    hs.close()
    assert latest is not None and latest[0] == cutoff
    past = partner_snapshot.history[30]["hazard_probability_30d"]
    now = partner_snapshot.scored["hazard_probability_30d"]
    churners = list(world.truth.churners())
    assert (
        now[churners].mean() > past[churners].mean()
    )  # risk built up as the planted drivers started


def test_every_partner_has_an_attribution_across_the_five_signal_families(
    partner_snapshot: PartnerSnapshot,
) -> None:
    for contributions in partner_snapshot.contributions.values():
        assert len(contributions) == 5


def test_days_to_churn_falls_as_hazard_rises() -> None:
    days = [expected_days_to_churn(h) for h in (0.01, 0.2, 0.5, 0.9, 0.999)]
    assert days == sorted(days, reverse=True)
    assert days[0] == 365 and days[-1] >= 1
