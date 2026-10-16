"""Questions that judge people by who they are are refused before the model runs, so no tool is ever read for them.

Geography is evidence about behaviour (a shared exit, a jump no flight could make, money through a listed
jurisdiction), never about a person's nationality, ethnicity, race or religion. The geo instructions already say so,
but a live run showed the model sometimes reads the overview first and refuses after; a question like "which
nationality launders the most" should not be handed a result to answer from at all. This is an ADK
`before_model_callback` on the drafter: returning a response skips the model call, so the refusal costs no tokens,
calls no tool, and is the same every time.
"""

from __future__ import annotations

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse

from eios.assistant.geo_context import asks_about_origin
from eios.llm_gateway.providers.adk_types import Content, Part, text_of

GUARDED = "eios_guarded"  # event metadata: a response the platform wrote in place of the model
REFUSAL = (
    "I cannot answer that: I don't rank or judge people by nationality, ethnicity, race or religion. Geography here "
    "is evidence about "
    "behaviour, never about who someone is. I can show which corridors, shared exits or accounts behave unusually, "
    "and why."
)


def refuse_by_origin(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> LlmResponse | None:
    """The refusal as the model's answer when the question asks about people by origin; otherwise the model runs."""
    if not asks_about_origin(text_of(callback_context.user_content)):
        return None
    return LlmResponse(
        content=Content(role="model", parts=[Part(text=REFUSAL)]),
        custom_metadata={GUARDED: True},  # the platform answered: not a model call
    )
