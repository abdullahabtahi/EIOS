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
Schema = _types.Schema


def user_message(text: str) -> _types.Content:
    return _types.Content(role="user", parts=[_types.Part.from_text(text=text)])


def text_of(content: _types.Content | None) -> str:
    """All text parts of a model message joined, or an empty string; never raises on a missing message."""
    if content is None or not content.parts:
        return ""
    return "".join(part.text or "" for part in content.parts if not getattr(part, "thought", False))


def generation_config(
    *, temperature: float, max_output_tokens: int, thinking_level: str | None = None, **extra: Any
) -> _types.GenerateContentConfig:
    """Generation settings. Gemini 3.x counts thinking tokens against `max_output_tokens`, so callers cap
    the thinking level and leave room for the answer (a 256-token limit with LOW thinking was measured
    to leave 42 characters of text)."""
    if thinking_level is not None:
        extra["thinking_config"] = _types.ThinkingConfig(thinking_level=thinking_level)  # type: ignore[arg-type]
    return _types.GenerateContentConfig(
        temperature=temperature, max_output_tokens=max_output_tokens, **extra
    )


# ADK retries a model call twice by default; a quota error (429) on the shared project needs longer backoff.
# [ASSUMPTION] attempts and delays, to be tuned on the live run.
_RETRY = _types.HttpRetryOptions(
    attempts=5, initial_delay=2.0, max_delay=30.0, exp_base=2.0, jitter=1.0
)


def retrying_gemini(model_id: str) -> Gemini:
    """ADK's own Gemini model with its native retry policy (429, 5xx), instead of a hand-written retry loop."""
    return Gemini(model=model_id, retry_options=_RETRY)
