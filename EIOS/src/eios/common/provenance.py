"""Provenance tag vocabulary: the only bracketed labels a figure or claim may carry."""

from __future__ import annotations

from enum import StrEnum

from eios.common.errors import BoundaryValidationError


class Tag(StrEnum):
    BRIEF = "[BRIEF]"
    ASSUMPTION = "[ASSUMPTION]"
    ILLUSTRATIVE = "[ILLUSTRATIVE]"
    TARGET = "[TARGET]"
    SPIKE = "[SPIKE]"


_BY_VALUE: dict[str, Tag] = {tag.value: tag for tag in Tag}
_UNVERIFIED: frozenset[Tag] = frozenset({Tag.SPIKE})


def parse_tag(text: str) -> Tag:
    """Parse an exact tag token; anything else is rejected."""
    if not isinstance(text, str):
        raise BoundaryValidationError("provenance tag must be a string")
    tag = _BY_VALUE.get(text)
    if tag is None:
        allowed = ", ".join(_BY_VALUE)
        raise BoundaryValidationError(f"unknown provenance tag; allowed tags: {allowed}")
    return tag


def is_unverified(tag: Tag) -> bool:
    """True when the tag marks a claim that is unverified until a spike closes."""
    return tag in _UNVERIFIED
