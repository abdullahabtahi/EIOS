from dataclasses import replace

import pytest

from eios.assistant.config import AssistantSettings
from eios.assistant.runtime import AssistantRuntime
from eios.assistant.scripted_model import ScriptedLlm, Step
from eios.assistant.sessions import build_session_service
from eios.ontology.omcp.port.catalogue import build_port
from eios.ontology.omcp.port.readmodels import ReadModels

SETTINGS = AssistantSettings.from_env(
    {"EIOS_ENVIRONMENT": "test", "EIOS_ASSISTANT_TURN_DEADLINE_S": "10"}
)


def make_runtime(
    steps: list[Step], settings: AssistantSettings = SETTINGS, sessions=None, knowledge=None
) -> tuple[AssistantRuntime, ScriptedLlm]:
    models = replace(ReadModels.default(), knowledge=knowledge)
    port = build_port(models)
    llm = ScriptedLlm(steps=steps)
    runtime = AssistantRuntime(
        port=port,
        settings=settings,
        session_service=sessions or build_session_service(settings),
        model=llm,
    )
    return runtime, llm


@pytest.fixture
def factory():
    return make_runtime
