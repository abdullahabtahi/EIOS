"""Safe YAML loading and JSON Schema validation; every error names file and path."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

from eios.common.errors import ConfigError

_ROOT = "$"


def _format_path(parts: tuple[str | int, ...]) -> str:
    """Render a JSON path as ``gates[0].threshold``; the root is ``$``."""
    out = ""
    for part in parts:
        out += f"[{part}]" if isinstance(part, int) else (f".{part}" if out else str(part))
    return out or _ROOT


def load_yaml(path: Path) -> object:
    """Parse ``path`` with ``yaml.safe_load`` only; failures become ``ConfigError``."""
    file = str(path)
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ConfigError(file, _ROOT, f"cannot read file: {exc}") from exc
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigError(file, _ROOT, f"invalid YAML: {_describe_yaml_error(exc)}") from exc


def _describe_yaml_error(exc: yaml.YAMLError) -> str:
    mark = getattr(exc, "problem_mark", None)
    problem = getattr(exc, "problem", None) or "syntax error"
    if mark is None:
        return str(problem)
    return f"{problem} at line {mark.line + 1}, column {mark.column + 1}"


def _violations(data: object, schema: Mapping[str, object]) -> list[ValidationError]:
    Draft202012Validator.check_schema(dict(schema))
    validator = Draft202012Validator(dict(schema))
    return sorted(
        validator.iter_errors(data),
        key=lambda e: (_format_path(tuple(e.absolute_path)), e.message),
    )


def load_validated(path: Path, schema: Mapping[str, object]) -> object:
    """Load ``path`` safely and validate it against ``schema``.

    Raises ``ConfigError`` for the first violation's path, listing every violation.
    """
    data = load_yaml(path)
    file = str(path)
    try:
        errors = _violations(data, schema)
    except SchemaError as exc:
        raise ConfigError(file, _ROOT, f"invalid schema supplied: {exc.message}") from exc
    if not errors:
        return data
    lines = [f"{_format_path(tuple(e.absolute_path))}: {e.message}" for e in errors]
    first_path = _format_path(tuple(errors[0].absolute_path))
    raise ConfigError(file, first_path, "schema violations: " + "; ".join(lines))
