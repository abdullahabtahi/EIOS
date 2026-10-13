"""Unit suffixes need a word boundary: 'bps' is not billions and 'months' is not millions."""

import pytest

from eios.ontology.auditor.normalizer import NumericTokenNormalizer

N = NumericTokenNormalizer()


def values(text: str) -> list[float]:
    return [x.normalized_value for x in N.extract_numbers(text)]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("spread moved 1.2 bps", [1.2]),
        ("churn within 5 months", [5.0]),
        ("revenue of $3.2M", [3_200_000.0]),
        ("revenue of 1.2 B", [1_200_000_000.0]),
        ("up 12%", [0.12]),
        ("a 4k balance", [4000.0]),
        ("14 connected sub-affiliates", [14.0]),
    ],
)
def test_suffixes_require_a_word_boundary(text, expected):
    assert values(text) == expected


@pytest.mark.parametrize(
    "text", ["### 2. Network Topology", "* 3. Item", "## 1. Overview\n### 2. Details"]
)
def test_markdown_heading_and_list_numbering_is_not_a_metric(text):
    assert values(text) == []
