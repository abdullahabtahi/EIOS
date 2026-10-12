"""Overlay: a return type the strict checker rejects."""

from __future__ import annotations


def broken() -> int:
    return "not an int"
