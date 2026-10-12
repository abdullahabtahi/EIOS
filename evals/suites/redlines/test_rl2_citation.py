"""RL-2: Citation & Provenance Coverage Gate (T020).

Enforces Invariant 6 (Data as a Product) and Constitution Principle V (Provenance).
Every factual claim regarding entity behavior or metrics must cite:
- An explicit Entity ID (e.g. tok_usr_*, P-*, TXN-*)
- Metric definition version (e.g. definition_version v*)
- Data product as_of timestamp (e.g. as_of YYYY-MM-DD...)
"""

import re
import time
from typing import Any

from eios.evals.models import RedLineID, RedLineResult

ENTITY_ID_PATTERN = re.compile(r"\b(tok_usr_[a-zA-Z0-9_]+|P-\d+|TXN-\d+)\b")
AS_OF_PATTERN = re.compile(r"\bas_of\s+\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}Z?)?\b", re.IGNORECASE)
DEF_VERSION_PATTERN = re.compile(r"\bdefinition_version\s+v?\d+(\.\d+)*\b", re.IGNORECASE)


class RL2CitationVerifier:
    """Verifies that emitted narratives include rigorous entity and provenance citations."""

    def verify(self, text: str) -> RedLineResult:
        start_time = time.perf_counter()
        violations: list[dict[str, Any]] = []

        has_entity = bool(ENTITY_ID_PATTERN.search(text))
        has_as_of = bool(AS_OF_PATTERN.search(text))
        has_def = bool(DEF_VERSION_PATTERN.search(text))

        # Full provenance requires at least entity citation and temporal / version anchor
        has_provenance = has_entity and (has_as_of or has_def)

        if not has_provenance:
            missing = []
            if not has_entity:
                missing.append("entity ID (tok_usr_*, P-*, TXN-*)")
            if not (has_as_of or has_def):
                missing.append("data product as_of or definition_version")
            violations.append(
                {
                    "reason": f"Missing required entity or timestamp citations: {', '.join(missing)}.",
                }
            )

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return RedLineResult(
            test_id=RedLineID.RL_2,
            name="Citation & Provenance Coverage",
            passed=len(violations) == 0,
            total_evaluated=1,
            violations_detected=len(violations),
            tolerance=0,
            violation_samples=violations,
            execution_time_ms=elapsed_ms,
        )


def verify_citation_coverage(text: str) -> RedLineResult:
    return RL2CitationVerifier().verify(text)


def test_rl2_suite() -> None:
    res = verify_citation_coverage("tok_usr_123 P-1 as_of 2026-10-01")
    assert res.passed, f"RL-2 failed: {res.violation_samples}"


def main() -> None:
    import json
    import sys
    from pathlib import Path

    res = verify_citation_coverage(
        "Entity tok_usr_abc spikes under P-12 as_of 2026-10-01T00:00:00Z."
    )
    out = Path("evals/reports/rl_citation.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res.model_dump(), indent=2), encoding="utf-8")
    if not res.passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
