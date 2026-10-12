"""Metric Auditor Gate bridge with legal citation normalization and KPI isolation (F018, T007)."""

from __future__ import annotations

import re
import string
from datetime import UTC, datetime
from typing import Any, Dict, List
from eios.conversation.models import AuditorRecord, AuditorStatus
from eios.ontology.auditor.gate import MetricAuditorGate


STATUTORY_PATTERNS = [
    re.compile(r"\b\d{1,3}\s*CFR\s*§?\s*\d+(?:\.\d+)?", re.IGNORECASE),
    re.compile(r"\b\d{1,3}\s*U\.?S\.?C\.?\s*§?\s*\d+(?:\([a-zA-Z0-9]+\))*", re.IGNORECASE),
    re.compile(r"\b(?:Section|Sec\.)\s*\d+(?:\([a-zA-Z0-9]+\))*", re.IGNORECASE),
    re.compile(r"\b(?:Form|FinCEN\s*Form)\s*\d+", re.IGNORECASE),
    re.compile(r"\bFATF\s*(?:Recommendation|Rec\.)\s*\d+", re.IGNORECASE),
]

# Matches any identifier code containing letters and digits like CR84920, AP1029, Tier1, VIP_Spread_Rebate_Tier1
ALPHANUMERIC_IDENTIFIER_PATTERN = re.compile(r"\b[A-Za-z0-9_]*[A-Za-z]+[-_]?[0-9]+[A-Za-z0-9_]*\b")


class ConversationAuditorBridge:
    """Connects the conversational reasoning mesh to the Metric Auditor Gate (Principle I)."""

    def __init__(self, auditor: MetricAuditorGate | None = None) -> None:
        self.auditor = auditor or MetricAuditorGate(relative_tolerance=0.01)

    def extract_statutory_citations(self, text: str) -> List[str]:
        """Extracts and normalizes legal and regulatory citations to exempt them from arithmetic audits."""
        exemptions = []
        for pat in STATUTORY_PATTERNS:
            for match in pat.finditer(text):
                exemptions.append(match.group(0))
        return exemptions

    def audit_turn(
        self,
        narrative_text: str,
        tool_trace: List[Dict[str, Any]],
        trace_id: str = "tr_turn",
    ) -> AuditorRecord:
        """Audits an agent turn against tool outputs while exempting statutory citations and identifier codes."""
        exemptions = self.extract_statutory_citations(narrative_text)

        # Mask statutory citations with pure alphabet tokens (no digits!)
        masked_text = narrative_text
        letters = string.ascii_uppercase
        for idx, citation in enumerate(exemptions):
            tag = letters[idx % len(letters)] * 4
            masked_text = masked_text.replace(citation, f"STATUTORYMASK{tag}")

        # Mask alphanumeric codes like Tier1, CR84920, P-882 so identifier digits aren't treated as financial KPIs
        for idx, match in enumerate(ALPHANUMERIC_IDENTIFIER_PATTERN.finditer(masked_text)):
            matched_code = match.group(0)
            tag = letters[idx % len(letters)] * 3
            masked_text = masked_text.replace(matched_code, f"IDENTIFIERMASK{tag}")

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

    def scan_egress_response(self, response_text: str, evidence_ledger: List[Dict[str, Any]]) -> str:
        """Convenience method returning safe narrative or refusal message."""
        record = self.audit_turn(response_text, evidence_ledger)
        if not record.passed:
            return "I cannot provide a response because the metric auditor detected unanchored numerical claims."
        return response_text
