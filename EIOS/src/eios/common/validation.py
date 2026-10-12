"""Frozen, extra-forbidden base model and boundary validation that never echoes input values."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, ValidationError
from pydantic_core import ErrorDetails

from eios.common.errors import BoundaryValidationError

# Only short snake_case names are echoed as path segments. Anything else (for example an
# unknown dict key that is actually a secret) is replaced, because unknown keys are input data.
_SAFE_SEGMENT = re.compile(r"[a-z_][a-z0-9_]{0,63}")
_REDACTED_SEGMENT = "<redacted>"
_ROOT_PATH = "<root>"


class StrictModel(BaseModel):
    """Immutable base model that rejects unknown fields."""

    model_config = ConfigDict(frozen=True, extra="forbid")


def _segment(part: str | int) -> str:
    if isinstance(part, int):
        return str(part)
    return part if _SAFE_SEGMENT.fullmatch(part) else _REDACTED_SEGMENT


def _field_path(error: ErrorDetails) -> str:
    parts = [_segment(p) for p in error["loc"]]
    return ".".join(parts) if parts else _ROOT_PATH


def _describe(errors: list[ErrorDetails]) -> tuple[tuple[str, ...], str]:
    paths = tuple(dict.fromkeys(_field_path(e) for e in errors))
    detail = "; ".join(f"{_field_path(e)} ({e['type']})" for e in errors)
    return paths, detail


def validate_at_boundary[M: StrictModel](model: type[M], data: object) -> M:
    """Validate untrusted ``data`` into ``model``.

    Raises BoundaryValidationError listing field paths and error types only. Rejected input
    values are never included, whether or not they look like secrets.
    """
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        paths, detail = _describe(exc.errors(include_input=False, include_url=False))
        raise BoundaryValidationError(f"{model.__name__} rejected input: {detail}", paths) from None
