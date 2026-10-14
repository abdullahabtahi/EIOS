"""Verdict and gate-result tests (T007)."""

from eios.agent_gates.verdicts import CaseVerdict, Verdict, summarise_gate


def _v(case: str, verdict: Verdict, evidence: str = "") -> CaseVerdict:
    return CaseVerdict(case_id=case, verdict=verdict, evidence=evidence)


def test_all_pass_is_proven() -> None:
    result = summarise_gate("g", True, [_v("a", Verdict.PASS), _v("b", Verdict.PASS)])
    assert result.proven
    assert result.counts == {"pass": 2, "fail": 0, "inconclusive": 0}
    assert result.first_failure is None


def test_inconclusive_is_never_proven_even_without_failures() -> None:
    result = summarise_gate("g", True, [_v("a", Verdict.PASS), _v("b", Verdict.INCONCLUSIVE)])
    assert not result.proven
    assert result.counts["inconclusive"] == 1


def test_first_failure_carries_its_evidence() -> None:
    result = summarise_gate(
        "g", True, [_v("a", Verdict.PASS), _v("b", Verdict.FAIL, "16 is not the risk score")]
    )
    assert not result.proven
    assert result.first_failure is not None
    assert result.first_failure.case_id == "b"
    assert result.first_failure.evidence == "16 is not the risk score"


def test_an_empty_gate_is_not_proven() -> None:
    assert not summarise_gate("g", True, []).proven
