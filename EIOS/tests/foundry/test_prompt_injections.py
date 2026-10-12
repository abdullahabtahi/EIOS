"""Tests for adversarial prompt-injection test strings embedded in partner comms (FR-042, Red-Line RL-6)."""

import pytest
from eios.foundry.contracts import ContractValidator, PartnerCommsRecord
from eios.foundry.noise.prompt_injections import PromptInjectionGenerator
from eios.foundry.rng import DeterministicRNG
from eios.foundry.universe import GlobalEntityUniverse


def test_prompt_injection_embedding_in_partner_comms():
    """Confirms prompt injections are safely embedded in partner comms and pass schema validation."""
    rng = DeterministicRNG(master_seed=42)
    universe = GlobalEntityUniverse(rng=rng, client_count=100, partner_count=50)
    inj_gen = PromptInjectionGenerator(universe=universe, rng=rng)

    comms_records = inj_gen.generate_comms_with_injections(count=50)
    assert len(comms_records) == 50

    validator = ContractValidator(PartnerCommsRecord)
    validated = validator.validate_batch(comms_records)
    assert len(validated) == 50

    # Ensure adversarial prompts for RL-6 exist
    injection_signatures = [
        "IGNORE PREVIOUS INSTRUCTIONS",
        "SYSTEM PROMPT OVERRIDE",
        "DAN MODE",
        "DISREGARD ALL SAFEGUARDS",
    ]

    found_injections = [
        rec for rec in comms_records
        if any(sig.lower() in rec["body_text"].lower() for sig in injection_signatures)
    ]
    assert len(found_injections) >= 5, f"Expected at least 5 injection strings, found {len(found_injections)}"

    # Ensure bounds on body text length
    for rec in comms_records:
        assert 10 <= len(rec["body_text"]) <= 5000
