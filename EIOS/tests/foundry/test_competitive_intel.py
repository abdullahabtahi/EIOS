"""Tests for competitive market intel events with generic aliases (FR-044, SC-003)."""

import pytest
from eios.foundry.contracts import CompetitorEventRecord, ContractValidator
from eios.foundry.generators.competitive import CompetitiveDataGenerator
from eios.foundry.rng import DeterministicRNG

REAL_BROKER_BLACKLIST = [
    "etoro",
    "plus500",
    "interactive brokers",
    "robinhood",
    "xm",
    "exness",
    "oanda",
    "ig group",
]


def test_competitive_events_generic_aliases_and_schema():
    """Confirms competitor events use generic aliases (never real brokers) and pass contracts."""
    rng = DeterministicRNG(master_seed=42)
    comp_gen = CompetitiveDataGenerator(rng=rng)

    events = comp_gen.generate_events(count=30)
    assert len(events) == 30

    validator = ContractValidator(CompetitorEventRecord)
    validated = validator.validate_batch(events)
    assert len(validated) == 30

    event_types = {e.event_type for e in validated}
    assert "PAYOUT_INCREASE" in event_types
    assert "SPREAD_CUT" in event_types

    # Ensure all aliases are strictly generic aliases like "Competitor Alpha", "Competitor X"
    for e in validated:
        alias_lower = e.competitor_alias.lower()
        assert "competitor" in alias_lower or "broker_" in alias_lower
        for real_broker in REAL_BROKER_BLACKLIST:
            assert real_broker not in alias_lower
