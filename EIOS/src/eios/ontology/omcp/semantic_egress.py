"""Semantic Egress Safety Gate (FM-5 Countermeasure).

Enforces automated inspection and sanitization of outbound agent narratives,
executive briefing texts, and partner-facing communications to prevent:
1. Defamatory, ungrounded legal accusations (e.g. "fraudster", "guilty of AML").
2. Ungrounded absolute certainty assertions (e.g. "guaranteed to churn").
3. Unverified numeric claims lacking provenance tags.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class EgressViolation:
    rule_id: str
    matched_term: str
    message: str
    severity: str = "ERROR"  # "ERROR" | "WARNING"


@dataclass
class SemanticEgressResult:
    is_safe: bool
    sanitized_text: str
    violations: list[EgressViolation] = field(default_factory=list)
    audit_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def has_blocking_errors(self) -> bool:
        return any(v.severity == "ERROR" for v in self.violations)


class SemanticEgressGate:
    """Pre-egress compliance firewall for LLM narrative outputs and briefings."""

    PROHIBITED_DEFAMATORY_TERMS: dict[str, str] = {
        r"\bfraudster\b": "party under anomaly review",
        r"\bmoney launderer\b": "subject of AML pattern analysis",
        r"\bguilty of (?:aml|fraud|crime)\b": "flagged for compliance inquiry",
        r"\bcriminal scheme\b": "high-risk transaction pattern",
        r"\billegal scam\b": "unauthorized activity pattern",
        r"\bsanctions evader\b": "sanctions nexus inquiry subject",
    }

    OVERCONFIDENT_CERTAINTY_TERMS: dict[str, str] = {
        r"\bguaranteed to churn\b": "projected high churn risk",
        r"\b100%\s*(?:churn|loss|leaving)\b": "elevated probability churn risk",
        r"\bwill definitely churn\b": "has high propensity to churn",
        r"\bzero chance of retention\b": "low baseline retention probability",
        r"\babsolutely certain\b": "statistically confident",
    }

    PROVENANCE_TAG_PATTERN = re.compile(r"\[(BRIEF|ASSUMPTION|TARGET|SPIKE|ILLUSTRATIVE)\]")

    NUMERIC_PATTERN = re.compile(
        r"(?<![\w$])(?:\$\d{1,3}(?:,\d{3})+(?:\.\d+)?|\$\d+(?:\.\d+)?|\d+(?:\.\d+)?%)(?!\w)"
    )

    def __init__(self, strict_provenance: bool = False) -> None:
        self.strict_provenance = strict_provenance

    def inspect_and_sanitize(
        self,
        text: str,
        context: dict[str, Any] | None = None,
    ) -> SemanticEgressResult:
        """Inspects text for defamatory allegations, excessive certainty, and ungrounded claims."""
        violations: list[EgressViolation] = []
        sanitized = text

        # 1. Defamatory allegations check
        for pattern, replacement in self.PROHIBITED_DEFAMATORY_TERMS.items():
            matches = list(re.finditer(pattern, sanitized, flags=re.IGNORECASE))
            if matches:
                for match in matches:
                    violations.append(
                        EgressViolation(
                            rule_id="egress.defamatory_allegation",
                            matched_term=match.group(0),
                            message=(
                                f"Prohibited ungrounded legal allegation '{match.group(0)}' detected. "
                                "Replace with objective compliance inquiry terminology."
                            ),
                            severity="ERROR",
                        )
                    )
                sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)

        # 2. Overconfident certainty assertions check
        for pattern, replacement in self.OVERCONFIDENT_CERTAINTY_TERMS.items():
            matches = list(re.finditer(pattern, sanitized, flags=re.IGNORECASE))
            if matches:
                for match in matches:
                    violations.append(
                        EgressViolation(
                            rule_id="egress.uncalibrated_certainty",
                            matched_term=match.group(0),
                            message=(
                                f"Uncalibrated certainty claim '{match.group(0)}' violates probabilistic reasoning. "
                                "Adjust to calibrated statistical bounds."
                            ),
                            severity="WARNING",
                        )
                    )
                sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)

        # 3. Numeric provenance check (if strict)
        if self.strict_provenance:
            has_tag = bool(self.PROVENANCE_TAG_PATTERN.search(text))
            has_numbers = bool(self.NUMERIC_PATTERN.search(text))
            if has_numbers and not has_tag:
                violations.append(
                    EgressViolation(
                        rule_id="egress.unlabelled_numeric_claim",
                        matched_term="[NUMERIC_UNTAGGED]",
                        message="Executive egress contains quantitative figures without provenance labels.",
                        severity="ERROR",
                    )
                )

        is_safe = not any(v.severity == "ERROR" for v in violations)

        return SemanticEgressResult(
            is_safe=is_safe,
            sanitized_text=sanitized,
            violations=violations,
        )
