"""Shared kit for LLM gateway tests: configs, locked prompt trees, spies and a built gateway."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

from eios.llm_gateway.caps import CapEvent
from eios.llm_gateway.config import GatewayConfig, parse_config
from eios.llm_gateway.gateway import Gateway, GatewaySinks, GatewayStores
from eios.llm_gateway.models import GatewayRequest
from eios.llm_gateway.prompt_lock import PromptLock
from eios.llm_gateway.providers.base import Provider, ProviderResult
from eios.llm_gateway.providers.stub import StubProvider
from eios.llm_gateway.stores.memory import MemoryCounterStore, MemoryReplayStore

TRUSTED_PROMPT = ("smoke-echo", "v1", "Echo this note back.\n\n{{message}}\n")
UNTRUSTED_PROMPT = ("triage-note", "v1", "Ticket {{ticket}}:\n{{untrusted:body}}\n")
DEFAULT_PROMPTS = (TRUSTED_PROMPT, UNTRUSTED_PROMPT)


def config_dict(**overrides: object) -> dict[str, object]:
    """A valid dev-shaped configuration; ``overrides`` replace whole top-level keys."""
    base: dict[str, object] = {
        "environment": "dev",
        "provider": "stub",
        "model_id": "stub-test-model",
        "prices": {
            "input_per_unit": 2.0,
            "output_per_unit": 4.0,
            "currency": "USD",
            "unit": "1000 tokens",
        },
        "rate_limits": {"requests_per_minute": 60},
        "daily_token_cap": 1000,
        "cap_warning_thresholds_percent": [50, 80],
        "verification": {
            "model_id": "[ILLUSTRATIVE]",
            "prices": "[ILLUSTRATIVE]",
            "rate_limits": "[ILLUSTRATIVE]",
            "daily_token_cap": "[ILLUSTRATIVE]",
            "cap_warning_thresholds_percent": "[TARGET]",
        },
    }
    return {**base, **overrides}


def make_config(**overrides: object) -> GatewayConfig:
    return parse_config(config_dict(**overrides), source="test")


def write_prompt_tree(
    root: Path, prompts: tuple[tuple[str, str, str], ...] = DEFAULT_PROMPTS
) -> Path:
    """Write prompt files and a matching ``prompts.lock.json`` under ``root``."""
    entries = []
    for prompt_id, version, text in prompts:
        target = root / prompt_id / f"{version}.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        entries.append({"id": prompt_id, "version": version, "sha256": digest})
    lock = {"prompts": sorted(entries, key=lambda e: (e["id"], e["version"]))}
    (root / "prompts.lock.json").write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    return root


@dataclass(frozen=True)
class FixedUsageProvider:
    """Returns fixed content and token counts so cap arithmetic is exact."""

    tokens_in: int = 30
    tokens_out: int = 30
    content: str = "fixed-content"

    def generate(
        self, rendered_prompt: str, model_id: str | None, limits: Mapping[str, int]
    ) -> ProviderResult:
        return ProviderResult(
            content=self.content, tokens_in=self.tokens_in, tokens_out=self.tokens_out
        )


@dataclass
class MutableClock:
    """A test clock that can be advanced; ``step`` moves it on every read (non-zero latency)."""

    instant: datetime = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    step: timedelta = timedelta(0)

    def now(self) -> datetime:
        current = self.instant
        self.instant = self.instant + self.step
        return current

    def advance(self, delta: timedelta) -> None:
        self.instant = self.instant + delta


@dataclass
class SpyProvider:
    """Counts calls and records arguments; delegates to an inner provider."""

    inner: Provider = field(default_factory=StubProvider)
    calls: list[tuple[str, str | None, Mapping[str, int]]] = field(default_factory=list)

    def generate(
        self, rendered_prompt: str, model_id: str | None, limits: Mapping[str, int]
    ) -> ProviderResult:
        self.calls.append((rendered_prompt, model_id, limits))
        return self.inner.generate(rendered_prompt, model_id, limits)


@dataclass
class CollectingTraceSink:
    records: list[Mapping[str, object]] = field(default_factory=list)

    def emit(self, record: Mapping[str, object]) -> None:
        self.records.append(record)


@dataclass
class CollectingEventSink:
    events: list[CapEvent] = field(default_factory=list)

    def emit(self, event: CapEvent) -> None:
        self.events.append(event)


@dataclass(frozen=True)
class Kit:
    gateway: Gateway
    provider: SpyProvider
    counter: MemoryCounterStore
    replay: MemoryReplayStore
    traces: CollectingTraceSink
    events: CollectingEventSink
    clock: MutableClock
    prompts_dir: Path
    config: GatewayConfig


def make_kit(
    tmp_path: Path,
    *,
    config: GatewayConfig | None = None,
    provider: Provider | None = None,
    clock: MutableClock | None = None,
    prompts: tuple[tuple[str, str, str], ...] = DEFAULT_PROMPTS,
) -> Kit:
    cfg = config if config is not None else make_config()
    spy = SpyProvider(inner=provider if provider is not None else StubProvider())
    counter, replay = MemoryCounterStore(), MemoryReplayStore()
    traces, events = CollectingTraceSink(), CollectingEventSink()
    fixed = clock if clock is not None else MutableClock()
    prompts_dir = write_prompt_tree(tmp_path / "prompts", prompts)
    ids = iter(f"trace-{n:04d}" for n in range(1, 10_000))
    gateway = Gateway(
        config=cfg,
        provider=spy,
        stores=GatewayStores(counter=counter, replay=replay),
        prompts=PromptLock.load(prompts_dir),
        sinks=GatewaySinks(trace=traces, events=events),
        clock=fixed,
        new_id=lambda: next(ids),
    )
    return Kit(gateway, spy, counter, replay, traces, events, fixed, prompts_dir, cfg)


def echo_request(message: str = "hello", *, correlation_id: str = "corr-1") -> GatewayRequest:
    return GatewayRequest(
        prompt_id=TRUSTED_PROMPT[0],
        prompt_version=TRUSTED_PROMPT[1],
        inputs={"message": message},
        correlation_id=correlation_id,
        caller="test-suite",
    )
