"""`search_regulations`: untrusted passages with provenance, an honest empty result, and typed errors."""

from dataclasses import replace

import pytest

from eios.knowledge.passage import IndexUnavailable
from eios.knowledge.static_index import StaticIndex
from eios.ontology.omcp.port.catalogue import build_port
from eios.ontology.omcp.port.contracts import DataOrigin, ToolErrorCode
from eios.ontology.omcp.port.readmodels import ReadModels
from tests.knowledge.passages import ALL, FILING
from tests.ontology.port.conftest import who

AML = who("aml_investigator")


def port_with(index: object | None):
    return build_port(replace(ReadModels.default(), knowledge=index))


def test_a_question_returns_untrusted_passages_with_document_page_and_jurisdiction() -> None:
    out = port_with(StaticIndex(ALL)).call(
        AML, "search_regulations", {"query": "when must a suspicious report be filed"}
    )
    assert out.error is None
    body = out.payload()
    assert body["capability"] == "knowledge.regulation"
    assert body["untrusted"] is True
    assert body["data_origin"] == DataOrigin.FIXTURE.value
    assert body["fact_ids"] == {}
    assert body["passages"][0]["document_id"] == FILING.document_id
    assert body["passages"][0]["pages"] == "41-42"


def test_nothing_found_says_so_in_the_result() -> None:
    out = port_with(StaticIndex(ALL)).call(
        AML, "search_regulations", {"query": "quarterly revenue forecast"}
    )
    assert out.error is None
    assert out.payload()["passages"] == []
    assert "No passage" in out.payload()["note"]


def test_jurisdiction_is_normalised_and_restricted_to_the_corpus_issuers() -> None:
    port = port_with(StaticIndex(ALL))
    ok = port.call(
        AML, "search_regulations", {"query": "red flag virtual assets", "jurisdiction": "lb"}
    )
    assert ok.payload()["jurisdiction"] == "LB"
    bad = port.call(
        AML, "search_regulations", {"query": "red flag virtual assets", "jurisdiction": "XX"}
    )
    assert bad.error is not None and bad.error.code is ToolErrorCode.INVALID_ARGUMENTS


def test_no_index_configured_is_data_unavailable_not_an_empty_answer() -> None:
    out = port_with(None).call(AML, "search_regulations", {"query": "reporting deadline"})
    assert out.error is not None and out.error.code is ToolErrorCode.DATA_UNAVAILABLE


def test_an_unreachable_index_is_a_retryable_error() -> None:
    class Down:
        origin = DataOrigin.LIVE
        description = "down"

        def search(self, query: str, jurisdiction: str | None, limit: int):
            raise IndexUnavailable("quota")

    out = port_with(Down()).call(AML, "search_regulations", {"query": "reporting deadline"})
    assert out.error is not None and out.error.retryable is True


@pytest.mark.parametrize("workstation", ["partner_manager", "executive", "data_operations"])
def test_other_workstations_are_not_offered_the_tool(workstation: str) -> None:
    out = port_with(StaticIndex(ALL)).call(
        who(workstation), "search_regulations", {"query": "reporting deadline"}
    )
    assert out.error is not None and out.error.code is ToolErrorCode.FORBIDDEN_ROLE


def test_every_passage_carries_a_highlight_that_is_a_slice_of_its_text() -> None:
    body = (
        port_with(StaticIndex(ALL))
        .call(AML, "search_regulations", {"query": "when must a suspicious report be filed"})
        .payload()
    )
    for passage in body["passages"]:
        assert passage["highlight"] and passage["highlight"] in passage["text"]


def test_every_passage_lists_its_body_sentences_numbered_for_quoting() -> None:
    body = (
        port_with(StaticIndex(ALL))
        .call(AML, "search_regulations", {"query": "when must a suspicious report be filed"})
        .payload()
    )
    first = body["passages"][0]
    assert first["sentences"] and first["sentences"][0].startswith("s1: ")
