"""Locked prompts (FR-037): a prompt is callable only if ``prompts.lock.json`` lists its hash.

The lockfile maps (prompt id, version) to the sha256 of the prompt file. ``resolve`` re-reads
and re-hashes the file on every call, so an edit after lock time is caught before any provider
call. Ids and versions are matched against strict patterns first, which blocks path traversal.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from pydantic import ValidationError

from eios.common.errors import BoundaryValidationError, ConfigError, EiosError
from eios.common.validation import StrictModel

DEFAULT_PROMPTS_DIR = Path(__file__).resolve().parents[3] / "prompts"
LOCK_FILE_NAME = "prompts.lock.json"
_ID = re.compile(r"[a-z][a-z0-9-]{0,63}")
_VERSION = re.compile(r"v[0-9]{1,6}")
PROMPT_ID_PATTERN = _ID
PROMPT_VERSION_PATTERN = _VERSION
_SHA256 = re.compile(r"[0-9a-f]{64}")


class PromptNotLocked(BoundaryValidationError):
    """The prompt id/version is not in the lockfile."""


class PromptIntegrityError(EiosError):
    """A locked prompt cannot be used as locked."""


class PromptHashMismatch(PromptIntegrityError):
    """The prompt file changed since it was locked."""


class PromptFileMissing(PromptIntegrityError):
    """The lockfile lists a prompt whose file is gone."""


class LockedPrompt(StrictModel):
    prompt_id: str
    version: str
    template: str
    content_hash: str


class _LockEntry(StrictModel):
    id: str
    version: str
    sha256: str


def content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _parse_lock(directory: Path) -> dict[tuple[str, str], str]:
    path = directory / LOCK_FILE_NAME
    where = str(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError:
        raise ConfigError(where, "<file>", "cannot be read") from None
    except ValueError:
        raise ConfigError(where, "<file>", "is not valid JSON") from None
    if not isinstance(raw, dict) or not isinstance(raw.get("prompts"), list):
        raise ConfigError(where, "prompts", "must be a list under a top-level object")
    entries: dict[tuple[str, str], str] = {}
    for index, item in enumerate(raw["prompts"]):
        entry = _entry(item, f"prompts.{index}", where)
        key = (entry.id, entry.version)
        if key in entries:
            raise ConfigError(where, f"prompts.{index}", "duplicates an earlier entry")
        entries[key] = entry.sha256
    return entries


def _entry(item: object, path: str, where: str) -> _LockEntry:
    try:
        entry = _LockEntry.model_validate(item)
    except ValidationError:
        raise ConfigError(where, path, "must have string id, version and sha256") from None
    valid = (
        _ID.fullmatch(entry.id)
        and _VERSION.fullmatch(entry.version)
        and _SHA256.fullmatch(entry.sha256)
    )
    if not valid:
        raise ConfigError(where, path, "has an invalid id, version or sha256")
    return entry


class PromptLock:
    """Read-only view of the lockfile for one prompts directory."""

    def __init__(self, directory: Path, hashes: dict[tuple[str, str], str]) -> None:
        self._directory = directory
        self._hashes = hashes

    @classmethod
    def load(cls, directory: Path) -> PromptLock:
        return cls(directory, _parse_lock(directory))

    def hashes(self) -> dict[tuple[str, str], str]:
        """A copy of the lockfile contents: ``(prompt id, version) -> sha256``."""
        return dict(self._hashes)

    def resolve(self, prompt_id: str, version: str) -> LockedPrompt:
        """Return the locked prompt, or raise before anything reaches a provider."""
        if not (_ID.fullmatch(prompt_id) and _VERSION.fullmatch(version)):
            raise BoundaryValidationError(
                "prompt id or version has an invalid shape", ("prompt_id", "prompt_version")
            )
        expected = self._hashes.get((prompt_id, version))
        if expected is None:
            raise PromptNotLocked("prompt is not listed in the lockfile", ("prompt_id",))
        try:
            data = (self._directory / prompt_id / f"{version}.md").read_bytes()
        except OSError:
            raise PromptFileMissing("locked prompt file is missing") from None
        if content_hash(data) != expected:
            raise PromptHashMismatch("prompt file changed since it was locked")
        try:
            template = data.decode("utf-8")
        except UnicodeDecodeError:
            raise PromptIntegrityError("locked prompt file is not valid UTF-8") from None
        return LockedPrompt(
            prompt_id=prompt_id, version=version, template=template, content_hash=expected
        )
