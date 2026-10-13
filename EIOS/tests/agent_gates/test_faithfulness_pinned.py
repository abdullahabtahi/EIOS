"""The 13 legacy cases, frozen as Turn Records, are the seed regression set (T014).

The legacy auditor let all five wrong figures through and blocked both faithful answers; the new judge
must classify every one correctly. The cases are inputs, not the definition of correct.
"""

from typing import Any

import pytest

from eios.agent_gates.core.faithfulness import judge

from .conftest import load_recorded

RECORDS = load_recorded("pinned")

EXPECTED_REASON = {
    "pinned_wrong_field": "wrong_field",
    "pinned_hundred_times_too_small": "wrong_scale",
    "pinned_hundred_times_too_large": "wrong_scale",
    "pinned_wrong_unit": "wrong_unit",
    "pinned_invented_ring_size": "no_matching_value",
    "pinned_invented_rounded_revenue": "no_matching_value",
}


def test_all_thirteen_pinned_cases_are_present() -> None:
    assert len(RECORDS) == 13


@pytest.mark.parametrize("record", RECORDS, ids=[str(r["case_id"]) for r in RECORDS])
def test_each_pinned_case_is_classified_correctly(record: dict[str, Any]) -> None:
    result = judge(record)
    assert result.passed is record["expected_supported"], [
        (v.text, v.verdict, v.reason) for v in result.verdicts
    ]


@pytest.mark.parametrize("case_id", list(EXPECTED_REASON))
def test_unsupported_figures_carry_the_right_reason(case_id: str) -> None:
    (record,) = [r for r in RECORDS if r["case_id"] == case_id]
    reasons = {v.reason for v in judge(record).verdicts if v.verdict == "unsupported"}
    assert EXPECTED_REASON[case_id] in reasons, reasons
