"""T190 (acceptance scenario 2): the trace names the prompt version that was actually called."""

from __future__ import annotations

import itertools
import shutil
from pathlib import Path

import pytest

from eios.common.errors import BoundaryValidationError
from eios.llm_gateway.config import config_identity
from eios.llm_gateway.gateway import Gateway, GatewaySinks, GatewayStores
from eios.llm_gateway.models import GatewayRequest, Outcome
from eios.llm_gateway.prompt_lock import DEFAULT_PROMPTS_DIR, PromptLock
from eios.llm_gateway.replay_cache import replay_key
from tests.support.llm_gateway import Kit, make_kit
from tools.prompt_lock.__main__ import main as prompt_lock_main

PROMPT_ID = "smoke-echo"
INPUTS = {"message": "hello"}


def _request(version: str) -> GatewayRequest:
    return GatewayRequest(
        prompt_id=PROMPT_ID,
        prompt_version=version,
        inputs=INPUTS,
        correlation_id="corr-trace",
        caller="test-suite",
    )


def _gateway(kit: Kit, prompts_dir: Path) -> Gateway:
    """A gateway over the kit's stores and sinks that reads ``prompts_dir`` afresh."""
    ids = itertools.count(1)
    return Gateway(
        config=kit.config,
        provider=kit.provider,
        stores=GatewayStores(counter=kit.counter, replay=kit.replay),
        prompts=PromptLock.load(prompts_dir),
        sinks=GatewaySinks(trace=kit.traces, events=kit.events),
        clock=kit.clock,
        new_id=lambda: f"trace-{next(ids):04d}",
    )


def _prompts_copy(tmp_path: Path) -> Path:
    copy = tmp_path / "prompts_copy"
    shutil.copytree(DEFAULT_PROMPTS_DIR, copy, ignore=shutil.ignore_patterns("__pycache__"))
    return copy


def _cli(command: str, prompts_dir: Path) -> int:
    return prompt_lock_main(
        [command, "--repo-root", str(prompts_dir.parent), "--prompts-dir", str(prompts_dir)]
    )


def _add_v2(prompts_dir: Path, text: str) -> None:
    (prompts_dir / PROMPT_ID / "v2.md").write_text(text, encoding="utf-8")
    assert _cli("update", prompts_dir) == 0
    assert _cli("check", prompts_dir) == 0


def _traced_version(kit: Kit) -> object:
    return kit.traces.records[-1]["prompt_version"]


def _key(kit: Kit, version: str) -> str:
    return replay_key(
        prompt_id=PROMPT_ID,
        prompt_version=version,
        inputs=INPUTS,
        config_identity=config_identity(kit.config),
    )


def test_the_trace_shows_v1_then_v2_and_the_replay_keys_differ(tmp_path: Path) -> None:
    kit = make_kit(tmp_path)
    prompts = _prompts_copy(tmp_path)
    assert _gateway(kit, prompts).complete(_request("v1")).outcome is Outcome.OK
    assert _traced_version(kit) == "v1"

    _add_v2(prompts, "Echo this note back, version two.\n\n{{message}}\n")
    assert _gateway(kit, prompts).complete(_request("v2")).outcome is Outcome.OK
    assert _traced_version(kit) == "v2"

    assert _key(kit, "v1") != _key(kit, "v2")
    assert kit.replay.get(_key(kit, "v1")) is not None
    assert kit.replay.get(_key(kit, "v2")) is not None


def test_v1_remains_callable_after_v2_is_added(tmp_path: Path) -> None:
    kit = make_kit(tmp_path)
    prompts = _prompts_copy(tmp_path)
    _add_v2(prompts, "second {{message}}\n")
    assert _gateway(kit, prompts).complete(_request("v1")).outcome is Outcome.OK
    assert _traced_version(kit) == "v1"


def test_a_version_not_in_the_lock_is_rejected_before_any_provider_call(tmp_path: Path) -> None:
    kit = make_kit(tmp_path)
    prompts = _prompts_copy(tmp_path)
    (prompts / PROMPT_ID / "v2.md").write_text("unlocked {{message}}\n", encoding="utf-8")
    with pytest.raises(BoundaryValidationError):
        _gateway(kit, prompts).complete(_request("v2"))
    assert kit.provider.calls == []
    assert kit.traces.records == []
