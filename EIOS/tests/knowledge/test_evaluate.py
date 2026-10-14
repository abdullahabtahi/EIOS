from pathlib import Path

from eios.knowledge.corpus import acquired
from eios.knowledge.evaluate import Expect, RetrievalCase, evaluate, is_hit, load_cases, page_span
from eios.knowledge.static_index import StaticIndex
from tests.knowledge.passages import ALL, FILING

CASES = Path(__file__).resolve().parents[2] / "evals" / "knowledge" / "cases.yaml"


def test_page_spans_read_single_pages_ranges_and_missing() -> None:
    assert (
        list(page_span("41")) == [41]
        and list(page_span("41-43")) == [41, 42, 43]
        and list(page_span("n/a")) == []
    )


def test_a_hit_needs_the_expected_document_and_an_overlapping_page() -> None:
    assert is_hit(FILING, [Expect(document_id="TEST-RULE-A", pages=(42,))])
    assert not is_hit(FILING, [Expect(document_id="TEST-RULE-A", pages=(50,))])
    assert not is_hit(FILING, [Expect(document_id="OTHER", pages=(41,))])


def test_recall_and_silence_are_computed_over_answerable_and_unanswerable_cases() -> None:
    cases = (
        RetrievalCase(
            id="a",
            question="when must a suspicious report be filed",
            expect=(Expect(document_id="TEST-RULE-A", pages=(41,)),),
        ),
        RetrievalCase(
            id="b",
            question="red flag virtual assets wallets",
            expect=(Expect(document_id="TEST-RULE-A", pages=(99,)),),
        ),
        RetrievalCase(id="c", question="quarterly revenue forecast"),
    )
    report = evaluate(StaticIndex(ALL), cases)
    assert (report["answerable"], report["unanswerable"]) == (2, 1)
    assert report["recall_at_1"] == 0.5 and report["silence_on_unanswerable"] == 1.0


def test_the_shipped_cases_name_only_acquired_documents_and_pages_inside_them() -> None:
    documents = {d.id: d for d in acquired()}
    for case in load_cases(CASES):
        for e in case.expect:
            assert e.document_id in documents, case.id
            assert all(1 <= p <= (documents[e.document_id].pages or 0) for p in e.pages), case.id
    assert any(not c.expect for c in load_cases(CASES))
