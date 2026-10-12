"""Run a gate's commands as subprocesses with a scrubbed environment and a captured log."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

_SCRUBBED_PREFIXES = ("COV_CORE", "COVERAGE", "PYTEST_")
_PYTHON_ALIAS = "python"


@dataclass(frozen=True, slots=True)
class CommandsResult:
    """``passed`` is true only when every command exited 0; ``log`` is stdout+stderr."""

    passed: bool
    log: str


def build_env(tool_root: Path, base: Mapping[str, str] | None = None) -> dict[str, str]:
    """Environment for child commands.

    Drops coverage and pytest plugin variables so an outer ``pytest --cov`` run does not leak
    into inner runs, and sets PYTHONPATH to ``<tool_root>/src`` plus ``<tool_root>``.
    """
    source = os.environ if base is None else base
    env = {k: v for k, v in source.items() if not k.startswith(_SCRUBBED_PREFIXES)}
    env["PYTHONPATH"] = os.pathsep.join((str(tool_root / "src"), str(tool_root)))
    return env


def resolve_argv(argv: Sequence[str], threshold: int | float | None = None) -> tuple[str, ...]:
    """Substitute ``{threshold}`` and map a leading ``python`` to the running interpreter."""
    substituted = [
        token.replace("{threshold}", "" if threshold is None else str(threshold)) for token in argv
    ]
    if substituted and substituted[0] == _PYTHON_ALIAS:
        substituted[0] = sys.executable
    return tuple(substituted)


def _run_one(
    argv: tuple[str, ...], cwd: Path, env: dict[str, str], timeout: float
) -> tuple[bool, str]:
    header = "$ " + " ".join(argv)
    try:
        completed = subprocess.run(  # noqa: S603 - argv comes from reviewed repo configuration
            argv,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raw = exc.stdout
        partial = raw.decode(errors="replace") if isinstance(raw, bytes) else (raw or "")
        return False, f"{header}\n{partial}\n[timed out after {timeout:g}s]\n"
    except OSError as exc:  # missing or non-executable command: a failure, never a skip
        return False, f"{header}\n[could not start command: {type(exc).__name__}: {exc}]\n"
    status = "ok" if completed.returncode == 0 else f"failed with exit code {completed.returncode}"
    return completed.returncode == 0, f"{header}\n{completed.stdout}[{status}]\n"


def run_commands(
    commands: Sequence[Sequence[str]],
    *,
    cwd: Path,
    env: dict[str, str],
    timeout: float,
    threshold: int | float | None = None,
) -> CommandsResult:
    """Run every command in order from ``cwd``; all run even after one fails."""
    passed = True
    logs: list[str] = []
    for raw in commands:
        ok, log = _run_one(resolve_argv(raw, threshold), cwd, env, timeout)
        passed = passed and ok
        logs.append(log)
    return CommandsResult(passed=passed, log="\n".join(logs))
