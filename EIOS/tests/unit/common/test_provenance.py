"""T011: provenance tag vocabulary is closed and SPIKE is unverified."""

from __future__ import annotations

import pytest

from eios.common.errors import BoundaryValidationError
from eios.common.provenance import Tag, is_unverified, parse_tag

_EXPECTED = {"[BRIEF]", "[ASSUMPTION]", "[ILLUSTRATIVE]", "[TARGET]", "[SPIKE]"}


def test_vocabulary_is_exactly_the_five_tags() -> None:
    assert {t.value for t in Tag} == _EXPECTED
    assert len(Tag) == 5


@pytest.mark.parametrize("value", sorted(_EXPECTED))
def test_parse_accepts_each_tag(value: str) -> None:
    assert parse_tag(value).value == value


@pytest.mark.parametrize(
    "text",
    ["[FOO]", "[brief]", "BRIEF", "", "[BRIEF", "[BRIEF] ", " [BRIEF]", "[BRIEF][SPIKE]", "[]"],
)
def test_parse_rejects_anything_else(text: str) -> None:
    with pytest.raises(BoundaryValidationError):
        parse_tag(text)


def test_parse_rejects_non_string() -> None:
    with pytest.raises(BoundaryValidationError):
        parse_tag(None)  # type: ignore[arg-type]


def test_only_spike_is_unverified() -> None:
    assert is_unverified(Tag.SPIKE) is True
    assert [t for t in Tag if is_unverified(t)] == [Tag.SPIKE]
