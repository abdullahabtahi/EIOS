from __future__ import annotations

import pytest

from skeleton.calc import add, clamp, mean


def test_add() -> None:
    assert add(2, 3) == 5


def test_clamp_inside_and_outside_the_range() -> None:
    assert clamp(5, 0, 10) == 5
    assert clamp(-1, 0, 10) == 0
    assert clamp(11, 0, 10) == 10


def test_clamp_rejects_an_inverted_range() -> None:
    with pytest.raises(ValueError, match="low must not exceed high"):
        clamp(1, 2, 1)


def test_mean() -> None:
    assert mean([1, 2, 3]) == 2.0


def test_mean_rejects_empty_input() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        mean([])
