"""Deterministic stub provider: canned or hash-derived responses and configurable failure."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from enum import StrEnum
from types import MappingProxyType

from eios.llm_gateway.providers.base import (
    ProviderResult,
    ProviderTimeout,
    ProviderUnavailable,
    parse_provider_result,
)


class StubFailure(StrEnum):
    NONE = "none"
    UNAVAILABLE = "unavailable"
    TIMEOUT = "timeout"
    MALFORMED = "malformed"


def _words(text: str) -> int:
    return len(text.split())


@dataclass(frozen=True)
class StubProvider:
    """No network, no randomness. Identical prompts always produce identical results."""

    canned: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))
    failure: StubFailure = StubFailure.NONE

    def __post_init__(self) -> None:
        # Frozen dataclass: the one sanctioned write, so callers cannot alias the mapping.
        object.__setattr__(self, "canned", MappingProxyType(dict(self.canned)))

    def with_failure(self, failure: StubFailure) -> StubProvider:
        return replace(self, failure=failure)

    def with_canned(self, prompt: str, response: str) -> StubProvider:
        return replace(self, canned=MappingProxyType({**self.canned, prompt: response}))

    def generate(
        self, rendered_prompt: str, model_id: str | None, limits: Mapping[str, int]
    ) -> ProviderResult:
        if self.failure is StubFailure.UNAVAILABLE:
            raise ProviderUnavailable("stub provider configured as unavailable")
        if self.failure is StubFailure.TIMEOUT:
            raise ProviderTimeout("stub provider configured to time out")
        if self.failure is StubFailure.MALFORMED:
            return parse_provider_result({"content": rendered_prompt, "tokens_in": "malformed"})
        content = self.canned.get(rendered_prompt) or _derived(rendered_prompt)
        return ProviderResult(
            content=content, tokens_in=_words(rendered_prompt), tokens_out=_words(content)
        )


def _derived(rendered_prompt: str) -> str:
    digest = hashlib.sha256(rendered_prompt.encode("utf-8")).hexdigest()[:16]
    return f"stub response {digest}"
