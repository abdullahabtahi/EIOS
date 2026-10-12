"""Metric Auditor Gate egress firewall enforcing Red-Line test RL-1 (Principle I, US5)."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from eios.ontology.auditor.normalizer import NumericTokenNormalizer


class AuditVerificationRecord(BaseModel):
    """Immutable record documenting mathematical provenance verification."""

    trace_id: str
    narrative_text: str
    extracted_numbers: list[str] = Field(default_factory=list)
    anchored_numbers: list[float] = Field(default_factory=list)
    untraceable_numbers: list[str] = Field(default_factory=list)
    audit_passed: bool
    rejection_reason: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_compliant(self) -> bool:
        return self.audit_passed

    @property
    def passed(self) -> bool:
        return self.audit_passed

    @property
    def unanchored_tokens(self) -> list[str]:
        return self.untraceable_numbers


class MetricAuditorGate:
    """Egress firewall verifying that all numeric tokens anchor to tool execution traces."""

    def __init__(self, relative_tolerance: float = 0.01) -> None:
        self.normalizer = NumericTokenNormalizer()
        self.relative_tolerance = relative_tolerance

    def verify_response(
        self,
        narrative_text: str,
        tool_trace: list[dict[str, Any]],
        trace_id: str = "tr_default",
    ) -> AuditVerificationRecord:
        """Alias for audit to support response verification interface."""
        return self.audit(narrative_text, tool_trace, trace_id=trace_id)

    def _collect_numbers_from_obj(self, obj: Any, out_set: set[float]) -> None:
        """Recursively harvest numbers from arbitrary tool trace output JSON."""
        if isinstance(obj, (int, float)) and not isinstance(obj, bool):
            out_set.add(float(obj))
        elif isinstance(obj, dict):
            for v in obj.values():
                self._collect_numbers_from_obj(v, out_set)
        elif isinstance(obj, list):
            for item in obj:
                self._collect_numbers_from_obj(item, out_set)

    def extract_ground_truth_numbers(self, tool_trace: list[dict[str, Any]]) -> set[float]:
        """Collect all scalar numbers output by deterministic tools in the session trace."""
        ground_truth: set[float] = set()
        for call in tool_trace:
            output = call.get("output", {})
            self._collect_numbers_from_obj(output, ground_truth)
        return ground_truth

    def _matches_any(self, val: float, ground_truth: set[float]) -> bool:
        """Check if val matches any ground truth number within relative tolerance."""
        for gt in ground_truth:
            diff = abs(val - gt)
            denom = max(abs(gt), 1e-9)
            if (diff / denom) <= self.relative_tolerance:
                return True
            # Also check direct percentage scaling: e.g. 0.28 vs 28.0 (val was 0.281 vs gt 0.28)
            if gt != 0:
                if abs((val * 100.0) - gt) / abs(gt) <= self.relative_tolerance:
                    return True
                if abs(val - (gt * 100.0)) / (abs(gt) * 100.0) <= self.relative_tolerance:
                    return True
        return False

    def audit(
        self,
        narrative_text: str | None = None,
        tool_trace: list[dict[str, Any]] | None = None,
        trace_id: str = "tr_default",
        *,
        response_text: str | None = None,
        tool_outputs: list[dict[str, Any]] | None = None,
    ) -> AuditVerificationRecord:
        """Audit an agent response text against tool execution outputs."""
        text = response_text if response_text is not None else (narrative_text or "")
        trace = tool_outputs if tool_outputs is not None else (tool_trace or [])
        extracted = self.normalizer.extract_numbers(text)
        ground_truth = self.extract_ground_truth_numbers(trace)

        extracted_strs: list[str] = []
        anchored: list[float] = []
        untraceable: list[str] = []

        for item in extracted:
            extracted_strs.append(item.raw_string)
            if self._matches_any(item.normalized_value, ground_truth):
                anchored.append(item.normalized_value)
            else:
                untraceable.append(item.raw_string)

        passed = len(untraceable) == 0
        rejection_reason = (
            f"Blocked by Auditor Gate: Found {len(untraceable)} unanchored numbers: {untraceable}"
            if not passed
            else None
        )

        return AuditVerificationRecord(
            trace_id=trace_id,
            narrative_text=text,
            extracted_numbers=extracted_strs,
            anchored_numbers=anchored,
            untraceable_numbers=untraceable,
            audit_passed=passed,
            rejection_reason=rejection_reason,
        )
