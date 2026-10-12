"""Gate hook registry (``evals/registry.yaml``): entry rules and the tier-by-workflow matrix.

Rules come from contracts/gate-hook-registry.md. A malformed registry raises ConfigError
before any suite runs.
"""

from __future__ import annotations

import shlex
from collections.abc import Mapping
from enum import StrEnum
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Annotated

from pydantic import Field, field_validator

from eios.common.validation import StrictModel
from tools.gates._config_loading import ensure_unique, load_entries
from tools.gates.run_record import Workflow

REPORT_ROOT = PurePosixPath("evals/reports")
_KEBAB = r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$"
_OWNER = r"^F[0-9]{2}$"


class Tier(StrEnum):
    CONTRACT = "contract"
    EVAL_SMOKE = "eval_smoke"
    RED_LINE = "red_line"
    VALIDATION = "validation"
    SEALED = "sealed"


_ALWAYS = frozenset({Tier.CONTRACT, Tier.EVAL_SMOKE, Tier.RED_LINE})
_PROMOTION = _ALWAYS | {Tier.VALIDATION}

# Sealed suites run only under the release-candidate workflow identity (Constitution VI).
TIERS_BY_WORKFLOW: Mapping[Workflow, frozenset[Tier]] = MappingProxyType(
    {
        Workflow.PR: _ALWAYS,
        Workflow.PROMOTE_STAGE: _PROMOTION,
        Workflow.PROMOTE_PROD_LIKE: _PROMOTION,
        Workflow.RELEASE_CANDIDATE: frozenset(Tier),
    }
)


def tier_runs_in(tier: Tier, workflow: Workflow) -> bool:
    return tier in TIERS_BY_WORKFLOW[workflow]


class SuiteEntry(StrictModel):
    """One registered evaluation suite."""

    id: Annotated[str, Field(pattern=_KEBAB)]
    tier: Tier
    command: tuple[str, ...]
    owner_feature: Annotated[str, Field(pattern=_OWNER)]
    report: str

    @field_validator("command", mode="before")
    @classmethod
    def _split_command(cls, value: object) -> object:
        if isinstance(value, str):
            try:
                return tuple(shlex.split(value))
            except ValueError as exc:
                raise ValueError(f"command cannot be split: {exc}") from exc
        if isinstance(value, list):
            return tuple(value)
        return value

    @field_validator("command")
    @classmethod
    def _command_non_empty(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value or any(not token.strip() for token in value):
            raise ValueError("command must be non-empty with no blank tokens")
        return value

    @field_validator("report")
    @classmethod
    def _report_under_reports(cls, value: str) -> str:
        path = PurePosixPath(value)
        under_root = path.parts[:2] == REPORT_ROOT.parts and len(path.parts) > 2
        clean = not path.is_absolute() and ".." not in path.parts and not value.endswith("/")
        if not (under_root and clean):
            raise ValueError("report must be a file path under evals/reports/")
        return value


def load_registry(path: Path) -> tuple[SuiteEntry, ...]:
    """Load and validate every entry; duplicates and malformed entries raise ConfigError."""
    entries = load_entries(path, SuiteEntry)
    ensure_unique(str(path), [e.id for e in entries], "suite id")
    return entries
