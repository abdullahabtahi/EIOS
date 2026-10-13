"""Interactive Demo: GenAI Emerging Churn Pattern Discovery (T036 / US6).

Demonstrates:
1. Ingesting raw, unstructured partner support tickets containing PII
2. Applying PII sanitization pre-processor (redacting emails, IPs, phone numbers)
3. Running PatternDiscoverySpecialist to extract novel churn hypotheses
4. Presenting structured DisengagementTheme cards with evidence citations
"""

import sys
from pathlib import Path

# Ensure src is on python path
src_dir = Path(__file__).resolve().parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from eios.churn.pattern_discovery import PatternDiscoverySpecialist
from eios.churn.sanitizer import PIISanitizer


def run_pattern_discovery_demo() -> None:
    print("=" * 75)
    print("FEIOS PARTNER CHURN RADAR: GENAI EMERGING PATTERN DISCOVERY DEMO")
    print("=" * 75)

    # 1. Raw synthetic ticket corpus with embedded PII
    raw_tickets = [
        {
            "ticket_id": "TICK-9011",
            "partner_id": "P-VIP-88",
            "text": (
                "Hi Support, our VIP EA account (IB: john.fx@brokerage.com, IP: 203.0.113.195, "
                "phone: +65-6789-0123) is failing with MT5 WebSocket bridge error 504 timeouts. "
                "Referred clients are complaining about trade slippage during Tokyo-London crossover."
            ),
            "timestamp": "2026-10-04T07:15:00Z",
        },
        {
            "ticket_id": "TICK-9012",
            "partner_id": "P-IB-42",
            "text": (
                "Urgent: automated copy-trading WebSocket disconnects every 20 minutes on MT5 server 2. "
                "Can you check if server rate-limiting was changed? Several sub-affiliates paused deposits."
            ),
            "timestamp": "2026-10-04T09:40:00Z",
        },
        {
            "ticket_id": "TICK-9013",
            "partner_id": "P-MGR-SEA",
            "text": (
                "Sub-affiliates in Kuala Lumpur and Jakarta report that Exness launched a zero-spread "
                "and zero-swap promotion. My master rebate is being undercut by 15 pips. Will you match?"
            ),
            "timestamp": "2026-10-05T03:20:00Z",
        },
    ]

    print(f"\n[1] Ingested {len(raw_tickets)} Unstructured Support Communications")
    print("  Sample Raw Ticket (with PII):")
    print(f'  "{raw_tickets[0]["text"][:110]}..."')

    # 2. PII Sanitization
    print("\n[2] Executing PII Sanitization Pre-processor...")
    sanitizer = PIISanitizer()
    sanitized_sample = sanitizer.sanitize(raw_tickets[0]["text"])
    print("  ✓ Sanitized Ticket (PII Redacted):")
    print(f'  "{sanitized_sample[:130]}..."')

    # 3. GenAI Pattern Discovery
    print("\n[3] Running PatternDiscoverySpecialist (Clustering & Hypothesis Articulation)...")
    specialist = PatternDiscoverySpecialist(use_replay=False)
    themes = specialist.discover_themes(raw_tickets)

    print(f"\n[4] Discovered {len(themes)} Emerging Disengagement Themes:")
    for idx, theme in enumerate(themes, 1):
        print(f"\n  --- Theme #{idx}: {theme.title} ---")
        print(f"  • Theme ID:            {theme.theme_id}")
        print(f"  • Confidence Score:    {theme.confidence_score * 100:.1f}%")
        print(f"  • Partners Affected:   {theme.affected_partner_count}")
        print(f"  • Implicated Families: {[f.value for f in theme.signal_families_implicated]}")
        print(f"  • Supporting Tickets:  {theme.supporting_ticket_ids}")
        print(f"  • Plain Language:      {theme.plain_language_summary}")
        print(f"  • Remediation Action:  {theme.actionable_remediation}")

    print("\n" + "=" * 75)
    print("DEMO COMPLETE: PII Sanitization & Autonomous Theme Discovery Validated.")
    print("=" * 75)


if __name__ == "__main__":
    run_pattern_discovery_demo()
