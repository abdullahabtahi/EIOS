"""``config/gates.yaml``: the single definition of every blocking gate (data-model section 3)."""

from __future__ import annotations

import shlex
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from eios.common.errors import ConfigError
from eios.common.validation import StrictModel
from tools.common.yaml_io import load_yaml
from tools.gates._config_loading import ensure_unique, entries_from_data

Stage = Literal["pr", "merge", "promote", "release_candidate"]
THRESHOLD_TOKEN = "{threshold}"  # noqa: S105 - a placeholder name, not a credential
_GATE_ID = r"^[a-z][a-z0-9_-]*$"


class GateSpec(StrictModel):
    """One gate row. ``command`` holds one argv tuple per command; every one must exit 0."""

    id: Annotated[str, Field(pattern=_GATE_ID)]
    blocking: Literal[True]
    stage: Stage
    threshold: int | float | None = None
    proof_fixture: Annotated[str, Field(min_length=1)]
    command: tuple[tuple[str, ...], ...]

    @field_validator("command", mode="before")
    @classmethod
    def _split_commands(cls, value: object) -> object:
        if not isinstance(value, (list, tuple)):
            raise ValueError("command must be a list of command strings")
        parsed: list[tuple[str, ...]] = []
        for item in value:
            if isinstance(item, str):
                parsed.append(tuple(shlex.split(item)))
            else:
                parsed.append(tuple(item))
        return tuple(parsed)

    @model_validator(mode="after")
    def _commands_valid(self) -> GateSpec:
        if not self.command or any(not argv for argv in self.command):
            raise ValueError("command must hold at least one non-empty command")
        uses_threshold = any(THRESHOLD_TOKEN in token for argv in self.command for token in argv)
        if uses_threshold and self.threshold is None:
            raise ValueError("command uses {threshold} but the row has no threshold")
        return self


def load_gates(path: Path) -> tuple[GateSpec, ...]:
    """Load ``gates`` in file order; malformed rows and duplicate ids raise ConfigError."""
    document = load_yaml(path)
    if not isinstance(document, dict) or "gates" not in document:
        raise ConfigError(str(path), "$", "expected a mapping with a `gates` list")
    gates = entries_from_data(document["gates"], str(path), GateSpec, base_path="gates")
    ensure_unique(str(path), [g.id for g in gates], "gate id")
    return gates


def select_gates(gates: tuple[GateSpec, ...], stage: Stage) -> tuple[GateSpec, ...]:
    return tuple(g for g in gates if g.stage == stage)
