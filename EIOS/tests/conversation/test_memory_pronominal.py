"""Tests for pronominal resolution and entity anchors across conversation turns (F018, T016)."""

import pytest
from eios.conversation.memory import SessionMemoryManager


def test_session_memory_registers_and_resolves_entity_anchors():
    mem = SessionMemoryManager(session_id="sess_mem_01")

    # Turn 1: User mentions entity AP-1029
    t1_query = "What is the churn hazard probability for partner AP-1029?"
    mem.register_turn_entities(turn_index=1, query=t1_query, extracted_entities={"partner": "AP-1029"})

    assert mem.get_active_entity_anchor() == "AP-1029"

    # Turn 2: User uses pronoun "them" / "their"
    t2_query = "What retention playbook should we deploy for them?"
    resolved_query = mem.resolve_pronominal_references(t2_query)

    assert "AP-1029" in resolved_query


def test_session_memory_switches_anchor_on_new_entity():
    mem = SessionMemoryManager(session_id="sess_mem_02")
    mem.register_turn_entities(turn_index=1, query="Check account CR84920", extracted_entities={"account": "CR84920"})
    assert mem.get_active_entity_anchor() == "CR84920"

    mem.register_turn_entities(turn_index=2, query="Now switch to P-882", extracted_entities={"partner": "P-882"})
    assert mem.get_active_entity_anchor() == "P-882"
