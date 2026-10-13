"""Google GenAI unified client implementation under LLM Gateway providers (ADR-002 compliant)."""

from __future__ import annotations

import logging
import os

from google import genai
from google.genai import types

_LOG = logging.getLogger("eios.llm_gateway.providers.gemini_client")

# Gemini 3.x models are served from the `global` Vertex AI endpoint; regional endpoints return 404.
DEFAULT_LOCATION = "global"
DEFAULT_MODEL = "gemini-3.8-flash"
FALLBACK_MODEL = "gemini-3.7-flash"


class GeminiClientManager:
    """Manages Vertex AI client connections, model fallbacks, and context caching."""

    def __init__(
        self,
        project: str | None = None,
        location: str | None = None,
        model_id: str | None = None,
        offline_mode: bool = False,
    ) -> None:
        self.project = project or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = location or os.getenv("GOOGLE_CLOUD_LOCATION", DEFAULT_LOCATION)
        self.model_id = model_id or os.getenv("EIOS_GEMINI_MODEL", DEFAULT_MODEL)
        self.fallback_model_id = FALLBACK_MODEL
        self.offline_mode = offline_mode or (os.getenv("EIOS_OFFLINE_REPLAY", "0") == "1")
        self.offline_reason: str | None = (
            "offline replay mode requested" if self.offline_mode else None
        )
        self._client: genai.Client | None = None
        self._active_cache_name: str | None = None

    def get_client(self) -> genai.Client | None:
        """Initializes and returns the unified google.genai client."""
        if self.offline_mode:
            return None

        if self._client is None:
            if not self.project:
                self.offline_reason = "GOOGLE_CLOUD_PROJECT is not set; live Gemini is unavailable"
                _LOG.warning(self.offline_reason)
                self.offline_mode = True
                return None
            try:
                self._client = genai.Client(
                    vertexai=True,
                    project=self.project,
                    location=self.location,
                )
                _LOG.info(
                    "Initialized client for project=%s in location=%s", self.project, self.location
                )
            except Exception as e:
                _LOG.warning("Failed to initialize client, falling back to offline replay: %s", e)
                self.offline_reason = f"Gemini client initialisation failed: {e}"
                self.offline_mode = True
                return None

        return self._client

    def ensure_context_cache(
        self, system_instruction: str, ontology_schema_text: str
    ) -> str | None:
        """Creates or returns a cached context bundle on the backend provider."""
        if self.offline_mode or not self.get_client():
            return None

        if self._active_cache_name:
            return self._active_cache_name

        try:
            client = self.get_client()
            if client is None:
                return None

            cache = client.caches.create(
                model=self.model_id,
                config=types.CreateCachedContentConfig(
                    contents=[
                        f"SYSTEM INSTRUCTIONS:\n{system_instruction}\n\n"
                        f"ONTOLOGY & SEMANTIC REGISTRY SCHEMAS:\n{ontology_schema_text}"
                    ],
                    ttl="7200s",
                    display_name="feios_sovereign_context_cache",
                ),
            )
            self._active_cache_name = cache.name
            _LOG.info("Successfully established context cache: %s", self._active_cache_name)
            return self._active_cache_name
        except Exception as e:
            _LOG.warning(
                "Context caching initialization encountered an error (continuing without cache): %s",
                e,
            )
            return None
