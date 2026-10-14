"""Shared word handling for the judges: content tokens, number words and direction words.

Standard library only. The same tokeniser is used on tool-result field names and on answer text, so that a
word in a sentence can be compared with the words of a field name.
"""

from __future__ import annotations

import re

UNITS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
}  # fmt: skip
TENS = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    "eighty": 80, "ninety": 90,
}  # fmt: skip
SCALES = {"hundred": 100, "thousand": 1_000, "million": 1_000_000, "billion": 1_000_000_000}
NUMBER_WORDS = frozenset(UNITS) | frozenset(TENS) | frozenset(SCALES)

# Words that carry no label meaning. Unit words are included so "dollars" cannot make two fields match.
STOPWORDS = frozenset(
    "the a an is are was were be been being of as has have had in on at to and or by for with from "
    "that this it its than then about approximately around roughly nearly almost over under per each "
    "which also now today currently current there their they you we i our your not no into up down "
    "across so if but can will would could should may might more less very key some any all "
    "usd eur gbp dollar euro percent pct percentage bps basis point hour hr day week month year "
    "and count value total amount number num id".split()
)  # fmt: skip

_CAMEL = re.compile(r"(?<=[a-z])(?=[A-Z])")
_WORD = re.compile(r"[A-Za-z]+|\d+[A-Za-z]*")
DIRECTION_WORDS = re.compile(
    r"\b(?:down|drop(?:ped|s)?|declin\w*|decreas\w*|fell|fall(?:en|s)?|decay\w*|lower|reduc\w*|loss|lost"
    r"|negative|shrank|shrunk|contract\w*)\b",
    re.IGNORECASE,
)
DERIVED_WORDS = re.compile(
    r"\b(?:higher|lower|more|less|increase\w*|decrease\w*|grew|grow\w*|rise|rose|fell|double\w*|triple\w*"
    r"|difference|gap|versus|vs)\b",
    re.IGNORECASE,
)


def singular(word: str) -> str:
    """A deliberately small plural stripper: enough to match 'accounts' with 'account'."""
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 3 and word.endswith("s") and not word.endswith(("ss", "us", "is")):
        return word[:-1]
    return word


def raw_tokens(text: str) -> list[str]:
    """Lower-case words of a field name or sentence, camelCase and snake_case split, nothing removed."""
    return [t.lower() for t in _WORD.findall(_CAMEL.sub(" ", text.replace("_", " ")))]


def content_tokens(text: str) -> list[str]:
    """Words that can label a figure: no stop words, no number words, no digits-first tokens."""
    out: list[str] = []
    for tok in raw_tokens(text):
        if len(tok) < 2 or tok in STOPWORDS or tok in NUMBER_WORDS or tok[0].isdigit():
            continue
        out.append(singular(tok))
    return out
