"""Tests for hierarchical supervisor intent classification and routing (F018, T026)."""

from eios.conversation.models import SpecialistRoute
from eios.conversation.supervisor import ConversationalSupervisor


def test_supervisor_routes_aml_queries():
    sup = ConversationalSupervisor()
    route = sup.classify_route("Look up account CR84920 and check for mule activity")
    assert route == SpecialistRoute.AML_INVESTIGATOR


def test_supervisor_routes_partner_churn_queries():
    sup = ConversationalSupervisor()
    route = sup.classify_route("Partner AP-1029 has dropped volume after competitor spread cut")
    assert route == SpecialistRoute.PARTNER_RETENTION


def test_supervisor_routes_compliance_queries():
    sup = ConversationalSupervisor()
    route = sup.classify_route(
        "Show me the audit proof for WORM compliance under FinCEN guidelines"
    )
    assert route == SpecialistRoute.GOVERNANCE_COMPLIANCE


def test_supervisor_routes_executive_synthesis_default():
    sup = ConversationalSupervisor()
    route = sup.classify_route("Summarize overall brokerage KPI health and active alerts")
    assert route == SpecialistRoute.EXECUTIVE_SYNTHESIS


def test_supervisor_build_graph_compilation_and_transitions():
    sup = ConversationalSupervisor()
    graph = sup.build_graph()
    assert graph is not None

    from eios.conversation.models import BlackboardState, OperatorRole

    state = BlackboardState(
        session_id="sess_1",
        user_role=OperatorRole.EXECUTIVE,
        compliance_hold=True,
    )
    assert sup.evaluate_priority_transition(state) == "governance_compliance"

    state.compliance_hold = False
    state.reflection_cycles = 3
    assert sup.evaluate_reflection_transition(state) == "egress_synthesis"

    state.reflection_cycles = 1
    assert sup.evaluate_reflection_transition(state) == "supervisor"
