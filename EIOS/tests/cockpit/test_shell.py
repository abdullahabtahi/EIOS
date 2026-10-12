"""Unit tests for Tripartite Common Operational Picture (COP) Shell Presenter and Session RBAC."""

import pytest
from eios.cockpit.governance_shelf import GovernedActionShelf
from eios.cockpit.session import OperatorRole, SessionManager, WorkstationTab
from eios.cockpit.shell import CockpitShellPresenter, TripartiteLayoutConfig


def test_cockpit_shell_presenter_rendering():
    mgr = SessionManager()
    session = mgr.create_session(operator_id="officer_alice", role=OperatorRole.AML_INVESTIGATOR)
    shelf = GovernedActionShelf()
    presenter = CockpitShellPresenter(session_manager=mgr, action_shelf=shelf)

    view = presenter.render_workstation_view(session_id=session.session_id)

    assert view["active_tab"] == WorkstationTab.AML_TRIAGE_DOSSIER.value
    assert view["layout"]["is_pure_light_mode"] is True
    assert view["layout"]["left_rail_width_px"] == 320
    assert view["layout"]["center_dossier_width_px"] == 560
    assert view["layout"]["right_canvas_min_width_px"] == 640
    assert view["session"]["operator_id"] == "officer_alice"
    assert view["session"]["role"] == "AML_INVESTIGATOR"
    assert isinstance(view["governed_action_shelf"], list)


def test_cockpit_shell_session_not_found():
    presenter = CockpitShellPresenter()
    with pytest.raises(KeyError, match="Session non_existent_session not found"):
        presenter.render_workstation_view(session_id="non_existent_session")


def test_session_rbac_switching_and_touch():
    mgr = SessionManager()
    session = mgr.create_session(operator_id="lead_cfo", role=OperatorRole.EXECUTIVE)

    # Executive can switch across all tabs
    updated = mgr.switch_tab(session.session_id, WorkstationTab.AML_TRIAGE_DOSSIER)
    assert updated.active_tab == WorkstationTab.AML_TRIAGE_DOSSIER

    # Update filters
    with_filters = mgr.update_filters(session.session_id, {"severity": "CRITICAL"})
    assert with_filters.applied_filters["severity"] == "CRITICAL"

    # AML Investigator cannot switch to Data Ops Board
    aml_session = mgr.create_session(operator_id="aml_investigator_bob", role=OperatorRole.AML_INVESTIGATOR)
    with pytest.raises(PermissionError, match="does not have access"):
        mgr.switch_tab(aml_session.session_id, WorkstationTab.DATA_OPS_BOARD)
