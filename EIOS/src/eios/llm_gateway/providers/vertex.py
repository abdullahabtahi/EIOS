"""Google Gemini provider on Vertex AI, via the unified google-genai SDK."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

from google import genai
from google.genai import errors, types

from eios.llm_gateway.models import Count
from eios.llm_gateway.providers.base import (
    ProviderOutputInvalid,
    ProviderResult,
    ProviderUnavailable,
)

# Gemini 3.x is served from the global endpoint; regional endpoints return 404.
DEFAULT_LOCATION = "global"
DEFAULT_MAX_OUTPUT_TOKENS = 2048
# Thinking tokens count against max_output_tokens; unbounded thinking can leave an empty answer.
THINKING_LEVEL = types.ThinkingLevel.LOW


class VertexProvider:
    """Vertex AI provider. No default model: the gateway config supplies ``model_id``."""

    def __init__(self, project: str | None = None, location: str | None = None) -> None:
        self.project = project or os.getenv("GOOGLE_CLOUD_PROJECT")
        if not self.project:
            raise ProviderUnavailable("GOOGLE_CLOUD_PROJECT is not set; Vertex AI is unavailable")
        self.location = location or os.getenv("GOOGLE_CLOUD_LOCATION", DEFAULT_LOCATION)
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            self._client = genai.Client(vertexai=True, project=self.project, location=self.location)
        return self._client

    def generate(
        self, rendered_prompt: str, model_id: str | None, limits: Mapping[str, int]
    ) -> ProviderResult:
        if not model_id:
            raise ProviderUnavailable("model_id is required for the Vertex provider")
        try:
            response = self._get_client().models.generate_content(
                model=model_id,
                contents=rendered_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    thinking_config=types.ThinkingConfig(thinking_level=THINKING_LEVEL),
                    max_output_tokens=limits.get("max_output_tokens", DEFAULT_MAX_OUTPUT_TOKENS),
                ),
            )
        except errors.APIError as exc:
            raise ProviderUnavailable(f"Vertex AI API error {exc.code}") from exc
        usage = response.usage_metadata
        if not response.text:
            raise ProviderOutputInvalid("Vertex AI returned an empty answer")
        return ProviderResult(
            content=response.text,
            tokens_in=Count(getattr(usage, "prompt_token_count", None) or 0),
            tokens_out=Count(getattr(usage, "candidates_token_count", None) or 0),
        )
