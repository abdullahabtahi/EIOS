"""Shared types and parameter helpers for the open-decision rule kinds.

A rule kind builds a ``CompiledRule`` from a ``RuleSpec``: the checker itself plus the file
selection it wants. ``include`` is a tuple of path globs (``**`` spans directories); ``None``
means the default scan scope of ``config/open_decisions.yaml``. ``exclude`` removes paths from
a rule that declared its own ``include``.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import PurePosixPath

from eios.common.errors import ConfigError
from tools.open_decision_check.config import CONFIG_PATH, RuleSpec


@dataclass(frozen=True, slots=True)
class SourceFile:
    """A scanned file: repo-relative POSIX path and its text ("" when it is not UTF-8)."""

    path: str
    text: str


@dataclass(frozen=True, slots=True)
class Hit:
    """One place a rule fired; the engine adds the decision and rule id."""

    file: str
    line: int
    message: str


type Checker = Callable[[Sequence[SourceFile]], tuple[Hit, ...]]


@dataclass(frozen=True, slots=True)
class CompiledRule:
    check: Checker
    include: tuple[str, ...] | None = None
    exclude: tuple[str, ...] = ()


def string_list(
    spec: RuleSpec, key: str, *, default: Sequence[str] | None = None
) -> tuple[str, ...]:
    """A non-empty list of non-empty strings from the rule's parameters.

    Without ``default`` the parameter is required.
    """
    where = f"{spec.where}.{key}"
    value = spec.params.get(key)
    if value is None and default is not None:
        return tuple(default)
    if not isinstance(value, list) or not value:
        raise ConfigError(CONFIG_PATH, where, f"rule kind {spec.kind!r} needs a non-empty list")
    for position, item in enumerate(value):
        if not isinstance(item, str) or not item:
            raise ConfigError(CONFIG_PATH, f"{where}[{position}]", "expected a non-empty string")
    return tuple(value)


def compiled(
    spec: RuleSpec, check: Checker, default_include: Sequence[str] | None = None
) -> CompiledRule:
    """Wrap ``check`` with the rule's own ``include``/``exclude`` (or the kind's default)."""
    own = spec.params.get("include")
    include = string_list(spec, "include") if own is not None else None
    if include is None and default_include is not None:
        include = tuple(default_include)
    exclude = string_list(spec, "exclude") if spec.params.get("exclude") is not None else ()
    return CompiledRule(check, include, exclude)


def path_matches(path: str, globs: Sequence[str]) -> bool:
    """True when the repo-relative POSIX ``path`` matches any glob (``**`` spans directories)."""
    return any(PurePosixPath(path).full_match(glob) for glob in globs)
