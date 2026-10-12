from __future__ import annotations

from collections.abc import Callable

import pytest

from tools.common.findings import Finding
from tools.label_check.scanner import numeric_claim_kinds

from .conftest import rule_ids

Scan = Callable[[str], tuple[Finding, ...]]


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        ("Churn rose 12% last quarter.", "percentage"),
        ("Churn rose 12.5 percent.", "percentage"),
        ("Budget is $4 million.", "currency"),
        ("Budget is 400 USD.", "currency"),
        ("There are 40 partners.", "count"),
        ("A 30-prompt set.", "count"),
        ("Up to 1M edges.", "count"),
        ("Takes 30 minutes.", "duration"),
        ("Latency 300 ms.", "duration"),
        ("A ratio of 3:1.", "ratio"),
        ("About 1 in 20 cases.", "ratio"),
    ],
)
def test_positive_claims(rules, text: str, kind: str) -> None:  # type: ignore[no-untyped-def]
    assert kind in numeric_claim_kinds(text, rules)


@pytest.mark.parametrize(
    "text",
    [
        "See FR-001, SC-007, T001, S-01, ADR-002 and F00.",
        "Released 2026-01-05 at 10:30Z.",
        "1. A numbered list marker",
        "## 4.2 Heading number",
        "See `src/a.py:12` and lines 61-72.",
        "Section §4 and version 1.2.3 and `99 clients` in code.",
        "Python 3.14 is the runtime.",
        "Commit abc1234 fixed it.",
        "[link text](https://example.test/50-percent)",
    ],
)
def test_negative_claims(rules, text: str) -> None:  # type: ignore[no-untyped-def]
    assert numeric_claim_kinds(text, rules) == frozenset()


def test_fenced_code_is_skipped(scan: Scan) -> None:
    assert scan("```text\n99% of 100 clients\n```\n") == ()


def test_unlabelled_claim_is_flagged_and_message_omits_the_figure(scan: Scan) -> None:
    (finding,) = scan("# T\n\nChurn rose 12% last quarter.\n")
    assert (finding.rule_id, finding.line) == ("label.unlabelled-claim", 3)
    assert "12" not in finding.message


def test_one_tag_passes_two_tags_fail_unknown_tag_fails(scan: Scan) -> None:
    assert scan("Latency is 300 ms [TARGET].\n") == ()
    assert rule_ids(scan("Latency is 300 ms [TARGET] [ASSUMPTION].\n")) == ["label.multiple-tags"]
    assert rule_ids(scan("Latency is 300 ms [BOGUS].\n")) == [
        "label.unknown-tag",
        "label.unlabelled-claim",
    ]


def test_markdown_link_brackets_are_not_unknown_tags(scan: Scan) -> None:
    assert scan("See [README](docs/a.md) for more.\n") == ()


def test_scope_sentence_row_and_item(scan: Scan) -> None:
    assert scan("Ten days [TARGET]. Then 30 days later it ends.\n")[0].line == 1
    assert rule_ids(scan("Ten days [TARGET]. Then 30 days later it ends.\n")) == [
        "label.unlabelled-claim"
    ]
    table = "| a | b |\n|---|---|\n| 30 days | x |\n| 5 days | y [TARGET] |\n"
    assert [(f.line, f.rule_id) for f in scan(table)] == [(3, "label.unlabelled-claim")]
    items = "- 30 days later\n  continued [TARGET]\n- 5 days\n"
    assert [(f.line, f.rule_id) for f in scan(items)] == [(3, "label.unlabelled-claim")]


def test_tag_inside_backticks_counts_but_numbers_inside_do_not(scan: Scan) -> None:
    assert scan("Takes 30 minutes `[TARGET]`.\n") == ()
    assert scan("Takes `30 minutes`.\n") == ()
