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
DEFAULT_HEDGE_AFTER_S = 3.0  # [ASSUMPTION] the default model answers in about 2 s [MEASURED]; a call still silent at 3 s is probably stalled; 0 turns hedging off
DEFAULT_MAX_LLM_CALLS = 12  # [ASSUMPTION] tool rounds plus up to three assembly attempts


def _on(value: str) -> bool:
    return value.strip().lower() not in {"0", "false", "no", "off"}


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
    hedge_after_s: float = DEFAULT_HEDGE_AFTER_S
    # the turn reads and writes its session in memory and the durable store catches up after (session_cache.py)
    session_write_behind: bool = True
    # a figure the model writes plainly is shown when a tool returned it this turn (assembly.py, traced mode); off
    # restores the old rule that every figure be a {{fact:...}} placeholder
    plain_figures: bool = True
    prefetch: bool = (
        True  # run the obvious tool before the model's first turn (one model call instead of two)
    )

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
            hedge_after_s=float(source.get("EIOS_ASSISTANT_HEDGE_AFTER_S", DEFAULT_HEDGE_AFTER_S)),
            prefetch=_on(source.get("EIOS_ASSISTANT_PREFETCH", "1")),
            plain_figures=_on(source.get("EIOS_ASSISTANT_PLAIN_FIGURES", "1")),
            session_write_behind=_on(source.get("EIOS_ASSISTANT_SESSION_WRITE_BEHIND", "1")),
        )
