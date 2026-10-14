from eios.knowledge.highlight import MAX_HIGHLIGHT_CHARS, highlight

CHUNK = """# 5.4 Internal Reporting Procedures

The internal reporting procedures of a subject person have to clearly set out the steps to be followed. Internal reports are understood to apply to contracted third parties.Page | 232FIAU

# CHAPTER 5 - REPORTING PROCEDURES AND OBLIGATIONS

The internal reporting procedures should clearly state that the employee shall report the matter to the officer without delay. The authority expects such a report to be made by not later than the next working day. It is crucial that all employees know the identity of the officer.

Reports should preferably be written using a standard template."""


def test_it_picks_the_sentence_that_answers_the_question_as_a_verbatim_slice() -> None:
    out = highlight(
        CHUNK, "How quickly must an employee pass a suspicion on to the reporting officer?"
    )
    assert "not later than the next working day" in out
    assert out in CHUNK  # copied, never reworded
    assert "# CHAPTER" not in out and "Page | 232" not in out


def test_it_extends_over_following_sentences_that_also_match() -> None:
    out = highlight(CHUNK, "when must the employee report the matter to the officer without delay")
    assert out.startswith("The internal reporting procedures should clearly state")
    assert "next working day" in out


def test_headings_and_page_furniture_are_never_the_highlight() -> None:
    assert highlight("# Only a heading\n\nPage | 12FIAU\n", "heading") == ""


def test_a_very_long_single_sentence_is_cut_at_a_word_with_an_ellipsis() -> None:
    out = highlight("word " * 400 + "end of sentence.", "word")
    assert len(out) <= MAX_HIGHLIGHT_CHARS and out.endswith("…")


def test_a_question_with_no_overlap_still_returns_the_first_body_sentence() -> None:
    out = highlight(CHUNK, "zebra giraffe")
    assert out and out in CHUNK
