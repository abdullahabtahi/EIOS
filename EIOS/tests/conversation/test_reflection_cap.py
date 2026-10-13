"""Tests for bounded deliberation and reflection cycle cap (Principle VII, T028)."""

from eios.conversation.models import BlackboardState
from eios.conversation.supervisor import ConversationalSupervisor


def test_supervisor_halts_after_3_reflection_cycles():
    sup = ConversationalSupervisor()
    state = BlackboardState(
        next_agent="aml_investigator",
        reflection_cycles=3,  # Already reached cap
    )
    # At cap, supervisor must transition to egress synthesis rather than re-querying
    next_node = sup.evaluate_reflection_transition(state)
    assert next_node == "egress_synthesis"
