"""An in-memory index over a given list of passages, for tests and the offline agent gates.

It ranks by shared words, which is enough to exercise routing, assembly and the refusal path; it makes no claim to
retrieval quality (that is measured against the real index, `evals/knowledge`). Its origin is FIXTURE, so an
answer built on it never claims to come from the acquired corpus.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from eios.knowledge.passage import Passage
from eios.ontology.omcp.port.contracts import DataOrigin

_WORD = re.compile(r"[a-z]{3,}")
_STOP = frozenset(
    {"the", "and", "for", "that", "with", "what", "does", "say", "about", "are", "this", "from"}
)


def _words(text: str) -> set[str]:
    return {w for w in _WORD.findall(text.lower()) if w not in _STOP}


class StaticIndex:
    origin = DataOrigin.FIXTURE
    description = "knowledge.static_index"

    def __init__(self, passages: Iterable[Passage]) -> None:
        self._passages = tuple(passages)

    def search(self, query: str, jurisdiction: str | None, limit: int) -> list[Passage]:
        wanted = _words(query)
        scored = [
            (len(wanted & _words(p.title + " " + p.text)), p)
            for p in self._passages
            if jurisdiction is None or p.jurisdiction == jurisdiction
        ]
        hits = sorted((s for s in scored if s[0] > 0), key=lambda s: -s[0])
        return [p for _, p in hits[:limit]]
