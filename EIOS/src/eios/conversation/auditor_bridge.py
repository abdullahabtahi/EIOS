"""Metric Auditor Gate bridge with legal citation normalization and KPI isolation (F018, T007)."""

from __future__ import annotations

import json
import re
import string
from datetime import UTC, datetime
from typing import Any

from eios.conversation.models import AuditorRecord, AuditorStatus
from eios.ontology.auditor.gate import MetricAuditorGate

STATUTORY_PATTERNS = [
    re.compile(r"\b\d{1,3}\s*CFR\s*§?\s*\d+(?:\.\d+)?", re.IGNORECASE),
    re.compile(r"\b\d{1,3}\s*U\.?S\.?C\.?\s*§?\s*\d+(?:\([a-zA-Z0-9]+\))*", re.IGNORECASE),
    re.compile(r"\b(?:Section|Sec\.)\s*\d+(?:\([a-zA-Z0-9]+\))*", re.IGNORECASE),
    re.compile(r"\b(?:Form|FinCEN\s*Form)\s*\d+", re.IGNORECASE),
    re.compile(r"\bFATF\s*(?:Recommendation|Rec\.)\s*\d+", re.IGNORECASE),
    re.compile(r"\bSR\s*\d{1,2}-\d{1,2}\b"),  # Federal Reserve supervisory letters, e.g. SR 11-7
]

# Dates, timestamps and explicit version labels carry digits but are not business metrics. The patterns
# are deliberately narrow: an ISO date or datetime, an HH:MM:SS clock time, and a `v`-prefixed or
# `version`-labelled dotted version. A bare ratio such as 3:20 or a decimal such as 2.5 stays auditable.
NON_METRIC_PATTERNS = [
    re.compile(
        r"\b\d{4}-\d{2}-\d{2}(?:[T ]\d{1,2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:\s?(?:UTC|Z)|[+-]\d{2}:?\d{2})?)?"
    ),
    re.compile(r"\b\d{1,2}:\d{2}:\d{2}(?:\.\d+)?(?:\s?(?:UTC|Z))?"),
    re.compile(r"\bv\d+(?:\.\d+){1,3}\b", re.IGNORECASE),
    re.compile(r"\bversion\s+\d+(?:\.\d+){1,3}\b", re.IGNORECASE),
]

# Matches any identifier-shaped token containing letters and digits like CR84920, AP1029, Tier1, Q3
ALPHANUMERIC_IDENTIFIER_PATTERN = re.compile(r"\b[A-Za-z0-9_]*[A-Za-z]+[-_]?[0-9]+[A-Za-z0-9_]*\b")

# An identifier-shaped token is exempt from the numeric audit only when it is grounded (a tool produced it or
# the operator typed it) or is a short structural code such as Q3, P1 or Tier1. Everything else keeps its
# digits visible to the gate, otherwise "USD9999999" or "x500" would launder an arbitrary figure past Principle I.
MAX_UNGROUNDED_IDENTIFIER_DIGITS = 2
CURRENCY_OR_UNIT_PREFIX = re.compile(
    r"^(?:USDT?|EUR|GBP|JPY|AUD|CAD|CHF|CNY|BTC|ETH|BPS|PCT)(?=\d)", re.IGNORECASE
)


class ConversationAuditorBridge:
    """Connects the conversational reasoning mesh to the Metric Auditor Gate (Principle I)."""

    def __init__(self, auditor: MetricAuditorGate | None = None) -> None:
        self.auditor = auditor or MetricAuditorGate(relative_tolerance=0.01)

    def extract_statutory_citations(self, text: str) -> list[str]:
        """Extracts and normalizes legal and regulatory citations to exempt them from arithmetic audits."""
        exemptions = []
        for pat in STATUTORY_PATTERNS:
            for match in pat.finditer(text):
                exemptions.append(match.group(0))
        return exemptions

    @staticmethod
    def _evidence_text(tool_trace: list[dict[str, Any]], query: str) -> str:
        """Lower-cased text of everything an identifier may legitimately come from: tool outputs and the query."""
        outputs = json.dumps([call.get("output", {}) for call in tool_trace], default=str)
        return f"{outputs}\n{query}".lower()

    @staticmethod
    def _is_exempt_identifier(token: str, evidence: str) -> bool:
        if token.lower() in evidence:
            return True
        if CURRENCY_OR_UNIT_PREFIX.match(token):
            return False
        return sum(ch.isdigit() for ch in token) <= MAX_UNGROUNDED_IDENTIFIER_DIGITS

    def audit_turn(
        self,
        narrative_text: str,
        tool_trace: list[dict[str, Any]],
        trace_id: str = "tr_turn",
        query: str = "",
    ) -> AuditorRecord:
        """Audits an agent turn against tool outputs, exempting statutory citations and grounded identifiers."""
        exemptions = self.extract_statutory_citations(narrative_text)

        # Mask statutory citations with pure alphabet tokens (no digits!)
        masked_text = narrative_text
        letters = string.ascii_uppercase
        for idx, citation in enumerate(exemptions):
            tag = letters[idx % len(letters)] * 4
            masked_text = masked_text.replace(citation, f"STATUTORYMASK{tag}")

        # Mask dates, timestamps and version labels (pure-letter tokens, no digits)
        for idx, pat in enumerate(NON_METRIC_PATTERNS):
            masked_text = pat.sub(f"NONMETRICMASK{letters[idx % len(letters)] * 2}", masked_text)

        # Mask grounded or short structural codes (CR84920 from a tool, Q3, Tier1) so their digits are not read as
        # KPIs. One pass, so a token that is a substring of another cannot leave digits behind.
        evidence = self._evidence_text(tool_trace, query)
        identifier_count = 0

        def mask_identifier(match: re.Match[str]) -> str:
            nonlocal identifier_count
            if not self._is_exempt_identifier(match.group(0), evidence):
                return match.group(0)
            tag = letters[identifier_count % len(letters)] * 3
            identifier_count += 1
            return f"IDENTIFIERMASK{tag}"

        masked_text = ALPHANUMERIC_IDENTIFIER_PATTERN.sub(mask_identifier, masked_text)

        # Run verification through the ontology gate
        audit_res = self.auditor.verify_response(masked_text, tool_trace, trace_id=trace_id)

        status = AuditorStatus.PASS if audit_res.passed else AuditorStatus.BLOCKED

        return AuditorRecord(
            passed=audit_res.passed,
            status=status,
            verified_numerical_anchors=audit_res.anchored_numbers,
            unanchored_tokens=audit_res.untraceable_numbers,
            exempted_statutory_citations=exemptions,
            relative_tolerance=self.auditor.relative_tolerance,
            audited_at=datetime.now(UTC),
            trace_id=trace_id,
        )

    def scan_egress_response(
        self, response_text: str, evidence_ledger: list[dict[str, Any]]
    ) -> str:
        """Convenience method returning safe narrative or refusal message."""
        record = self.audit_turn(response_text, evidence_ledger)
        if not record.passed:
            return "I cannot provide a response because the metric auditor detected unanchored numerical claims."
        return response_text
