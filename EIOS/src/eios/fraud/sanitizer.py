"""Semantic Egress Gate and PII Sanitizer for Partner Fraud Briefings (T007).

Authoritative References:
- specs/009-partner-fraud/spec.md (FR-017)
- .specify/memory/constitution.md (Principle IV)

Guarantees:
1. Redacts raw PII (emails, IPs, phones, payment instruments) while preserving
   canonical pseudonymized tokens like tok_id_cluster_<hex16>.
2. Sanitizes inflammatory accusations into objective compliance inquiry terminology
   suitable for regulatory audits and dual four-eyes review dossiers.
"""

import re


class FraudComplianceSanitizer:
    """Sanitizes outgoing narrative summaries and briefings for legal and compliance safety."""

    def __init__(self) -> None:
        self.email_pattern = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
        # Match raw IPs but do not match tokenized hashes like tok_id_cluster_...
        self.ip_pattern = re.compile(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b")
        self.phone_pattern = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4})\b")
        self.card_pattern = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")

        # Semantic Egress Gate vocabulary mappings
        self.inflammatory_mappings: list[tuple[re.Pattern, str]] = [
            (re.compile(r"\b(?:criminal ring|crime syndicate)\b", re.IGNORECASE), "coordinated account cluster"),
            (re.compile(r"\b(?:fraudsters?|scammers?|criminals?)\b", re.IGNORECASE), "correlated participants"),
            (re.compile(r"\b(?:stolen commissions?|looted funds?|scammed money)\b", re.IGNORECASE), "unearned incentive volume"),
            (re.compile(r"\b(?:guilty of fraud|blatant theft)\b", re.IGNORECASE), "confirmed anomalous correlation"),
            (re.compile(r"\b(?:illegal operation|criminal scheme)\b", re.IGNORECASE), "high-risk syndication pattern"),
            (re.compile(r"\b(?:money launderers?)\b", re.IGNORECASE), "entities under compliance inquiry"),
        ]

    def sanitize(self, text: str) -> str:
        """Sanitize text for PII and replace inflammatory allegations with objective terms."""
        if not text:
            return ""

        # 1. Redact raw PII
        cleaned = self.email_pattern.sub("[REDACTED_EMAIL]", text)
        cleaned = self.ip_pattern.sub("[REDACTED_IP]", cleaned)
        cleaned = self.phone_pattern.sub("[REDACTED_PHONE]", cleaned)
        cleaned = self.card_pattern.sub("[REDACTED_PAYMENT]", cleaned)

        # 2. Apply semantic egress gate
        for pattern, replacement in self.inflammatory_mappings:
            cleaned = pattern.sub(replacement, cleaned)

        return cleaned
