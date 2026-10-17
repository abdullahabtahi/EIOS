"""How early the churn radar sees planted churn (the brief asks for lead time, not only an AUC today)."""

import pandas as pd
import pytest

from eios.dataplane.partner_engine import HIGH_RISK, PartnerSnapshot
from eios.dataplane.partner_lead_time import LEADS, LeadTimeRow, lead_time_report
from eios.dataplane.rank_metrics import ranking_auc


def test_report_has_a_row_per_lead_in_order(partner_snapshot: PartnerSnapshot) -> None:
    rows = lead_time_report(partner_snapshot)
    assert [r.lead_days for r in rows] == list(LEADS) == [0, 14, 30]
    assert all(isinstance(r, LeadTimeRow) for r in rows)


def test_every_figure_is_a_proportion_and_the_alert_counts_are_real(
    partner_snapshot: PartnerSnapshot,
) -> None:
    churners = partner_snapshot.world.truth.churners()
    for row in lead_time_report(partner_snapshot):
        assert 0.0 <= row.auc <= 1.0
        assert 0.0 <= row.precision_at_k <= 1.0
        assert 0.0 <= row.alert_recall <= 1.0
        assert row.alert_precision is None or 0.0 <= row.alert_precision <= 1.0
        assert row.planted_churners == len(churners)
    now = lead_time_report(partner_snapshot)[0]
    assert now.alerts == int((partner_snapshot.scored["hazard_probability_30d"] >= HIGH_RISK).sum())


def test_detection_today_and_two_weeks_ahead_keep_their_measured_floors(
    partner_snapshot: PartnerSnapshot,
) -> None:
    """Floors under the measured AUCs (0.974 now, 0.72 at 14 days) `[MEASURED]`; a change that loses ranking shows here."""
    by_lead = {r.lead_days: r for r in lead_time_report(partner_snapshot)}
    assert by_lead[0].auc >= 0.95
    assert by_lead[14].auc >= 0.65


def test_the_thirty_day_lead_is_reported_not_hidden(partner_snapshot: PartnerSnapshot) -> None:
    """The label says 'churn in 30 days', so the 30-day-ahead figure must always be in the report, whatever it is."""
    by_lead = {r.lead_days: r for r in lead_time_report(partner_snapshot)}
    assert by_lead[30].lead_days == 30 and by_lead[30].auc is not None


def test_no_alerts_means_no_precision_not_zero(partner_snapshot: PartnerSnapshot) -> None:
    """Honesty rule: a figure nothing measured is absent, never zero."""
    quiet = PartnerSnapshot(
        world=partner_snapshot.world,
        scored=partner_snapshot.scored.assign(hazard_probability_30d=0.01),
        history={
            k: v.assign(hazard_probability_30d=0.01) for k, v in partner_snapshot.history.items()
        },
        contributions=partner_snapshot.contributions,
        cohorts=partner_snapshot.cohorts,
        pairs=partner_snapshot.pairs,
        quality=partner_snapshot.quality,
    )
    rows = lead_time_report(quiet)
    assert all(r.alerts == 0 and r.alert_precision is None and r.alert_recall == 0.0 for r in rows)


def test_ranking_auc_is_chance_for_a_constant_score_and_one_for_a_perfect_one() -> None:
    ids = ["a", "b", "c", "d"]
    positives = frozenset({"a", "b"})
    assert ranking_auc(pd.Series([0.5] * 4, index=ids), positives) == pytest.approx(0.5)
    assert ranking_auc(pd.Series([0.9, 0.8, 0.2, 0.1], index=ids), positives) == pytest.approx(1.0)
    assert (
        ranking_auc(pd.Series([0.9, 0.8], index=["a", "b"]), positives) == 0.0
    )  # no negatives: not defined, not a score


def test_the_table_renders_every_lead_and_says_n_a_for_no_alerts(
    partner_snapshot: PartnerSnapshot,
) -> None:
    from dataclasses import replace

    from evals.partner.lead_time import render

    rows = lead_time_report(partner_snapshot)
    text = render((replace(rows[0], alert_precision=None), *rows[1:]))
    assert text.count("\n") == len(rows)
    assert "n/a" in text and "0d" in text and "30d" in text
