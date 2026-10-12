"""``spec_text``: a sentence in prose that states a still-open decision as settled.

Parameters (``candidates`` per rule; the rest usually from the top-level ``spec_text`` section):

* ``candidates`` - names of the options, matched as whole words with the case written.
* ``verbs`` - decisive words or phrases ("use", "built on"), matched as whole words, any case.
* ``qualifiers`` - words that mark a sentence as discussing options ("candidate", "option"...).
* ``include`` / ``exclude`` - path globs of the prose files to read (Markdown).

A sentence is flagged when it holds a candidate and a decisive verb and no qualifier. Fenced
code blocks are skipped. Sentences are split at ``. ! ?`` followed by space, and at the start of
each list item, table row or heading.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Sequence
from dataclasses import dataclass

from eios.common.errors import ConfigError
from tools.open_decision_check.config import CONFIG_PATH, RuleSpec
from tools.open_decision_check.rules_base import (
    CompiledRule,
    Hit,
    SourceFile,
    compiled,
    path_matches,
    string_list,
)

_UNIT_START = re.compile(r"^\s*(?:[-*+|#>]|\d+[.)]\s)")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
_FENCE = re.compile(r"^\s*(```|~~~)")


def _phrase_regex(words: Sequence[str], *, ignore_case: bool) -> re.Pattern[str]:
    body = "|".join(r"\s+".join(re.escape(part) for part in w.split()) for w in words)
    pattern = rf"(?<![\w-])(?:{body})(?![\w-])"
    return re.compile(pattern, re.IGNORECASE if ignore_case else 0)


def _units(text: str) -> Iterator[tuple[int, str]]:
    """``(first line number, text)`` of each prose unit outside fenced code blocks."""
    current: list[str] = []
    start = 1
    fenced = False
    for number, line in enumerate(text.splitlines(), start=1):
        if _FENCE.match(line):
            fenced = not fenced
            continue
        blank = not line.strip()
        if fenced or blank or _UNIT_START.match(line):
            if current:
                yield start, " ".join(current)
                current = []
        if fenced or blank:
            continue
        if not current:
            start = number
        current.append(line.strip())
    if current:
        yield start, " ".join(current)


def _sentences(text: str) -> Iterator[tuple[int, str]]:
    """Sentences of the file with their first line number."""
    for start, unit in _units(text):
        for sentence in _SENTENCE_END.split(unit):
            if sentence.strip():
                yield start, sentence


@dataclass(frozen=True, slots=True)
class _Matchers:
    candidates: re.Pattern[str]
    verbs: re.Pattern[str]
    qualifiers: re.Pattern[str]


def _hits(source: SourceFile, m: _Matchers) -> Iterator[Hit]:
    for line, sentence in _sentences(source.text):
        candidate = m.candidates.search(sentence)
        if candidate and m.verbs.search(sentence) and not m.qualifiers.search(sentence):
            message = (
                f"states {candidate.group(0)!r} as settled in prose "
                "(no candidate, option or open qualifier)"
            )
            yield Hit(source.path, line, message)


def build_spec_text(spec: RuleSpec) -> CompiledRule:
    try:
        matchers = _Matchers(
            _phrase_regex(string_list(spec, "candidates"), ignore_case=False),
            _phrase_regex(string_list(spec, "verbs"), ignore_case=True),
            _phrase_regex(string_list(spec, "qualifiers"), ignore_case=True),
        )
    except re.error as exc:  # pragma: no cover - every part is escaped
        raise ConfigError(CONFIG_PATH, spec.where, f"invalid phrase list: {exc}") from exc
    globs = string_list(spec, "include")

    def check(files: Sequence[SourceFile]) -> tuple[Hit, ...]:
        prose = (f for f in files if path_matches(f.path, globs))
        return tuple(h for f in prose for h in _hits(f, matchers))

    return compiled(spec, check, globs)
