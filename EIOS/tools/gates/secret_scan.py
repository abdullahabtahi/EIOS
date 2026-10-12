"""Secret scanner (T050, SC-004): working tree, captured logs and git history.

Patterns are data (``RULES``). A finding names the file, line and rule id only; the matched
text is never stored, printed or logged. Container images are scanned once image builds exist
(T216); history scanning runs whenever the target has a ``.git`` directory.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

from eios.common.errors import ToolError
from tools.common.cli import run_tool
from tools.common.findings import Finding
from tools.gates import _exec


@dataclass(frozen=True, slots=True)
class SecretRule:
    rule_id: str
    description: str
    pattern: re.Pattern[str]


RULES: tuple[SecretRule, ...] = (
    SecretRule(
        "secret-cloud-access-key",
        "cloud access key id",
        re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    ),
    SecretRule(
        "secret-api-key",
        "cloud API key",
        re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    ),
    SecretRule(
        "secret-vcs-token",
        "source-control access token",
        re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,255}|github_pat_[A-Za-z0-9_]{22,255})\b"),
    ),
    SecretRule(
        "secret-private-key",
        "private key block",
        re.compile(r"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY(?: BLOCK)?-----"),
    ),
    SecretRule(
        "secret-chat-token",
        "chat service token",
        re.compile(r"\bxox[abposr]-[0-9A-Za-z-]{10,}\b"),
    ),
)

SKIP_DIR_NAMES = frozenset(
    {
        ".venv",
        "venv",
        ".git",
        "node_modules",
        "__pycache__",
        ".terraform",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
    }
)
_BINARY_SNIFF_BYTES = 8192
_HUNK = re.compile(r"^@@ -\S+ \+(\d+)")
_COMMIT_MARK = "commit:"


def scan_text(name: str, text: str) -> list[Finding]:
    """Findings for ``text`` labelled ``name``; one per (rule, line)."""
    findings: list[Finding] = []
    for number, line in enumerate(text.splitlines(), start=1):
        findings.extend(_scan_line(name, number, line, ""))
    return findings


def _scan_line(name: str, number: int, line: str, suffix: str) -> Iterator[Finding]:
    for rule in RULES:
        if rule.pattern.search(line):
            yield Finding(name, number, rule.rule_id, f"{rule.description} detected{suffix}")


def _scan_file(root: Path, path: Path) -> list[Finding]:
    name = path.relative_to(root).as_posix()
    findings: list[Finding] = []
    try:
        with path.open("rb") as handle:
            if b"\x00" in handle.read(_BINARY_SNIFF_BYTES):
                return []
            handle.seek(0)
            for number, raw in enumerate(handle, start=1):
                line = raw.decode("utf-8", errors="replace")
                findings.extend(_scan_line(name, number, line, ""))
    except OSError as exc:
        raise ToolError(f"cannot read {name}: {exc.strerror or type(exc).__name__}") from exc
    return findings


def _iter_files(root: Path) -> Iterator[Path]:
    for current, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIR_NAMES)
        for filename in sorted(filenames):
            path = Path(current) / filename
            if path.is_file() and not path.is_symlink():
                yield path


def scan_tree(repo_root: Path) -> list[Finding]:
    """Scan every regular file under ``repo_root`` (captured logs under evals/reports included)."""
    root = repo_root.resolve()
    findings: list[Finding] = []
    for path in _iter_files(root):
        findings.extend(_scan_file(root, path))
    return findings


def _history_findings(log_output: str) -> list[Finding]:
    seen: set[tuple[str, str, str]] = set()
    findings: list[Finding] = []
    commit, file, line_no = "", "", 0
    for raw in log_output.splitlines():
        if raw.startswith(_COMMIT_MARK):
            commit = raw[len(_COMMIT_MARK) :][:12]
        elif raw.startswith("+++ "):
            file = raw[6:] if raw.startswith("+++ b/") else ""
        elif hunk := _HUNK.match(raw):
            line_no = int(hunk.group(1))
        elif raw.startswith("+") and file:
            suffix = f" in history (commit {commit})"
            for finding in _scan_line(file, line_no, raw[1:], suffix):
                key = (finding.file, finding.rule_id, commit)
                if key not in seen:
                    seen.add(key)
                    findings.append(finding)
            line_no += 1
    return findings


def scan_history(repo_root: Path) -> list[Finding]:
    """Scan every added line in all commits; nothing to do without a ``.git`` directory."""
    if not (repo_root / ".git").exists():
        return []
    git = _exec.require_executable("git")
    argv = [git, "log", "--all", "-p", "-U0", "--no-color", "--no-ext-diff"]
    result = _exec.run([*argv, f"--format={_COMMIT_MARK}%H"], repo_root)
    if result.returncode != 0:
        raise ToolError(f"git log failed: {_exec.tail(result.stderr)}")
    return _history_findings(result.stdout)


def _run(args: argparse.Namespace) -> Sequence[Finding]:
    repo_root: Path = args.repo_root
    return [*scan_tree(repo_root), *scan_history(repo_root)]


def main(argv: Sequence[str]) -> int:
    return run_tool("secret_scan", _run, argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
