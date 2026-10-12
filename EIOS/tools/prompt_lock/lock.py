"""Compare prompt files with ``prompts.lock.json`` and maintain the lock (FR-037).

A locked version is immutable: ``update`` only ever adds entries for new ``v<N>.md`` files and
never changes the hash of an existing entry. An edit to a locked file must become a new version.
The lock is written sorted (id, then numeric version) so its diff is reviewable.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from eios.common.errors import ToolError
from eios.llm_gateway.prompt_lock import (
    LOCK_FILE_NAME,
    PROMPT_ID_PATTERN,
    PROMPT_VERSION_PATTERN,
    PromptLock,
    content_hash,
)
from tools.common.findings import Finding

PromptKey = tuple[str, str]
RULE_HASH_MISMATCH = "prompt_lock.hash_mismatch"
RULE_UNLOCKED = "prompt_lock.unlocked_file"
RULE_MISSING = "prompt_lock.missing_file"
RULE_INVALID_NAME = "prompt_lock.invalid_name"
_SKIPPED_PREFIXES = ("_", ".")


def _sort_key(key: PromptKey) -> tuple[str, int]:
    return (key[0], int(key[1][1:]))


def _finding_sort_key(finding: Finding) -> tuple[str, int, str, str]:
    return (finding.file, finding.line, finding.rule_id, finding.message)


def display_path(repo_root: Path, path: Path) -> str:
    """Repo-relative POSIX path when ``path`` is inside the repo, otherwise the full path."""
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _read(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise ToolError(f"cannot read prompt file {path}: {exc}") from exc


def _invalid_name(shown: str, what: str) -> Finding:
    return Finding(shown, 1, RULE_INVALID_NAME, f"{what}: expected prompts/<id>/v<N>.md")


def _scan_prompt_dir(
    directory: Path, repo_root: Path, files: dict[PromptKey, str], bad: list[Finding]
) -> None:
    for entry in sorted(directory.iterdir()):
        if not entry.is_file() or entry.name.startswith(_SKIPPED_PREFIXES):
            continue
        version = entry.name.removesuffix(".md")
        if entry.suffix != ".md" or not PROMPT_VERSION_PATTERN.fullmatch(version):
            bad.append(_invalid_name(display_path(repo_root, entry), "misnamed prompt file"))
            continue
        files[(directory.name, version)] = content_hash(_read(entry))


def scan_prompts(prompts_dir: Path, repo_root: Path) -> tuple[dict[PromptKey, str], list[Finding]]:
    """Hash every ``<id>/v<N>.md`` under ``prompts_dir``; misnamed entries become findings."""
    files: dict[PromptKey, str] = {}
    bad: list[Finding] = []
    if not prompts_dir.is_dir():
        raise ToolError(f"prompts directory not found: {prompts_dir}")
    for directory in sorted(prompts_dir.iterdir()):
        if not directory.is_dir() or directory.name.startswith(_SKIPPED_PREFIXES):
            continue
        if not PROMPT_ID_PATTERN.fullmatch(directory.name):
            bad.append(_invalid_name(display_path(repo_root, directory), "misnamed prompt id"))
            continue
        _scan_prompt_dir(directory, repo_root, files, bad)
    return files, bad


def _compare(
    lock: Mapping[PromptKey, str],
    files: Mapping[PromptKey, str],
    prompts_dir: Path,
    repo_root: Path,
) -> list[Finding]:
    findings: list[Finding] = []
    for key in sorted(set(lock) | set(files), key=_sort_key):
        prompt_id, version = key
        shown = display_path(repo_root, prompts_dir / prompt_id / f"{version}.md")
        label = f"prompt {prompt_id} {version}"
        if key not in files:
            msg = f"{label}: locked version has no file (a locked version must not be deleted)"
            findings.append(Finding(shown, 1, RULE_MISSING, msg))
        elif key not in lock:
            msg = (
                f"{label}: file is not in {LOCK_FILE_NAME}; "
                "run `python -m tools.prompt_lock update`"
            )
            findings.append(Finding(shown, 1, RULE_UNLOCKED, msg))
        elif files[key] != lock[key]:
            msg = (
                f"{label}: content hash differs from the lock; locked versions are immutable, "
                "publish the change as a new version file instead"
            )
            findings.append(Finding(shown, 1, RULE_HASH_MISMATCH, msg))
    return findings


def check_prompts(prompts_dir: Path, repo_root: Path) -> tuple[Finding, ...]:
    """Findings for every disagreement between the files and the lock; raises if no lock."""
    lock = PromptLock.load(prompts_dir).hashes()
    files, bad = scan_prompts(prompts_dir, repo_root)
    found = [*bad, *_compare(lock, files, prompts_dir, repo_root)]
    return tuple(sorted(found, key=_finding_sort_key))


def render_lock(hashes: Mapping[PromptKey, str]) -> str:
    """The lockfile text: sorted entries, two-space indent, trailing newline."""
    entries = [
        {"id": key[0], "version": key[1], "sha256": hashes[key]}
        for key in sorted(hashes, key=_sort_key)
    ]
    return json.dumps({"prompts": entries}, indent=2) + "\n"


def _write(path: Path, text: str) -> None:
    try:
        if path.is_file() and path.read_text(encoding="utf-8") == text:
            return
        path.write_text(text, encoding="utf-8")
    except OSError as exc:
        raise ToolError(f"cannot write {path}: {exc}") from exc


def update_lock(prompts_dir: Path, repo_root: Path) -> tuple[Finding, ...]:
    """Add new versions to the lock; report (never accept) edited or deleted locked versions."""
    lock_path = prompts_dir / LOCK_FILE_NAME
    lock = PromptLock.load(prompts_dir).hashes() if lock_path.is_file() else {}
    files, bad = scan_prompts(prompts_dir, repo_root)
    added = {key: digest for key, digest in files.items() if key not in lock}
    _write(lock_path, render_lock({**lock, **added}))
    violations = [
        f for f in _compare(lock, files, prompts_dir, repo_root) if f.rule_id != RULE_UNLOCKED
    ]
    return tuple(sorted([*bad, *violations], key=_finding_sort_key))
