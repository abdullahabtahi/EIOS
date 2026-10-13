"""Conversational client bridge to gateway provider adapters."""

from __future__ import annotations

from eios.llm_gateway.providers.gemini_client import (
    DEFAULT_LOCATION,
    DEFAULT_MODEL,
    FALLBACK_MODEL,
    GeminiClientManager,
    genai,
    types,
)

__all__ = [
    "DEFAULT_LOCATION",
    "DEFAULT_MODEL",
    "FALLBACK_MODEL",
    "GeminiClientManager",
    "genai",
    "types",
]
