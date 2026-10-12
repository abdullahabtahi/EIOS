"""Statutory regulatory citation normalizer (Constitution Principle VII).

Authoritative References:
- specs/010-client-aml/research.md §6
- .specify/memory/constitution.md (Principles I, VII)

Prevents the Metric Auditor Gate from mistakenly flagging statutory regulatory citations
(e.g., '31 CFR 1010.410', '31 U.S.C. 5318(g)', 'Section 314(b)') as ungrounded business metrics.
"""

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class StatutoryCitation:
    raw_match: str
    normalized_code: str
    category: str
    description: str


# Canonical regex patterns for financial crime statutes and regulatory forms
STATUTORY_PATTERNS = [
    (
        re.compile(r"\b31\s*CFR\s*1010(?:\.\d+)?\b", re.IGNORECASE),
        "31_CFR_1010",
        "FEDERAL_REGULATION",
        "General Financial Recordkeeping and Reporting (FinCEN)",
    ),
    (
        re.compile(r"\b31\s*CFR\s*1020(?:\.\d+)?\b", re.IGNORECASE),
        "31_CFR_1020",
        "FEDERAL_REGULATION",
        "Rules for Banks / Broker-Dealers (FinCEN)",
    ),
    (
        re.compile(r"\b31\s*U\.S\.C\.\s*5318(?:\([a-z]\))?", re.IGNORECASE),
        "31_USC_5318",
        "FEDERAL_STATUTE",
        "Compliance, Exemptions, and Suspicious Transaction Reporting (BSA)",
    ),
    (
        re.compile(r"\b18\s*U\.S\.C\.\s*(?:1956|1957)\b", re.IGNORECASE),
        "18_USC_1956",
        "CRIMINAL_STATUTE",
        "Laundering of Monetary Instruments / Monetary Transactions in Property Derived from Unlawful Activity",
    ),
    (
        re.compile(r"\bSection\s*314(?:\([ab]\))?", re.IGNORECASE),
        "SECTION_314",
        "USA_PATRIOT_ACT",
        "Information Sharing Between Law Enforcement and Financial Institutions",
    ),
    (
        re.compile(r"\bFinCEN\s*Form\s*111\b", re.IGNORECASE),
        "FINCEN_FORM_111",
        "REGULATORY_FORM",
        "Suspicious Activity Report by Broker-Dealers",
    ),
]


class StatutoryCitationNormalizer:
    """Extracts, normalizes, and white-lists statutory regulatory citations."""

    def extract_citations(self, text: str) -> list[StatutoryCitation]:
        """Scan text and return all detected statutory references."""
        citations: list[StatutoryCitation] = []
        for pattern, norm_code, category, desc in STATUTORY_PATTERNS:
            for match in pattern.finditer(text):
                citations.append(
                    StatutoryCitation(
                        raw_match=match.group(0),
                        normalized_code=norm_code,
                        category=category,
                        description=desc,
                    )
                )
        return citations

    def normalize_text_for_audit(self, text: str) -> str:
        """Replace statutory numerical patterns with [STATUTE:<code>] tokens.
        
        This prevents numerical audit gates from parsing '1010', '5318', etc.
        as financial figures or untraced quantitative assertions.
        """
        normalized = text
        for pattern, norm_code, _, _ in STATUTORY_PATTERNS:
            normalized = pattern.sub(f"[STATUTE:{norm_code}]", normalized)
        return normalized

    def is_statutory_token(self, token: str) -> bool:
        """Check if a string token is a recognized statutory reference."""
        for pattern, _, _, _ in STATUTORY_PATTERNS:
            if pattern.search(token):
                return True
        return False
