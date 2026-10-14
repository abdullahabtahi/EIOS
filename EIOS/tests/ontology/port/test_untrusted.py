"""Outside text is bounded on a word boundary (spec 023 FR-008)."""

from eios.ontology.omcp.port.untrusted import MAX_EXCERPT_CHARS, bound_excerpt


def test_short_text_is_only_whitespace_normalised() -> None:
    assert bound_excerpt("hello   there\n friend") == "hello there friend"


def test_long_text_is_cut_on_a_word_and_marked() -> None:
    out = bound_excerpt("word " * 200)
    assert len(out) <= MAX_EXCERPT_CHARS and out.endswith("…") and "wor…" not in out


def test_a_single_unbroken_token_is_still_bounded() -> None:
    assert len(bound_excerpt("x" * 1000)) <= MAX_EXCERPT_CHARS
