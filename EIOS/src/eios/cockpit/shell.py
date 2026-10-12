"""Tripartite Common Operational Picture (COP) Shell Presenter.

Orchestrates the 3-column layout (Triage Rail, Copilot Dossier, Kinetic Canvas)
plus the bottom-docked Governed Action Shelf across all 5 persona workstations.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from eios.cockpit.tokens import INSTITUTIONAL_LIGHT_TOKENS
from eios.cockpit.session import (
    SessionManager,
    OperatorRole,
    WorkstationTab,
    WorkstationViewSession,
)
from eios.cockpit.governance_shelf import GovernedActionShelf


class TripartiteLayoutConfig(BaseModel):
    left_rail_width_px: int = 320
    center_dossier_width_px: int = 560
    right_canvas_min_width_px: int = 640
    bottom_shelf_collapsed_height_px: int = 72
    bottom_shelf_expanded_height_px: int = 360
    is_pure_light_mode: bool = True
    design_tokens: Dict[str, str] = Field(default_factory=lambda: INSTITUTIONAL_LIGHT_TOKENS)


class CockpitShellView(BaseModel):
    session: Dict[str, Any]
    layout: TripartiteLayoutConfig
    active_tab: str
    triage_column: Dict[str, Any]
    dossier_column: Dict[str, Any]
    canvas_column: Dict[str, Any]
    governed_action_shelf: List[Dict[str, Any]]


class CockpitShellPresenter:
    """Aggregates persona data into the tripartite Common Operational Picture."""

    def __init__(
        self,
        session_manager: Optional[SessionManager] = None,
        action_shelf: Optional[GovernedActionShelf] = None,
    ) -> None:
        self.session_manager = session_manager or SessionManager()
        self.action_shelf = action_shelf or GovernedActionShelf()
        self.layout_config = TripartiteLayoutConfig()

    def render_workstation_view(
        self,
        session_id: str,
        triage_data: Optional[Dict[str, Any]] = None,
        dossier_data: Optional[Dict[str, Any]] = None,
        canvas_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Renders the complete tripartite workspace view for the given session."""
        session = self.session_manager.get_session(session_id)
        if not session:
            raise KeyError(f"Session {session_id} not found")

        # Compile active staged actions in shelf
        staged_cards = [card.to_contract_dict() for card in self.action_shelf.list_cards()]

        view = CockpitShellView(
            session=session.to_contract_dict(),
            layout=self.layout_config,
            active_tab=session.active_tab.value,
            triage_column=triage_data or {"items": [], "total_count": 0, "filter_facet": "severity"},
            dossier_column=dossier_data or {"title": "Evidence Dossier", "sections": []},
            canvas_column=canvas_data or {"canvas_type": "KINETIC_GRAPH", "elements": []},
            governed_action_shelf=staged_cards,
        )
        return view.model_dump()
