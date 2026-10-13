"""Tests for Compliance Priority Hierarchy (Principle VII, T027)."""

from eios.conversation.models import BlackboardState, SpecialistRoute
from eios.conversation.supervisor import ConversationalSupervisor


def test_compliance_priority_hierarchy_suppresses_commercial_rebate_on_aml_alert():
    """When an AML discrepancy alert is active, compliance hold blocks commercial retention actions."""
    sup = ConversationalSupervisor()
    state = BlackboardState(
        next_agent="supervisor",
        active_route=SpecialistRoute.PARTNER_RETENTION,
        compliance_hold=True,
    )
    # The supervisor must evaluate priority hierarchy: AML / Compliance preempts commercial actions
    next_node = sup.evaluate_priority_transition(state)
    assert next_node == "governance_compliance"
