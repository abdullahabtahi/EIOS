"""Shared helpers for gate-related config files: list loading with entry-path errors."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from eios.common.errors import BoundaryValidationError, ConfigError
from eios.common.validation import StrictModel, validate_at_boundary
from tools.common.yaml_io import load_yaml


def load_entries[M: StrictModel](
    path: Path,
    model: type[M],
    prepare: Callable[[dict[str, object]], dict[str, object]] | None = None,
) -> tuple[M, ...]:
    """Load a YAML list of mappings, validating each entry into ``model``.

    An empty document (comments only) is an empty list. Errors name the file and the entry path.
    """
    data = load_yaml(path)
    return entries_from_data(data, str(path), model, prepare)


def entries_from_data[M: StrictModel](
    data: object,
    file: str,
    model: type[M],
    prepare: Callable[[dict[str, object]], dict[str, object]] | None = None,
    base_path: str = "$",
) -> tuple[M, ...]:
    if data is None:
        return ()
    if not isinstance(data, list):
        raise ConfigError(file, base_path, "expected a list of entries")
    entries: list[M] = []
    for index, raw in enumerate(data):
        entry_path = f"{base_path}[{index}]" if base_path != "$" else f"[{index}]"
        if not isinstance(raw, dict):
            raise ConfigError(file, entry_path, "each entry must be a mapping")
        try:
            prepared = prepare(raw) if prepare else raw
            entries.append(validate_at_boundary(model, prepared))
        except BoundaryValidationError as exc:
            raise ConfigError(file, entry_path, exc.message) from None
    return tuple(entries)


def ensure_unique(file: str, ids: list[str], what: str) -> None:
    seen: set[str] = set()
    for index, value in enumerate(ids):
        if value in seen:
            raise ConfigError(file, f"[{index}]", f"duplicate {what} {value!r}")
        seen.add(value)
