"""Small typed arithmetic helpers; every branch is exercised by tests/test_calc.py."""

from __future__ import annotations


def add(left: int, right: int) -> int:
    return left + right


def clamp(value: int, low: int, high: int) -> int:
    if low > high:
        raise ValueError("low must not exceed high")
    if value < low:
        return low
    if value > high:
        return high
    return value


def mean(values: list[int]) -> float:
    if not values:
        raise ValueError("values must not be empty")
    return sum(values) / len(values)
