"""Flag text matching a pattern from ``config/forbidden_literals.yaml``.

Entry shape: ``{id, regex, allowlist: [paths], reason}``. Findings never echo the matched text.
The config file itself is never scanned: it necessarily contains the patterns.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path

from eios.common.errors import ConfigError
from tools.common.findings import Finding
from tools.common.yaml_io import load_validated
from tools.repo_checks._walk import is_under, iter_files, relative_posix

RULE_ID = "repo.forbidden_literal"
CONFIG_PATH = "config/forbidden_literals.yaml"

_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["patterns"],
    "properties": {
        "patterns": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "regex", "allowlist", "reason"],
                "properties": {
                    "id": {"type": "string", "minLength": 1},
                    "regex": {"type": "string", "minLength": 1},
                    "allowlist": {"type": "array", "items": {"type": "string", "minLength": 1}},
                    "reason": {"type": "string", "minLength": 1},
                },
            },
        }
    },
}


@dataclass(frozen=True, slots=True)
class ForbiddenPattern:
    id: str
    regex: re.Pattern[str]
    allowlist: tuple[str, ...]
    reason: str

    def allows(self, relative: str) -> bool:
        """True when ``relative`` is allowlisted: an exact path, a directory, or a glob."""
        return is_under(relative, self.allowlist) or any(
            fnmatchcase(relative, entry) for entry in self.allowlist
        )


def _compile(file: str, index: int, entry: dict[str, object]) -> ForbiddenPattern:
    where = f"patterns[{index}].regex"
    try:
        regex = re.compile(str(entry["regex"]))
    except re.error as exc:
        raise ConfigError(file, where, f"invalid regular expression: {exc}") from exc
    allowlist = tuple(str(p) for p in entry["allowlist"])  # type: ignore[attr-defined]
    return ForbiddenPattern(str(entry["id"]), regex, allowlist, str(entry["reason"]))


def load_patterns(path: Path) -> tuple[ForbiddenPattern, ...]:
    """Load and validate the pattern config; raises ``ConfigError`` naming file and path."""
    data = load_validated(path, _SCHEMA)
    entries: list[dict[str, object]] = data["patterns"]  # type: ignore[index]
    patterns = tuple(_compile(str(path), i, entry) for i, entry in enumerate(entries))
    seen: set[str] = set()
    for index, pattern in enumerate(patterns):
        if pattern.id in seen:
            raise ConfigError(str(path), f"patterns[{index}].id", f"duplicate id {pattern.id!r}")
        seen.add(pattern.id)
    return patterns


def _read_text(path: Path) -> str | None:
    """Return the text of ``path``, or None for a file that is not UTF-8 text."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None
    except OSError as exc:
        raise ConfigError(str(path), "$", f"cannot read file: {exc}") from exc


def scan_patterns(
    repo_root: Path, patterns: Sequence[ForbiddenPattern], *, exclude: Sequence[str] = ()
) -> tuple[Finding, ...]:
    """Scan every text file under ``repo_root`` for ``patterns``, honouring allowlists."""
    if not patterns:
        return ()
    root = repo_root.resolve()
    findings: list[Finding] = []
    for path in iter_files(root, exclude=exclude):
        relative = relative_posix(root, path)
        if relative == CONFIG_PATH:
            continue  # the pattern config necessarily contains the patterns themselves
        active = [p for p in patterns if not p.allows(relative)]
        text = _read_text(path) if active else None
        if text is None:
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            for pattern in active:
                if pattern.regex.search(line):
                    message = f"forbidden literal {pattern.id!r}: {pattern.reason}"
                    findings.append(Finding(relative, number, RULE_ID, message))
    return tuple(sorted(findings, key=lambda f: (f.file, f.line)))


def check_forbidden_literals(
    repo_root: Path, *, exclude: Sequence[str] = ()
) -> tuple[Finding, ...]:
    """Run the check with the repo's own config; no config file means no patterns."""
    config = repo_root.resolve() / CONFIG_PATH
    if not config.is_file():
        return ()
    return scan_patterns(repo_root, load_patterns(config), exclude=exclude)
