"""Tests for churn radar time-series signals and seasonal dip hard negatives (FR-035 to FR-041)."""

from eios.foundry.contracts import ContractValidator, WeeklySignalRecord
from eios.foundry.generators.churn import ChurnDataGenerator
from eios.foundry.rng import DeterministicRNG
from eios.foundry.universe import GlobalEntityUniverse


def test_churn_signal_families_and_seasonal_dips():
    """Confirms 5 signal families, ~8% seasonal dip hard negatives recovering in 30 days, and cohort shock."""
    rng = DeterministicRNG(master_seed=42)
    universe = GlobalEntityUniverse(rng=rng, client_count=200, partner_count=100)
    churn_gen = ChurnDataGenerator(universe=universe, rng=rng)

    weekly_signals = churn_gen.generate_weekly_signals(weeks=8)
    assert len(weekly_signals) >= 100

    validator = ContractValidator(WeeklySignalRecord)
    validated = validator.validate_batch(weekly_signals)
    assert len(validated) == len(weekly_signals)

    # 1. Verify 5 signal families present
    first_sig = validated[0]
    assert hasattr(first_sig, "active_traders_count")
    assert hasattr(first_sig, "weekly_ftd_count")
    assert hasattr(first_sig, "click_to_signup_conversion")
    assert hasattr(first_sig, "average_ticket_sentiment")
    assert hasattr(first_sig, "poaching_language_flags")

    # 2. Verify ~8% seasonal dip partners with recovery
    seasonal_dips = churn_gen.get_seasonal_dip_partners()
    expected_dip_count = int(100 * 0.08)  # ~8 partners
    assert abs(len(seasonal_dips) - expected_dip_count) <= 2
    for dip in seasonal_dips:
        assert dip["recovery_days"] == 30
        assert dip["is_recovered"] is True

    # 3. Regional cohort disengagement event with lag
    cohort_shock = churn_gen.get_regional_cohort_shock()
    assert cohort_shock["region"] in ["LATAM", "APAC", "EMEA"]
    assert cohort_shock["lag_days"] == 14
    assert len(cohort_shock["affected_partners"]) >= 5
