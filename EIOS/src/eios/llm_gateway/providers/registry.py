"""The models the assistant may run on, read from `assistant_models.yaml` (ADR-002: ids live in providers/ and config/).

The browser sees only `key`, `label`, `note` and which one is the default; the model id never leaves the server.
The default is the first entry unless the file or `EIOS_ASSISTANT_DEFAULT_MODEL` names another key.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_PATH = Path(__file__).with_name("assistant_models.yaml")


class UnknownModelError(ValueError):
    """The requested model key is not in the registry."""


@dataclass(frozen=True)
class ModelChoice:
    key: str
    id: str
    label: str
    note: str


@dataclass(frozen=True)
class ModelRegistry:
    choices: tuple[ModelChoice, ...]
    default_key: str

    def resolve(self, key: str | None) -> ModelChoice:
        wanted = key or self.default_key
        for choice in self.choices:
            if choice.key == wanted:
                return choice
        raise UnknownModelError(f"unknown model {wanted!r}")

    def public(self) -> list[dict[str, Any]]:
        return [
            {
                "key": c.key,
                "label": c.label,
                "note": c.note,
                "default": c.key == self.default_key,
            }
            for c in self.choices
        ]


def load_registry(env: Mapping[str, str] | None = None, path: Path = _PATH) -> ModelRegistry:
    source = os.environ if env is None else env
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    choices = tuple(ModelChoice(**entry) for entry in raw["models"])
    keys = [c.key for c in choices]
    if not choices or len(set(keys)) != len(keys):
        raise ValueError("assistant_models.yaml needs at least one model and unique keys")
    default = source.get("EIOS_ASSISTANT_DEFAULT_MODEL") or raw.get("default") or keys[0]
    registry = ModelRegistry(choices, default)
    registry.resolve(
        default
    )  # a default that names no model fails at startup, not on the first turn
    return registry
