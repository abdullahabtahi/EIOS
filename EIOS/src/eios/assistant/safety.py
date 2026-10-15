"""Input and output screening with ADK's Model Armor plugin (spec 021 US6, FR-015).

Screening a prompt or a response that matches a filter replaces it with a fixed message and the turn is reported as
blocked. If the screening service fails the turn is blocked too, never passed through. The plugin screens what the
operator types and what the model writes; tool results are not screened by it (the port tags text that came from
outside as untrusted instead). Deployed environments must name both templates, or the service will not start.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from google.adk.agents.callback_context import CallbackContext
from google.adk.integrations.model_armor import ModelArmorConfig, ModelArmorPlugin
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.plugins.base_plugin import BasePlugin

from eios.assistant.config import AssistantConfigError, AssistantSettings
from eios.assistant.timing import current_timer

_LOG = logging.getLogger(__name__)
INPUT_BLOCKED = "I can't help with that request."
OUTPUT_BLOCKED = "I can't share that answer. Please rephrase the question."
BLOCKED_METADATA_KEY = "model_armor_blocked"
SCREENED_KEY = "temp:input_screened"


def _record(started: float) -> None:
    timer = current_timer()
    if timer is not None:
        timer.screen_calls_ms.append((time.perf_counter() - started) * 1000)


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
        started = time.perf_counter()
        try:
            blocked = await super().before_model_callback(
                callback_context=callback_context, llm_request=llm_request
            )
        finally:
            _record(started)
        if blocked is None:
            callback_context.state[SCREENED_KEY] = True
        return blocked

    async def after_model_callback(
        self, *, callback_context: CallbackContext, llm_response: LlmResponse
    ) -> LlmResponse | None:
        started = time.perf_counter()
        try:
            return await super().after_model_callback(
                callback_context=callback_context, llm_response=llm_response
            )
        finally:
            _record(started)

    async def warm_up(self) -> None:
        """Open the screening connection before the first operator turn. The service channel and credentials are
        created on first use, which costs the first turn several seconds. A fixed text is sent, never operator
        text. A failure here is logged and ignored: the first real turn still blocks if screening is down."""
        template = self._config.prompt_template_name
        if not template:
            return
        try:
            await self._sanitize_user_prompt("warm up", template)
        except Exception:
            _LOG.warning("Model Armor warm-up failed; the first turn will retry", exc_info=True)


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
