"""Partner facts the workstation service holds for one story partner only. [ILLUSTRATIVE]

`PartnerWorkstationService` returns the referral tree and the retention deals for whatever partner id it is
given. These sets say which partners that content is true for, so a deal or a ring is never attached to
another partner. Messages are fixture text standing in for the partner communications feed (spec 025).
"""

from datetime import UTC, datetime

from eios.cockpit.partner_readmodel import PartnerMessage

STORY_PARTNER = (
    "PTR-882"  # the partner the referral tree, deals and messages describe (alias AP-1029)
)


MESSAGES: dict[str, list[PartnerMessage]] = {
    STORY_PARTNER: [
        PartnerMessage(
            "COMM-882-1",
            "TELEGRAM",
            "NEGATIVE",
            "rival_offer",
            datetime(2026, 10, 9, 11, 2, tzinfo=UTC),
            "A rival broker is offering my sub-affiliates a higher revenue share and tighter spreads.",
        ),
        PartnerMessage(
            "COMM-882-2",
            "EMAIL",
            "NEGATIVE",
            "payout_delay",
            datetime(2026, 10, 11, 8, 40, tzinfo=UTC),
            "Two payout tickets from last week are still unresolved and my clients keep asking.",
        ),
    ]
}
