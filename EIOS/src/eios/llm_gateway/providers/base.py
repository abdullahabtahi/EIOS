"""Provider protocol, result type and typed provider errors.

Provider output is untrusted: ``parse_provider_result`` is the boundary every adapter's raw
payload crosses, and its errors never echo the payload.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from eios.common.errors import BoundaryValidationError, EiosError
from eios.common.validation import StrictModel, validate_at_boundary
from eios.llm_gateway.models import Count


class ProviderUnavailable(EiosError):
    """The provider is down or erroring. The gateway degrades to replay or ``unavailable``."""


class ProviderTimeout(ProviderUnavailable):
    """The provider did not answer in time."""


class ProviderOutputInvalid(EiosError):
    """The provider answered with something that is not a valid result."""


class ProviderResult(StrictModel):
    content: str
    tokens_in: Count
    tokens_out: Count


@runtime_checkable
class Provider(Protocol):
    """Turns a rendered prompt into text. ``model_id`` is None only in dev stub runs."""

    def generate(
        self, rendered_prompt: str, model_id: str | None, limits: Mapping[str, int]
    ) -> ProviderResult: ...


def parse_provider_result(raw: object) -> ProviderResult:
    """Validate a raw provider payload, or pass through an already valid result."""
    if isinstance(raw, ProviderResult):
        return raw
    try:
        return validate_at_boundary(ProviderResult, raw)
    except BoundaryValidationError as exc:
        paths = ", ".join(exc.field_paths) or "<root>"
        raise ProviderOutputInvalid(f"provider output rejected at: {paths}") from None
