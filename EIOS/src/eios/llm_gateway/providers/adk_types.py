"""The model-facing message types ADK needs, re-exported so the assistant never imports a vendor SDK (ADR-002).

`open_decision_check` allows vendor SDK imports only under `llm_gateway/providers/`; the assistant builds the
`Content` for a turn and reads parts back through these helpers.
"""

from __future__ import annotations

from typing import Any

from google.adk.models.google_llm import Gemini
from google.genai import types as _types

Content = _types.Content
Part = _types.Part
GenerateContentConfig = _types.GenerateContentConfig
FunctionDeclaration = _types.FunctionDeclaration
HttpRetryOptions = _types.HttpRetryOptions
Schema = _types.Schema


def user_message(text: str) -> _types.Content:
    return _types.Content(role="user", parts=[_types.Part.from_text(text=text)])


def text_of(content: _types.Content | None) -> str:
    """All text parts of a model message joined, or an empty string; never raises on a missing message."""
    if content is None or not content.parts:
        return ""
    return "".join(part.text or "" for part in content.parts if not getattr(part, "thought", False))


def generation_config(
    *,
    temperature: float,
    max_output_tokens: int,
    thinking_level: str | None = None,
    **extra: Any,
) -> _types.GenerateContentConfig:
    """Generation settings. Gemini 3.x counts thinking tokens against `max_output_tokens`, so callers cap
    the thinking level and leave room for the answer (a 256-token limit with LOW thinking was measured
    to leave 42 characters of text)."""
    if thinking_level is not None:
        extra["thinking_config"] = _types.ThinkingConfig(thinking_level=thinking_level)  # type: ignore[arg-type]
    return _types.GenerateContentConfig(
        temperature=temperature, max_output_tokens=max_output_tokens, **extra
    )


def retrying_gemini(model_id: str, retry: _types.HttpRetryOptions) -> Gemini:
    """ADK's own Gemini model with its native retry policy (429, 5xx, a request that timed out), instead of a
    hand-written retry loop. The caller states the policy because it must fit inside the turn's deadline."""
    return Gemini(model=model_id, retry_options=retry)
