"""The Agent Search adapter over a fake client: mapping, filtering, and an outage that is not 'no hits'."""

from types import SimpleNamespace
from typing import Any

import pytest

from eios.knowledge.agent_search import AgentSearchIndex
from eios.knowledge.passage import MAX_PASSAGE_CHARS, IndexUnavailable
from eios.ontology.omcp.port.contracts import DataOrigin


def chunk(
    text: str,
    *,
    name: str = "p/l/c/d/dataStores/s/branches/0/documents/MT-DOC/chunks/c3",
    **meta: Any,
) -> Any:
    data = {
        "document_id": "MT-DOC",
        "title": "Doc title",
        "jurisdiction": "MT",
        "kind": "legislation",
        **meta,
    }
    return SimpleNamespace(
        chunk=SimpleNamespace(
            id="c3",
            name=name,
            content=text,
            page_span=SimpleNamespace(page_start=41, page_end=42),
            document_metadata=SimpleNamespace(struct_data=data, title="uri title"),
        )
    )


class FakeClient:
    def __init__(self, results: list[Any] | Exception) -> None:
        self.results, self.requests = results, []

    def search(self, request: Any) -> list[Any]:
        self.requests.append(request)
        if isinstance(self.results, Exception):
            raise self.results
        return self.results


def index(client: FakeClient, **kw: Any) -> AgentSearchIndex:
    return AgentSearchIndex("proj", "store", client=client, **kw)


def test_a_chunk_becomes_a_passage_with_document_page_and_jurisdiction() -> None:
    client = FakeClient([chunk("  The rule text.  ")])
    [p] = index(client).search("what is the rule", None, 5)
    assert (p.passage_id, p.document_id, p.title, p.jurisdiction, p.pages) == (
        "MT-DOC.c3",
        "MT-DOC",
        "Doc title",
        "MT",
        "41-42",
    )
    assert p.text == "The rule text."
    assert index(client).origin is DataOrigin.LIVE


def test_the_request_asks_for_chunks_in_the_named_store_and_filters_by_jurisdiction() -> None:
    client = FakeClient([])
    index(client).search("reporting duty", "LB", 4)
    req = client.requests[0]
    assert req.serving_config.endswith("dataStores/store/servingConfigs/default_search")
    assert req.page_size == 4 and req.query == "reporting duty"
    assert req.filter == 'jurisdiction: ANY("LB")'
    assert req.content_search_spec.search_result_mode.name == "CHUNKS"


def test_no_jurisdiction_means_no_filter_and_a_bad_one_is_refused_before_the_call() -> None:
    client = FakeClient([])
    index(client).search("duty", None, 3)
    assert client.requests[0].filter == ""
    with pytest.raises(IndexUnavailable):
        index(client).search("duty", 'MT") OR jurisdiction: ANY("US', 3)
    assert len(client.requests) == 1


def test_no_result_is_an_empty_list_and_an_outage_is_an_error() -> None:
    assert index(FakeClient([])).search("anything", None, 5) == []
    with pytest.raises(IndexUnavailable):
        index(FakeClient(RuntimeError("quota"))).search("anything", None, 5)


def test_a_missing_page_span_is_n_a_and_an_empty_chunk_is_dropped() -> None:
    odd = chunk("text")
    odd.chunk.page_span = SimpleNamespace(page_start=0, page_end=0)
    assert index(FakeClient([odd, chunk("   ")])).search("q", None, 5)[0].pages == "n/a"
    assert len(index(FakeClient([odd, chunk("   ")])).search("q", None, 5)) == 1


def test_a_long_chunk_is_cut_to_the_limit_with_an_ellipsis() -> None:
    [p] = index(FakeClient([chunk("word " * 2000)])).search("q", None, 5)
    assert len(p.text) <= MAX_PASSAGE_CHARS and p.text.endswith("…")
