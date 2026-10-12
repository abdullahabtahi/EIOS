"""PII Sanitization Pre-processor for Unstructured Partner Communications (T033 / US6).

Guarantees no raw Personally Identifiable Information (PII) is transmitted to external
LLM APIs or logged, preserving enterprise data privacy and security.
"""

import re


class PIISanitizer:
    """Pre-processor sanitizing PII from unstructured text before LLM analysis."""

    def __init__(self) -> None:
        self.email_pattern = re.compile(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
        )
        self.ip_pattern = re.compile(
            r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"
        )
        self.phone_pattern = re.compile(
            r"(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4})\b"
        )
        self.card_pattern = re.compile(
            r"\b(?:\d{4}[-\s]?){3}\d{4}\b"
        )
        self.account_pattern = re.compile(
            r"\b\d{8,16}\b"
        )

    def sanitize(self, text: str) -> str:
        """Sanitizes PII tokens in text by replacing with standard redacted placeholders."""
        if not text:
            return ""

        cleaned = self.email_pattern.sub("[REDACTED_EMAIL]", text)
        cleaned = self.ip_pattern.sub("[REDACTED_IP]", cleaned)
        cleaned = self.phone_pattern.sub("[REDACTED_PHONE]", cleaned)
        cleaned = self.card_pattern.sub("[REDACTED_PAYMENT]", cleaned)
        cleaned = self.account_pattern.sub("[REDACTED_ACCOUNT]", cleaned)

        return cleaned
