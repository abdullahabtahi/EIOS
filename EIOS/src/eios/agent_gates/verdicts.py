"""Verdicts and gate results (spec 022). Inconclusive never counts as a pass (FR-024)."""

from collections.abc import Sequence
from enum import StrEnum

from eios.common.validation import StrictModel


class Verdict(StrEnum):
    PASS = "pass"  # noqa: S105 - a verdict label, not a credential
    FAIL = "fail"
    INCONCLUSIVE = "inconclusive"


class CaseVerdict(StrictModel):
    case_id: str
    verdict: Verdict
    evidence: str = ""


class GateResult(StrictModel):
    gate_id: str
    blocking: bool
    counts: dict[str, int]
    first_failure: CaseVerdict | None
    proven: bool


def summarise_gate(gate_id: str, blocking: bool, verdicts: Sequence[CaseVerdict]) -> GateResult:
    """A gate is `proven` only if it ran at least one case, none failed and none is inconclusive."""
    counts = {v.value: sum(1 for c in verdicts if c.verdict is v) for v in Verdict}
    first_failure = next((c for c in verdicts if c.verdict is Verdict.FAIL), None)
    proven = bool(verdicts) and counts["fail"] == 0 and counts["inconclusive"] == 0
    return GateResult(
        gate_id=gate_id,
        blocking=blocking,
        counts=counts,
        first_failure=first_failure,
        proven=proven,
    )
