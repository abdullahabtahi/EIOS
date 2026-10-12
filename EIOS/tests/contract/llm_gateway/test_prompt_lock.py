"""T109 (FR-037): prompts are locked artefacts; unknown or edited prompts never reach a provider."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from eios.common.errors import BoundaryValidationError, ConfigError
from eios.llm_gateway.prompt_lock import (
    DEFAULT_PROMPTS_DIR,
    PromptFileMissing,
    PromptHashMismatch,
    PromptLock,
    PromptNotLocked,
    content_hash,
)
from tests.support.llm_gateway import (
    TRUSTED_PROMPT,
    echo_request,
    make_kit,
    write_prompt_tree,
)


@pytest.fixture
def prompts_dir(tmp_path: Path) -> Path:
    return write_prompt_tree(tmp_path / "prompts")


def test_a_locked_prompt_resolves_with_its_template(prompts_dir: Path) -> None:
    locked = PromptLock.load(prompts_dir).resolve(TRUSTED_PROMPT[0], TRUSTED_PROMPT[1])
    assert locked.prompt_id == TRUSTED_PROMPT[0]
    assert locked.version == TRUSTED_PROMPT[1]
    assert locked.template == TRUSTED_PROMPT[2]
    assert locked.content_hash == hashlib.sha256(TRUSTED_PROMPT[2].encode()).hexdigest()


def test_unknown_prompt_id_is_a_validation_error(prompts_dir: Path) -> None:
    with pytest.raises(PromptNotLocked) as caught:
        PromptLock.load(prompts_dir).resolve("no-such-prompt", "v1")
    assert isinstance(caught.value, BoundaryValidationError)


def test_unknown_version_is_a_validation_error(prompts_dir: Path) -> None:
    with pytest.raises(PromptNotLocked):
        PromptLock.load(prompts_dir).resolve(TRUSTED_PROMPT[0], "v9")


def test_a_prompt_file_present_but_not_locked_is_not_callable(prompts_dir: Path) -> None:
    (prompts_dir / TRUSTED_PROMPT[0] / "v2.md").write_text("new text", encoding="utf-8")
    with pytest.raises(PromptNotLocked):
        PromptLock.load(prompts_dir).resolve(TRUSTED_PROMPT[0], "v2")


def test_edited_prompt_file_raises_a_mismatch_error(prompts_dir: Path) -> None:
    lock = PromptLock.load(prompts_dir)
    (prompts_dir / TRUSTED_PROMPT[0] / f"{TRUSTED_PROMPT[1]}.md").write_text("edited", "utf-8")
    with pytest.raises(PromptHashMismatch):
        lock.resolve(TRUSTED_PROMPT[0], TRUSTED_PROMPT[1])


def test_locked_prompt_with_missing_file_is_reported(prompts_dir: Path) -> None:
    lock = PromptLock.load(prompts_dir)
    (prompts_dir / TRUSTED_PROMPT[0] / f"{TRUSTED_PROMPT[1]}.md").unlink()
    with pytest.raises(PromptFileMissing):
        lock.resolve(TRUSTED_PROMPT[0], TRUSTED_PROMPT[1])


@pytest.mark.parametrize(
    ("prompt_id", "version"),
    [
        ("../escape", "v1"),
        ("smoke-echo", "../v1"),
        ("Smoke Echo", "v1"),
        ("smoke-echo", "1"),
        ("", "v1"),
    ],
)
def test_ids_and_versions_that_could_traverse_paths_are_rejected(
    prompts_dir: Path, prompt_id: str, version: str
) -> None:
    with pytest.raises(BoundaryValidationError):
        PromptLock.load(prompts_dir).resolve(prompt_id, version)


def test_unlocked_prompt_is_rejected_before_any_provider_call(tmp_path: Path) -> None:
    kit = make_kit(tmp_path)
    request = echo_request().model_copy(update={"prompt_version": "v7"})
    with pytest.raises(PromptNotLocked):
        kit.gateway.complete(request)
    assert kit.provider.calls == []
    assert kit.traces.records == []


def test_edited_prompt_is_rejected_before_any_provider_call(tmp_path: Path) -> None:
    kit = make_kit(tmp_path)
    (kit.prompts_dir / TRUSTED_PROMPT[0] / f"{TRUSTED_PROMPT[1]}.md").write_text(
        "tampered", "utf-8"
    )
    with pytest.raises(PromptHashMismatch):
        kit.gateway.complete(echo_request())
    assert kit.provider.calls == []


@pytest.mark.parametrize(
    "lock_text",
    [
        "not json",
        "[]",
        '{"prompts": "x"}',
        '{"prompts": [{"id": "a"}]}',
        '{"prompts": [{"id": "a", "version": "v1", "sha256": "zz"}]}',
    ],
)
def test_malformed_lock_is_a_config_error(tmp_path: Path, lock_text: str) -> None:
    (tmp_path / "prompts.lock.json").write_text(lock_text, encoding="utf-8")
    with pytest.raises(ConfigError):
        PromptLock.load(tmp_path)


def test_missing_lock_file_is_a_config_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        PromptLock.load(tmp_path)


def test_duplicate_lock_entries_are_rejected(tmp_path: Path) -> None:
    entry = {"id": "a", "version": "v1", "sha256": "0" * 64}
    (tmp_path / "prompts.lock.json").write_text(
        json.dumps({"prompts": [entry, entry]}), encoding="utf-8"
    )
    with pytest.raises(ConfigError):
        PromptLock.load(tmp_path)


def test_content_hash_is_sha256_hex() -> None:
    assert content_hash(b"abc") == hashlib.sha256(b"abc").hexdigest()


def test_committed_sample_prompt_is_locked_and_intact() -> None:
    locked = PromptLock.load(DEFAULT_PROMPTS_DIR).resolve("smoke-echo", "v1")
    assert locked.template.strip()
