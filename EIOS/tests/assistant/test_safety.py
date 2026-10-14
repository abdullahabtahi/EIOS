"""Screening at the edges: a match or an unavailable service blocks the turn (spec 021 US6, FR-015)."""

import asyncio
from typing import Any

import pytest
from google.cloud import modelarmor_v1

from eios.assistant.config import AssistantConfigError, AssistantSettings
from eios.assistant.safety import INPUT_BLOCKED, OUTPUT_BLOCKED, build_safety_plugins
from eios.assistant.scripted_model import call, draft
from eios.ontology.omcp.port.principal import principal_for

from .conftest import make_runtime

PROMPT = "projects/p/locations/us-central1/templates/in"
RESPONSE = "projects/p/locations/us-central1/templates/out"
SETTINGS = AssistantSettings.from_env(
    {
        "EIOS_ENVIRONMENT": "test",
        "EIOS_MODEL_ARMOR_PROMPT_TEMPLATE": PROMPT,
        "EIOS_MODEL_ARMOR_RESPONSE_TEMPLATE": RESPONSE,
    }
)
FIGURE = "{{fact:aml.dossier:CR84920:discrepancy_multiplier}}"


def _result(match: bool, ok: bool = True) -> Any:
    state = (
        modelarmor_v1.FilterMatchState.MATCH_FOUND
        if match
        else modelarmor_v1.FilterMatchState.NO_MATCH_FOUND
    )
    invocation = (
        modelarmor_v1.InvocationResult.SUCCESS if ok else modelarmor_v1.InvocationResult.FAILURE
    )
    return modelarmor_v1.SanitizationResult(filter_match_state=state, invocation_result=invocation)


class FakeArmor:
    def __init__(
        self, *, block_input: bool = False, block_output: bool = False, fail: bool = False
    ) -> None:
        self.block_input, self.block_output, self.fail = block_input, block_output, fail
        self.screened_prompts: list[str] = []

    async def sanitize_user_prompt(self, *, request: Any) -> Any:
        if self.fail:
            raise ConnectionError("model armor unavailable")
        self.screened_prompts.append(request.user_prompt_data.text)
        return modelarmor_v1.SanitizeUserPromptResponse(
            sanitization_result=_result(self.block_input)
        )

    async def sanitize_model_response(self, *, request: Any) -> Any:
        if self.fail:
            raise ConnectionError("model armor unavailable")
        return modelarmor_v1.SanitizeModelResponseResponse(
            sanitization_result=_result(self.block_output)
        )


def _run(armor: FakeArmor, steps: list[Any]):
    runtime, llm = make_runtime(steps)
    runtime._plugins = build_safety_plugins(SETTINGS, client=armor)
    out = asyncio.run(
        runtime.run_turn(
            principal=principal_for("alice", "aml_investigator"),
            question="What is the discrepancy?",
            entity_id="CR84920",
        )
    )
    return out, llm


def test_a_clean_turn_is_screened_and_answered() -> None:
    armor = FakeArmor()
    out, _ = _run(armor, [call("get_aml_dossier", entity_id="CR84920"), draft(f"It is {FIGURE}.")])
    assert out.answer.blocked is False
    assert "16x" in out.answer.text
    assert armor.screened_prompts == ["What is the discrepancy?"]


def test_a_flagged_question_is_blocked_before_any_tool_runs() -> None:
    out, llm = _run(
        FakeArmor(block_input=True), [call("get_aml_dossier", entity_id="CR84920"), draft("x")]
    )
    assert out.answer.blocked is True
    assert out.answer.text == INPUT_BLOCKED
    assert out.answer.figures == ()
    assert out.tool_calls == ()
    assert llm.cursor == 0  # the model was never called


def test_a_flagged_model_output_is_blocked() -> None:
    out, _ = _run(
        FakeArmor(block_output=True),
        [call("get_aml_dossier", entity_id="CR84920"), draft(f"It is {FIGURE}.")],
    )
    assert out.answer.blocked is True
    assert out.answer.text == OUTPUT_BLOCKED
    assert out.answer.figures == ()


def test_an_unavailable_screening_service_blocks_instead_of_letting_content_through() -> None:
    out, llm = _run(FakeArmor(fail=True), [draft("anything")])
    assert out.answer.blocked is True
    assert llm.cursor == 0


def test_deployed_without_both_templates_refuses_to_start() -> None:
    deployed = AssistantSettings.from_env({"EIOS_ENVIRONMENT": "prod-like"})
    with pytest.raises(AssistantConfigError, match="MODEL_ARMOR"):
        build_safety_plugins(deployed)
    half = AssistantSettings.from_env(
        {"EIOS_ENVIRONMENT": "prod-like", "EIOS_MODEL_ARMOR_PROMPT_TEMPLATE": PROMPT}
    )
    with pytest.raises(AssistantConfigError, match="MODEL_ARMOR"):
        build_safety_plugins(half)


def test_locally_without_templates_there_is_no_screening_and_it_says_so() -> None:
    assert build_safety_plugins(AssistantSettings.from_env({"EIOS_ENVIRONMENT": "test"})) == ()
