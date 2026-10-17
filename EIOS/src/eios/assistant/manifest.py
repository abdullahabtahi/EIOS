"""The orchestration manifest: what produced an answer, kept with the evidence it rested on.

A sealed bundle records what the assistant read and said. It did not record what the assistant was: which model, which
instructions, which tools, which limits. Those decide the answer as much as the data does (the same question under a
different instruction or model can end differently), and a replay of the data alone cannot tell a reader that the
setup has changed since. The manifest names each part and hashes the two that are long, the instruction and the tool
catalogue, so a change in either shows as a different hash.
"""

from __future__ import annotations

from collections.abc import Iterable
from importlib.metadata import PackageNotFoundError, version
from typing import Any

from eios.assistant.assembly import MAX_ATTEMPTS
from eios.assistant.config import AssistantSettings
from eios.evidence.bundle import digest
from eios.ontology.omcp.port.principal import Principal
from eios.ontology.omcp.port.registry import ToolSpec

MANIFEST_SCHEMA = "eios.orchestration_manifest/v1"


def toolset_digest(tools: Iterable[ToolSpec]) -> str:
    """SHA-256 of what the model is told about its tools: name, description and argument schema, in name order."""
    declared: list[dict[str, Any]] = [
        {
            "name": t.name,
            "kind": t.kind,
            "description": t.description or t.capability,
            "arguments": t.args_model.model_json_schema(),
        }
        for t in tools
    ]
    declared.sort(key=lambda d: str(d["name"]))
    return digest({"tools": declared})


def _adk_version() -> str:
    try:
        return version("google-adk")
    except PackageNotFoundError:  # a source checkout without installed metadata
        return "unknown"


def build_manifest(
    *,
    principal: Principal,
    tools: list[ToolSpec],
    settings: AssistantSettings,
    model_key: str | None,
    model_id: str,
) -> dict[str, Any]:
    # imported here: agents.py imports this package's modules, and the manifest is built only at run time
    from eios.assistant.agents import instruction_digest

    return {
        "schema": MANIFEST_SCHEMA,
        "workstation": principal.workstation.value,
        "adk_version": _adk_version(),
        "model": {"key": model_key, "id": model_id},
        "instruction_sha256": instruction_digest(
            principal.workstation, settings.plain_figures, settings.history_turns
        ),
        "toolset": {"count": len(tools), "sha256": toolset_digest(tools)},
        "assembly": {
            "max_attempts": MAX_ATTEMPTS,
            "plain_figures": settings.plain_figures,
            "prefetch": settings.prefetch,
        },
        "limits": {
            "turn_deadline_s": settings.turn_deadline_s,
            "max_llm_calls": settings.max_llm_calls,
            "hedge_after_s": settings.hedge_after_s,
            "history_turns": settings.history_turns,
        },
    }
