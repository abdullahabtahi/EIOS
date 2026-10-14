"""What the tool port and the workstation routes need from a partner read model (spec 032 FR-007).

Two planes satisfy it: `PartnerWorkstationService` (hand-written fixtures, detail for one story partner) and the
engine-backed service over the seeded partner world, which has detail for every partner it scores.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from eios.cockpit.partner import ChurnRadarScatter, RetentionPlaybookDeal


@dataclass(frozen=True)
class PartnerMessage:
    message_id: str
    channel: str
    sentiment: str
    topic: str
    received_at: datetime
    text: str


class PartnerReadModel(Protocol):
    def get_churn_radar_scatter(self) -> ChurnRadarScatter: ...

    def get_partner_referral_tree(self, partner_id: str = ...) -> dict[str, Any]: ...

    def get_retention_playbooks(self, partner_id: str = ...) -> list[RetentionPlaybookDeal]: ...

    def has_detail(self, partner_id: str) -> bool:
        """Whether deals, integrity evidence and messages are loaded for this partner."""
        ...

    def get_messages(self, partner_id: str) -> list[PartnerMessage]: ...
