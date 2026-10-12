"""Google Vertex AI Provider."""

import os
from collections.abc import Mapping
from typing import Any

from langchain_google_vertexai import VertexAI

from eios.llm_gateway.models import Count
from eios.llm_gateway.providers.base import ProviderResult, ProviderUnavailable


class VertexProvider:
    """Vertex AI GenAI provider implementation."""

    def __init__(self, project: str | None = None, location: str = "us-central1") -> None:
        self.project = project or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = location
        if not self.project:
            # Fallback for local dev if not set
            self.project = "default-eios-project"

    def generate(
        self, rendered_prompt: str, model_id: str | None, limits: Mapping[str, int]
    ) -> ProviderResult:
        """Generate response using Vertex AI via LangChain."""
        if not model_id:
            model_id = "gemini-3.8-flash"
            
        try:
            llm = VertexAI(
                model_name=model_id,
                project=self.project,
                location=self.location,
                max_output_tokens=limits.get("max_output_tokens", 2048),
                temperature=0.0, # Deterministic default
            )
            response = llm.invoke(rendered_prompt)
            # Depending on the response format, some metadata might be available.
            # We approximate token counts based on length if metadata isn't easily accessible.
            
            return ProviderResult(
                content=str(response),
                tokens_in=Count(len(rendered_prompt) // 4),
                tokens_out=Count(len(str(response)) // 4),
            )
        except Exception as e:
            raise ProviderUnavailable(f"Vertex AI API error: {e}") from e
