"""What the tool port and the workstation routes need from an AML read model (spec 031 FR-007).

Two planes satisfy it: `AMLWorkstationService` (hand-written fixtures for one story entity) and the engine-backed
service over the seeded world. The port holds only this protocol, so the plane is a composition-root choice.
"""

from typing import Any, Protocol

from eios.aml.case_views import PendingWithdrawal, TimelineEvent
from eios.cockpit.aml import EntityInvestigationDossier, KineticNetworkGraph, SARDraftDocument


class AmlReadModel(Protocol):
    def get_triage_queue(self, min_score: int = 50, limit: int = 10) -> list[dict[str, Any]]: ...

    def get_entity_dossier(self, entity_id: str) -> EntityInvestigationDossier: ...

    def get_kinetic_network_graph(
        self, entity_id: str, hub_threshold: int = 100
    ) -> KineticNetworkGraph: ...

    def compose_sar_draft(
        self, case_id: str = "", entity_id: str = "", investigator_id: str = ""
    ) -> SARDraftDocument: ...

    def account_ids(self) -> list[str]: ...

    def supports_detail(self, entity_id: str) -> bool: ...

    def get_alert_score(self, entity_id: str) -> int | None: ...

    def get_activity_timeline(self, entity_id: str) -> list[TimelineEvent] | None: ...

    def get_pending_withdrawal(self, entity_id: str) -> PendingWithdrawal | None: ...
