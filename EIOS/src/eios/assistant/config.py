"""Assistant settings, read once from the environment (spec 021 FR-017). No model id lives in source (ADR-002)."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

LOCAL_ENVIRONMENTS = frozenset({"dev", "test"})
DEFAULT_TURN_DEADLINE_S = 30.0  # [ASSUMPTION] bounds a turn well under the 60 s the baseline missed
DEFAULT_HISTORY_TURNS = (
    6  # [ASSUMPTION] earlier turns the model sees; older ones stay stored but out of context
)
DEFAULT_MAX_LLM_CALLS = 12  # [ASSUMPTION] tool rounds plus up to three assembly attempts


class AssistantConfigError(RuntimeError):
    """The assistant refuses to start: a required setting is missing for this environment."""


@dataclass(frozen=True)
class AssistantSettings:
    environment: str
    model: str | None
    persistence: str | None
    firestore_database: str | None
    prompt_template: str | None
    response_template: str | None
    turn_deadline_s: float
    max_llm_calls: int
    history_turns: int

    @property
    def local(self) -> bool:
        return self.environment in LOCAL_ENVIRONMENTS

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> AssistantSettings:
        source = os.environ if env is None else env
        return cls(
            environment=source.get("EIOS_ENVIRONMENT", "dev"),
            model=source.get("EIOS_GEMINI_MODEL") or None,
            persistence=source.get("EIOS_PERSISTENCE") or None,
            firestore_database=source.get("EIOS_FIRESTORE_DATABASE") or None,
            prompt_template=source.get("EIOS_MODEL_ARMOR_PROMPT_TEMPLATE") or None,
            response_template=source.get("EIOS_MODEL_ARMOR_RESPONSE_TEMPLATE") or None,
            turn_deadline_s=float(
                source.get("EIOS_ASSISTANT_TURN_DEADLINE_S", DEFAULT_TURN_DEADLINE_S)
            ),
            max_llm_calls=int(source.get("EIOS_ASSISTANT_MAX_LLM_CALLS", DEFAULT_MAX_LLM_CALLS)),
            history_turns=int(source.get("EIOS_ASSISTANT_HISTORY_TURNS", DEFAULT_HISTORY_TURNS)),
        )
