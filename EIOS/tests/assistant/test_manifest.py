"""The orchestration manifest: what produced an answer, recorded with it so a later reader can tell whether it still would."""

import asyncio

from eios.assistant.agents import instruction_digest
from eios.assistant.config import AssistantSettings
from eios.assistant.manifest import MANIFEST_SCHEMA, build_manifest, toolset_digest
from eios.assistant.scripted_model import call, draft
from eios.evidence.bundle import intact, seal
from eios.ontology.omcp.port.catalogue import build_port
from eios.ontology.omcp.port.principal import Workstation, principal_for
from eios.ontology.omcp.port.readmodels import ReadModels

from .conftest import make_runtime

SETTINGS = AssistantSettings.from_env({"EIOS_ENVIRONMENT": "test"})
PORT = build_port(ReadModels.default())
AML = principal_for("alice", "aml_investigator")


def _manifest(principal=AML, settings=SETTINGS, model_key="fast", model_id="a-model"):
    return build_manifest(
        principal=principal,
        tools=PORT.list_tools(principal),
        settings=settings,
        model_key=model_key,
        model_id=model_id,
    )


def test_the_instruction_digest_is_stable_and_follows_the_text() -> None:
    first = instruction_digest(Workstation.AML_INVESTIGATOR, plain_figures=True, history_turns=6)
    assert first == instruction_digest(
        Workstation.AML_INVESTIGATOR, plain_figures=True, history_turns=6
    )
    assert len(first) == 64
    assert first != instruction_digest(
        Workstation.AML_INVESTIGATOR, plain_figures=False, history_turns=6
    )
    assert first != instruction_digest(Workstation.GEOSPATIAL, plain_figures=True, history_turns=6)


def test_the_toolset_digest_changes_with_the_tools_offered() -> None:
    aml = toolset_digest(PORT.list_tools(AML))
    assert aml == toolset_digest(list(reversed(PORT.list_tools(AML))))  # order is not content
    assert aml != toolset_digest(PORT.list_tools(principal_for("alice", "executive")))


def test_the_manifest_names_what_produced_the_answer() -> None:
    m = _manifest()
    assert m["schema"] == MANIFEST_SCHEMA
    assert m["workstation"] == "aml_investigator"
    assert m["model"] == {"key": "fast", "id": "a-model"}
    assert m["adk_version"]
    assert m["instruction_sha256"] == instruction_digest(
        Workstation.AML_INVESTIGATOR, SETTINGS.plain_figures, SETTINGS.history_turns
    )
    assert m["toolset"]["count"] == len(PORT.list_tools(AML))
    assert m["toolset"]["sha256"] == toolset_digest(PORT.list_tools(AML))
    assert m["assembly"]["plain_figures"] is SETTINGS.plain_figures
    assert m["limits"]["turn_deadline_s"] == SETTINGS.turn_deadline_s


def test_a_changed_setting_or_model_changes_the_manifest() -> None:
    base = _manifest()
    other = AssistantSettings.from_env(
        {"EIOS_ENVIRONMENT": "test", "EIOS_ASSISTANT_PLAIN_FIGURES": "0"}
    )
    assert _manifest(settings=other) != base
    assert _manifest(model_id="another-model") != base
    assert _manifest() == base


def test_the_manifest_is_part_of_what_a_bundle_hashes() -> None:
    sealed = seal(
        workstation="aml_investigator",
        operator_id="alice",
        question="q",
        answer={"text": "a"},
        calls=[],
        model_key="fast",
        manifest=_manifest(),
    )
    assert sealed["manifest"]["model"]["id"] == "a-model"
    assert intact(sealed)
    altered = {
        **sealed,
        "manifest": {**sealed["manifest"], "model": {"key": "fast", "id": "other"}},
    }
    assert not intact(altered)


def test_a_bundle_without_a_manifest_still_seals_as_before() -> None:
    sealed = seal(
        workstation="aml_investigator",
        operator_id="alice",
        question="q",
        answer={"text": "a"},
        calls=[],
        model_key=None,
    )
    assert sealed["manifest"] is None and intact(sealed)


def test_every_turn_outcome_carries_its_manifest() -> None:
    runtime, llm = make_runtime([call("get_aml_dossier", entity_id="CR84920"), draft("Fine.")])
    out = asyncio.run(runtime.run_turn(principal=AML, question="q", entity_id="CR84920"))
    assert out.manifest is not None
    assert out.manifest["workstation"] == "aml_investigator"
    assert (
        out.manifest["model"]["id"] == llm.model
    )  # a model injected by a test is named by what it is
    assert out.manifest["toolset"]["sha256"] == toolset_digest(runtime._port.list_tools(AML))
