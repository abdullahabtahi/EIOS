"""Unit tests for GenAI Emerging Pattern Discovery (T032 / US6)."""

from eios.churn.models import DisengagementTheme, SignalFamily
from eios.churn.pattern_discovery import PatternDiscoverySpecialist
from eios.churn.sanitizer import PIISanitizer


def test_pii_sanitization():
    """Verify PIISanitizer redacts emails, phone numbers, IP addresses, and account numbers."""
    sanitizer = PIISanitizer()
    raw_text = (
        "Client john.doe@example.com from IP 192.168.1.42 called +1-800-555-0199 "
        "regarding trade account 4829104820 and card 4532-1234-5678-9012."
    )
    cleaned = sanitizer.sanitize(raw_text)

    assert "john.doe@example.com" not in cleaned
    assert "192.168.1.42" not in cleaned
    assert "+1-800-555-0199" not in cleaned
    assert "4532-1234-5678-9012" not in cleaned
    assert "[REDACTED_EMAIL]" in cleaned
    assert "[REDACTED_IP]" in cleaned
    assert "[REDACTED_PHONE]" in cleaned


def test_pattern_discovery_clusters_unstructured_tickets():
    """Verify PatternDiscoverySpecialist clusters tickets into valid DisengagementTheme models."""
    specialist = PatternDiscoverySpecialist(use_replay=True)

    tickets = [
        {
            "ticket_id": "TICK-101",
            "partner_id": "P-01",
            "text": "MT5 WebSocket disconnects every 15 minutes during London market open. Latency is unacceptable.",
            "timestamp": "2026-10-01T08:00:00Z",
        },
        {
            "ticket_id": "TICK-102",
            "partner_id": "P-02",
            "text": "Our automated EA crashed due to MT5 WebSocket bridge timeout error 504.",
            "timestamp": "2026-10-02T09:30:00Z",
        },
        {
            "ticket_id": "TICK-103",
            "partner_id": "P-03",
            "text": "My sub-affiliates are complaining about MT5 WebSocket server lag and quote delays.",
            "timestamp": "2026-10-03T11:15:00Z",
        },
    ]

    themes = specialist.discover_themes(tickets)

    assert len(themes) >= 1
    theme = themes[0]
    assert isinstance(theme, DisengagementTheme)
    assert "MT5" in theme.title or "WebSocket" in theme.title
    assert theme.affected_partner_count >= 1
    assert (
        SignalFamily.BEHAVIORAL in theme.signal_families_implicated
        or SignalFamily.COMMUNICATION in theme.signal_families_implicated
    )
    assert theme.confidence_score >= 0.70
    assert len(theme.supporting_ticket_ids) >= 1
    assert len(theme.actionable_remediation) > 0


def test_replay_fallback_when_offline():
    """Verify Principle VIII deterministic replay fallback when LLM gateway fails."""
    specialist = PatternDiscoverySpecialist(force_gateway_failure=True)
    themes = specialist.discover_themes([])

    assert len(themes) >= 1
    assert "[REPLAY]" in themes[0].plain_language_summary
    assert themes[0].confidence_score > 0.0
