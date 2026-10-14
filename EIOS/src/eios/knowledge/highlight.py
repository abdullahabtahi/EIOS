"""Pick the sentences of a passage that answer the question, as a verbatim excerpt.

A retrieved chunk is up to a few thousand characters of a regulation, with headings, footnote marks and page footers.
The answer shows only the sentence or two that match the question, copied exactly from the chunk (a contiguous slice, never
reworded), while the whole chunk stays available as the source. Selection is lexical and deterministic: it ranks, it does
not decide what a rule means.
"""

from __future__ import annotations

import re

MAX_HIGHLIGHT_CHARS = (
    600  # [ASSUMPTION] about three sentences: enough to carry a rule with its condition
)
MAX_SENTENCES = 3
_WORD = re.compile(r"[a-z]{3,}")
_STOP = frozenset(
    "the and for that with what does say about are this from how when who which must should shall have has not can may any "
    "into than then they their there been being was were will would could our your you its also such per".split()
)
_FURNITURE = re.compile(r"^(?:#+\s|page\s*\|\s*\d+|\d{1,4}\s*$)", re.IGNORECASE)
_SENTENCE = re.compile(r"\S.*?(?:[.!?;](?=\s+[A-Z(\"“#])|$)", re.DOTALL)


def _stems(text: str) -> set[str]:
    return {w[:5] for w in _WORD.findall(text.lower()) if w not in _STOP}


def _sentences(text: str) -> list[tuple[int, int]]:
    """Spans of the sentences of the body text; headings and page furniture are not candidates."""
    spans: list[tuple[int, int]] = []
    offset = 0
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        if stripped and not _FURNITURE.match(stripped):
            for m in _SENTENCE.finditer(line):
                if m.group(0).strip():
                    spans.append((offset + m.start(), offset + m.end()))
        offset += len(line)
    return spans


def body_sentences(text: str) -> list[str]:
    """The sentences of the body text in reading order, each exactly as written. The assistant is shown them numbered
    (`s1`, `s2`, ...) and quotes a run of them by number, so the answer prints the regulator's words and never its own."""
    return [text[a:b].strip() for a, b in _sentences(text)]


def highlight(text: str, query: str, limit: int = MAX_HIGHLIGHT_CHARS) -> str:
    """The best-matching sentence of `text` for `query`, extended over following sentences that also match.

    Always a contiguous slice of `text` (a very long single sentence is cut at a word boundary and ends with an ellipsis).
    Empty when the passage has no body sentence.
    """
    spans = _sentences(text)
    if not spans:
        return ""
    wanted = _stems(query)
    scores = [len(wanted & _stems(text[a:b])) for a, b in spans]
    best = max(range(len(spans)), key=lambda i: (scores[i], -i))
    first, last = best, best
    while (
        last + 1 < len(spans)
        and last - first + 1 < MAX_SENTENCES
        and scores[last + 1] > 0
        and spans[last + 1][1] - spans[first][0] <= limit
    ):
        last += 1
    chosen = text[spans[first][0] : spans[last][1]].strip()
    if len(chosen) <= limit:
        return chosen
    return chosen[: limit - 1].rsplit(" ", 1)[0] + "…"
