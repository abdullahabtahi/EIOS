"""RL-5: PII Leakage Scanner (T023).

Enforces Constitution Principle IV: Security Markings & Token Vault.
Raw client emails, credit card numbers, government IDs/SSNs must never appear in outputs.
All entity identities must be pseudonymized using Layer 1 token vault keys:
(tok_usr_*, tok_id_cluster_*, ent_syn_*).
"""

import time
from typing import Any

from eios.evals.models import RedLineID, RedLineResult
from eios.evals.scanner import PII_PATTERNS


class RL5PIIScanner:
    """Scans text for unauthorized raw PII tokens."""

    def scan(self, text: str) -> RedLineResult:
        start_time = time.perf_counter()
        violations: list[dict[str, Any]] = []

        for pii_type, pattern in PII_PATTERNS.items():
            matches = pattern.findall(text)
            for m in matches:
                violations.append(
                    {
                        "type": pii_type,
                        "matched": m,
                        "reason": f"Unmasked {pii_type} detected in output text.",
                    }
                )

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return RedLineResult(
            test_id=RedLineID.RL_5,
            name="PII Leakage Scanner",
            passed=len(violations) == 0,
            total_evaluated=len(PII_PATTERNS),
            violations_detected=len(violations),
            tolerance=0,
            violation_samples=violations,
            execution_time_ms=elapsed_ms,
        )


def scan_text_for_pii(text: str) -> RedLineResult:
    return RL5PIIScanner().scan(text)


def test_rl5_suite() -> None:
    res = scan_text_for_pii("tok_usr_123 traded within tok_id_cluster_abc")
    assert res.passed, f"RL-5 failed: {res.violation_samples}"


def main() -> None:
    import json
    import sys
    from pathlib import Path

    res = scan_text_for_pii("Pseudonymized entity tok_usr_99 within cluster tok_id_cluster_44.")
    out = Path("evals/reports/rl_pii_leakage.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res.model_dump(), indent=2), encoding="utf-8")
    if not res.passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
