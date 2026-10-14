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
