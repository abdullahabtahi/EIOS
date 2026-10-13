"""A model that is not frozen: only the repo_checks gate rejects it."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Counter:
    value: int
