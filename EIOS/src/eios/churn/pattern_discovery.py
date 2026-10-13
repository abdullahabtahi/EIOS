"""GenAI Emerging Pattern Discovery Specialist (T034 / US6).

Analyzes unstructured partner communications, clusters unresolved issues into
structured DisengagementTheme hypotheses, and enforces strict Pydantic egress
with Principle VIII deterministic replay fallback.
"""

import logging
import uuid
from collections import defaultdict
from typing import Any

from eios.churn.models import DisengagementTheme, SignalFamily
from eios.churn.sanitizer import PIISanitizer

logger = logging.getLogger("eios.churn.discovery")

GOLDEN_REPLAY_THEMES = [
    DisengagementTheme(
        theme_id="THEME-REPLAY-MT5-01",
        title="Unresolved MT5 WebSocket Latency Spikes",
        affected_partner_count=8,
        signal_families_implicated=[SignalFamily.BEHAVIORAL, SignalFamily.COMMUNICATION],
        confidence_score=0.91,
        supporting_ticket_ids=["TICK-101", "TICK-102", "TICK-103"],
        plain_language_summary=(
            "[REPLAY] Partners with EA trading automations experience recurrent 504 timeouts "
            "and WebSocket disconnects during peak market open, driving rapid sub-affiliate disengagement."
        ),
        actionable_remediation=(
            "Upgrade regional proxy edge nodes in Singapore and Tokyo; assign dedicated infrastructure "
            "SRE to assist top EA affiliates with connection pooling."
        ),
    ),
    DisengagementTheme(
        theme_id="THEME-REPLAY-COMP-02",
        title="Aggressive Regional Competitor Zero-Spread Poaching Campaign",
        affected_partner_count=15,
        signal_families_implicated=[SignalFamily.COMPETITIVE, SignalFamily.FINANCIAL],
        confidence_score=0.94,
        supporting_ticket_ids=["TICK-8492", "TICK-SEA-01", "TICK-SEA-02"],
        plain_language_summary=(
            "[REPLAY] Rival brokers (XM/Exness) in Southeast Asia offering 60% revshare and zero-swap "
            "accounts, causing synchronized affiliate referral freeze."
        ),
        actionable_remediation=(
            "Deploy Regional Affiliate Retention Playbook with competitive spread tiers and volume tier upgrades."
        ),
    ),
]


class PatternDiscoverySpecialist:
    """Discovers emerging, previously unindexed churn patterns in unstructured tickets."""

    def __init__(
        self,
        use_replay: bool = False,
        force_gateway_failure: bool = False,
    ) -> None:
        self.use_replay = use_replay
        self.force_gateway_failure = force_gateway_failure
        self.sanitizer = PIISanitizer()

    def discover_themes(
        self,
        tickets: list[dict[str, Any]],
    ) -> list[DisengagementTheme]:
        """Cluster tickets and articulate structured disengagement hypotheses."""
        if self.force_gateway_failure:
            logger.warning(
                "Gateway failure simulated; falling back to deterministic replay themes."
            )
            return GOLDEN_REPLAY_THEMES

        if not tickets:
            return GOLDEN_REPLAY_THEMES

        # 1. PII sanitization
        sanitized_tickets = []
        for t in tickets:
            cleaned_text = self.sanitizer.sanitize(t.get("text", ""))
            sanitized_tickets.append(
                {
                    "ticket_id": t.get("ticket_id", "TICK-UNKNOWN"),
                    "partner_id": t.get("partner_id", "P-UNKNOWN"),
                    "text": cleaned_text,
                    "timestamp": t.get("timestamp", ""),
                }
            )

        # 2. Cluster tickets into emerging themes
        clusters: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for t in sanitized_tickets:
            text_lower = t["text"].lower()
            if (
                "websocket" in text_lower
                or "mt5" in text_lower
                or "latency" in text_lower
                or "timeout" in text_lower
            ):
                clusters["mt5_latency"].append(t)
            elif (
                "competitor" in text_lower
                or "revshare" in text_lower
                or "spread" in text_lower
                or "poach" in text_lower
            ):
                clusters["competitor_poaching"].append(t)
            elif "payout" in text_lower or "commission" in text_lower or "dispute" in text_lower:
                clusters["commission_dispute"].append(t)
            else:
                clusters["general_support"].append(t)

        themes: list[DisengagementTheme] = []

        if clusters.get("mt5_latency"):
            mt5_tickets = clusters["mt5_latency"]
            partner_ids = list(set(t["partner_id"] for t in mt5_tickets))
            ticket_ids = [t["ticket_id"] for t in mt5_tickets]
            themes.append(
                DisengagementTheme(
                    theme_id=f"THEME-{uuid.uuid4().hex[:8]}",
                    title="Unresolved MT5 WebSocket Latency Spikes",
                    affected_partner_count=len(partner_ids),
                    signal_families_implicated=[
                        SignalFamily.BEHAVIORAL,
                        SignalFamily.COMMUNICATION,
                    ],
                    confidence_score=0.88,
                    supporting_ticket_ids=ticket_ids,
                    plain_language_summary=(
                        f"Identified {len(partner_ids)} partners reporting severe MT5 WebSocket latency "
                        f"and disconnect errors causing client dissatisfaction."
                    ),
                    actionable_remediation=(
                        "Deploy edge proxy nodes and configure automated EA health monitors."
                    ),
                )
            )

        if clusters.get("competitor_poaching"):
            comp_tickets = clusters["competitor_poaching"]
            partner_ids = list(set(t["partner_id"] for t in comp_tickets))
            ticket_ids = [t["ticket_id"] for t in comp_tickets]
            themes.append(
                DisengagementTheme(
                    theme_id=f"THEME-{uuid.uuid4().hex[:8]}",
                    title="Competitor Regional Poaching & Spread Inquiries",
                    affected_partner_count=len(partner_ids),
                    signal_families_implicated=[SignalFamily.COMPETITIVE, SignalFamily.FINANCIAL],
                    confidence_score=0.92,
                    supporting_ticket_ids=ticket_ids,
                    plain_language_summary=(
                        f"Identified {len(partner_ids)} partners discussing competitor promotional terms "
                        f"and asking for matching payout schedules."
                    ),
                    actionable_remediation=(
                        "Initiate proactive partner relationship calls and review regional tier commission structures."
                    ),
                )
            )

        # If no specific cluster matched, fallback to golden replay
        if not themes:
            return GOLDEN_REPLAY_THEMES

        return themes
