"""Input and output screening with ADK's Model Armor plugin (spec 021 US6, FR-015).

Screening a prompt or a response that matches a filter replaces it with a fixed message and the turn is reported as
blocked. If the screening service fails the turn is blocked too, never passed through. The plugin screens what the
operator types and what the model writes; tool results are not screened by it (the port tags text that came from
outside as untrusted instead). Deployed environments must name both templates, or the service will not start.
"""

from __future__ import annotations

from typing import Any

from google.adk.agents.callback_context import CallbackContext
from google.adk.integrations.model_armor import ModelArmorConfig, ModelArmorPlugin
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.plugins.base_plugin import BasePlugin

from eios.assistant.config import AssistantConfigError, AssistantSettings

INPUT_BLOCKED = "I can't help with that request."
OUTPUT_BLOCKED = "I can't share that answer. Please rephrase the question."
BLOCKED_METADATA_KEY = "model_armor_blocked"
SCREENED_KEY = "temp:input_screened"


class ScreenOncePerTurn(ModelArmorPlugin):
    """ADK's plugin screens the latest user text before every model call: tool rounds and retries would screen the
    same question again and spend the turn's latency budget. A pass is remembered in the turn's own state (so nothing
    outlives the turn), and only a pass: a block or a failure of the screening service still blocks.
    """

    async def before_model_callback(
        self, *, callback_context: CallbackContext, llm_request: LlmRequest
    ) -> LlmResponse | None:
        if callback_context.state.get(SCREENED_KEY):
            return None
        blocked = await super().before_model_callback(
            callback_context=callback_context, llm_request=llm_request
        )
        if blocked is None:
            callback_context.state[SCREENED_KEY] = True
        return blocked


def build_safety_plugins(
    settings: AssistantSettings, *, client: Any = None
) -> tuple[BasePlugin, ...]:
    prompt, response = settings.prompt_template, settings.response_template
    if prompt and response:
        config = ModelArmorConfig(
            prompt_template_name=prompt,
            response_template_name=response,
            input_blocked_message=INPUT_BLOCKED,
            output_blocked_message=OUTPUT_BLOCKED,
            block_on_screening_failure=True,
        )
        return (ScreenOncePerTurn(config=config, client=client),)
    if settings.local and not (prompt or response):
        return ()  # dev and test run unscreened by design; the live gates cover screening
    raise AssistantConfigError(
        "EIOS_MODEL_ARMOR_PROMPT_TEMPLATE and EIOS_MODEL_ARMOR_RESPONSE_TEMPLATE must both be set "
        f"in the '{settings.environment}' environment; refusing to run the assistant unscreened"
    )
