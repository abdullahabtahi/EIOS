"""The seeded partner world (spec 032 FR-001 to FR-003): deterministic, labelled, and blind to its own labels."""

from datetime import timedelta

import pandas as pd
import pytest

from eios.foundry.scenarios.aml_config import STORY_PARTNER as AML_RING_PARTNER
from eios.foundry.scenarios.partner_config import NAMED, STORY_PARTNER, PartnerWorldConfig
from eios.foundry.scenarios.partner_world import PartnerWorld, build_partner_world

SMALL = PartnerWorldConfig(n_partners=80, cohort_size=6, background_accounts=60)


@pytest.fixture(scope="module")
def world() -> PartnerWorld:
    return build_partner_world(SMALL)


def test_the_same_config_builds_the_same_world(world: PartnerWorld) -> None:
    again = build_partner_world(SMALL)
    pd.testing.assert_frame_equal(world.days, again.days)
    pd.testing.assert_frame_equal(world.messages, again.messages)
    pd.testing.assert_frame_equal(world.trades, again.trades)
    assert world.truth == again.truth


def test_named_partners_keep_their_identities(world: PartnerWorld) -> None:
    roster = world.roster.set_index("partner_id")
    for named in NAMED:
        assert roster.loc[named.partner_id, "name"] == named.name
        assert roster.loc[named.partner_id, "tier"] == named.tier.value
    assert STORY_PARTNER in roster.index and AML_RING_PARTNER in roster.index
    assert len(roster) == SMALL.n_partners and roster.index.is_unique


def test_what_the_engines_read_carries_no_planted_label(world: PartnerWorld) -> None:
    assert {"driver", "onset_day", "competitor", "in_cohort"}.isdisjoint(world.roster.columns)
    assert world.truth.churners() and world.truth.seasonal()
    assert len(world.truth.cohort) == SMALL.cohort_size


def test_history_ends_at_as_of_and_nothing_is_dated_after_it(world: PartnerWorld) -> None:
    days = world.days.groupby("partner_id")["date"]
    assert (days.count() == SMALL.history_days).all()
    assert days.max().eq(SMALL.as_of.date()).all()
    assert world.messages["timestamp"].max() < pd.Timestamp(SMALL.as_of.replace(tzinfo=None))
    assert world.trades["timestamp"].min() >= SMALL.as_of - timedelta(days=14)


def test_planted_pairs_sit_under_two_sibling_affiliates_and_mirror_each_other(
    world: PartnerWorld,
) -> None:
    roster = world.roster.set_index("partner_id")
    for pair in world.truth.pairs:
        assert pair.partner_a != pair.partner_b
        assert (
            roster.loc[pair.partner_a, "parent_id"]
            == roster.loc[pair.partner_b, "parent_id"]
            == pair.master_id
        )
        a = world.trades[world.trades["account_id"] == pair.account_a]
        b = world.trades[world.trades["account_id"] == pair.account_b]
        assert len(a) == len(b) >= 10
        assert set(a["direction"]) | set(b["direction"]) == {"BUY", "SELL"}


def test_messages_name_no_real_firm(world: PartnerWorld) -> None:
    text = " ".join(world.messages["text"]).lower()
    assert "exness" not in text and " xm" not in text
