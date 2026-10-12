from __future__ import annotations

from collections.abc import Callable

from tools.common.findings import Finding

Scan = Callable[[str], tuple[Finding, ...]]


def test_valid_citation_passes(scan: Scan) -> None:
    assert scan("Revenue reached $4 million [BRIEF] (docs/brief/data.md §3).\n") == ()


def test_brief_without_citation_is_flagged(scan: Scan) -> None:
    (finding,) = scan("Revenue reached $4 million [BRIEF].\n")
    assert finding.rule_id == "label.brief-citation"


def test_citation_to_missing_file_is_flagged(scan: Scan) -> None:
    (finding,) = scan("Revenue reached $4 million [BRIEF] (docs/brief/absent.md §3).\n")
    assert finding.rule_id == "label.brief-citation"
    assert "does not exist" in finding.message


def test_citation_without_section_is_flagged(scan: Scan) -> None:
    (finding,) = scan("Revenue reached $4 million [BRIEF] (docs/brief/data.md).\n")
    assert "section" in finding.message


def test_untagged_figure_with_valid_brief_citation_is_traceable(scan: Scan) -> None:
    assert scan("Revenue reached $4 million, docs/brief/data.md section 3.\n") == ()


def test_brief_tag_without_a_figure_still_needs_a_citation(scan: Scan) -> None:
    assert [f.rule_id for f in scan("The regime is described [BRIEF].\n")] == [
        "label.brief-citation"
    ]
