"""A quotation the tool returned word for word is exempt from the figure check; an invented one is not."""

from eios.agent_gates.core.faithfulness import judge

PASSAGE = {
    "passage_id": "TEST-RULE-A.c1",
    "title": "Test rule A (not a regulation)",
    "pages": "41-42",
    "jurisdiction": "MT",
    "text": "A subject person shall file a suspicious report within 5 working days of forming the suspicion.",
}
CALL = {
    "name": "search_regulations",
    "arguments": {"query": "deadline"},
    "result": {"capability": "knowledge.regulation", "passages": [PASSAGE]},
}
QUOTE = (
    "The guidance sets the period:\n\n"
    "> A subject person shall file a suspicious report within 5 working days of forming the suspicion.\n"
    "> — Test rule A (not a regulation), p. 41-42 (MT)\n"
)


def record(answer: str, calls: list[dict] | None = None) -> dict:
    return {
        "question": "deadline",
        "answer": answer,
        "tool_calls": calls if calls is not None else [CALL],
    }


def test_a_quote_the_tool_returned_is_exempt_with_its_numbers_and_page() -> None:
    result = judge(record(QUOTE))
    assert result.passed
    assert any(v.reason == "exempt:verified_quote" for v in result.verdicts)


def test_the_same_quote_without_a_tool_result_is_judged_like_any_text() -> None:
    assert not judge(record(QUOTE, calls=[])).passed


def test_an_altered_quote_is_not_exempt() -> None:
    altered = QUOTE.replace("5 working days", "10 working days")
    assert not judge(record(altered)).passed


def test_a_wrong_page_in_the_credit_line_is_not_exempt() -> None:
    assert not judge(record(QUOTE.replace("p. 41-42", "p. 7"))).passed


def test_a_number_the_model_typed_beside_a_valid_quote_still_fails() -> None:
    assert not judge(
        record("Reports are due within 5 working days.\n\n" + QUOTE.split("\n\n", 1)[1])
    ).passed


def test_a_contiguous_slice_of_the_returned_passage_is_exempt() -> None:
    sliced = (
        "The guidance sets the period:\n\n"
        "> shall file a suspicious report within 5 working days of forming the suspicion.\n"
        "> — Test rule A (not a regulation), p. 41-42 (MT)\n"
    )
    assert judge(record(sliced)).passed


def test_a_slice_that_ends_in_an_ellipsis_is_exempt_but_a_very_short_one_is_not() -> None:
    cut = QUOTE.replace("of forming the suspicion.", "of forming…")
    assert judge(record(cut)).passed
    tiny = "> 5 working\n> — Test rule A (not a regulation), p. 41-42 (MT)\n"
    assert not judge(record(tiny)).passed


def test_a_quote_of_several_sentences_is_exempt_when_each_line_is_in_the_passage() -> None:
    passage = {
        **PASSAGE,
        "text": "First rule applies to all persons. Second rule sets 5 working days. Page | 4FIAU Third rule is unrelated.",
    }
    call = {**CALL, "result": {"capability": "knowledge.regulation", "passages": [passage]}}
    answer = (
        "> First rule applies to all persons.\n"
        "> Second rule sets 5 working days.\n"
        "> — Test rule A (not a regulation), p. 41-42 (MT)\n"
    )
    assert judge(record(answer, [call])).passed
    invented = answer.replace(
        "Second rule sets 5 working days.", "Second rule sets 9 working days."
    )
    assert not judge(record(invented, [call])).passed


def test_a_record_that_holds_only_the_numbered_sentences_verifies_a_quote_too() -> None:
    view = {k: v for k, v in PASSAGE.items() if k != "text"}
    view["sentences"] = [
        "s1: First rule applies to all persons.",
        "s2: Second rule sets 5 working days.",
    ]
    call = {**CALL, "result": {"capability": "knowledge.regulation", "passages": [view]}}
    answer = (
        "> Second rule sets 5 working days.\n> — Test rule A (not a regulation), p. 41-42 (MT)\n"
    )
    assert judge(record(answer, [call])).passed
    assert not judge(record(answer.replace("5 working", "9 working"), [call])).passed
