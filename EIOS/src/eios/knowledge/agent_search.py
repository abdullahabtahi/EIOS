"""The regulatory index on Agent Search: one data store, queried in chunk mode.

The data store parses the PDFs with the layout parser and chunks along headings (infra/modules/knowledge), so a
search returns passages that carry their page span and the document's own metadata. The adapter maps each chunk to a
`Passage`, filters by the jurisdiction of the issuing regulator, and drops what the service scores below the relevance
threshold, so a question with no support in the corpus returns nothing instead of the nearest wrong text.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from eios.knowledge.passage import MAX_PASSAGE_CHARS, IndexUnavailable, Passage
from eios.ontology.omcp.port.contracts import DataOrigin

logger = logging.getLogger(__name__)

SERVING_CONFIG = "default_search"
RELEVANCE_LEVELS = frozenset({"LOWEST", "LOW", "MEDIUM", "HIGH"})
_SAFE_ID = re.compile(r"[^A-Za-z0-9_.-]")
_JURISDICTION = re.compile(r"^[A-Z]{2,5}$")


def _pages(span: Any) -> str:
    start, end = int(getattr(span, "page_start", 0) or 0), int(getattr(span, "page_end", 0) or 0)
    if not start:
        return "n/a"
    return str(start) if end in (0, start) else f"{start}-{end}"


def _bounded(text: str) -> str:
    clean = text.strip()
    if len(clean) <= MAX_PASSAGE_CHARS:
        return clean
    cut = clean[: MAX_PASSAGE_CHARS - 1].rsplit(" ", 1)[0] or clean[: MAX_PASSAGE_CHARS - 1]
    return f"{cut}…"


class AgentSearchIndex:
    origin = DataOrigin.LIVE

    def __init__(
        self,
        project: str,
        data_store: str,
        *,
        location: str = "global",
        relevance: str = "LOW",
        client: Any | None = None,
    ) -> None:
        if relevance not in RELEVANCE_LEVELS:
            raise ValueError(f"relevance must be one of {sorted(RELEVANCE_LEVELS)}")
        self.description = f"agent_search:{data_store}"
        self._project, self._data_store, self._location = project, data_store, location
        self._relevance = relevance
        self._client = client

    def _search_client(self) -> Any:
        if self._client is None:
            from google.cloud import discoveryengine_v1  # the client opens credentials on import

            self._client = discoveryengine_v1.SearchServiceClient()
        return self._client

    def _request(self, query: str, jurisdiction: str | None, limit: int) -> Any:
        from google.cloud import discoveryengine_v1 as de

        spec = de.SearchRequest.ContentSearchSpec(
            search_result_mode=de.SearchRequest.ContentSearchSpec.SearchResultMode.CHUNKS
        )
        if jurisdiction is not None and not _JURISDICTION.fullmatch(jurisdiction):
            raise ValueError("jurisdiction must be a short upper-case code")
        return de.SearchRequest(
            serving_config=de.SearchServiceClient.serving_config_path(
                self._project, self._location, self._data_store, SERVING_CONFIG
            ),
            query=query,
            page_size=limit,
            content_search_spec=spec,
            relevance_threshold=getattr(de.SearchRequest.RelevanceThreshold, self._relevance),
            filter=f'jurisdiction: ANY("{jurisdiction}")' if jurisdiction else "",
        )

    def search(self, query: str, jurisdiction: str | None, limit: int) -> list[Passage]:
        try:
            response = self._search_client().search(self._request(query, jurisdiction, limit))
            return [p for r in response if (p := self._passage(r)) is not None][:limit]
        except IndexUnavailable:
            raise
        except (
            Exception
        ) as exc:  # the service, credentials or quota: reported as unavailable, never as "no hits"
            logger.warning("regulation search failed: %s", type(exc).__name__)
            raise IndexUnavailable(type(exc).__name__) from exc

    @staticmethod
    def _passage(result: Any) -> Passage | None:
        chunk = result.chunk
        meta = chunk.document_metadata
        data = dict(meta.struct_data) if meta.struct_data else {}
        document_id = str(
            data.get("document_id") or chunk.name.split("/documents/")[-1].split("/")[0]
        )
        text = _bounded(chunk.content or "")
        if not text:
            return None
        return Passage(
            passage_id=_SAFE_ID.sub("-", f"{document_id}.{chunk.id}")[:127],
            document_id=document_id,
            title=str(data.get("title") or meta.title or document_id),
            jurisdiction=str(data.get("jurisdiction") or "n/a"),
            kind=str(data.get("kind") or "n/a"),
            pages=_pages(chunk.page_span),
            text=text,
        )
