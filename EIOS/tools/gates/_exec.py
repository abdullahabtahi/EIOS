"""Subprocess and executable lookup helpers shared by the scanner gates."""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path

from eios.common.errors import ToolError

DEFAULT_TIMEOUT_SECONDS = 600.0  # [TARGET] generous ceiling; a hung tool becomes a tool error


def find_executable(name: str) -> str | None:
    """Return the absolute path of ``name`` on PATH, or None. Tests replace this lookup."""
    return shutil.which(name)


def require_executable(name: str) -> str:
    """Return the path of ``name`` or raise ``ToolError`` naming the missing tool."""
    found = find_executable(name)
    if found is None:
        raise ToolError(f"required tool not found on PATH: {name}")
    return found


def run(
    argv: Sequence[str],
    cwd: Path,
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    extra_env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run ``argv`` (no shell) in ``cwd`` capturing text output; never raises on exit status."""
    env = {**os.environ, **(extra_env or {})}
    try:
        return subprocess.run(  # noqa: S603 - argv is a list built by this package, no shell
            list(argv),
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ToolError(f"{argv[0]} timed out after {timeout:.0f}s") from exc
    except OSError as exc:
        raise ToolError(f"could not run {argv[0]}: {exc}") from exc


def tail(text: str, limit: int = 400) -> str:
    """Last ``limit`` characters of ``text``, whitespace-normalised, for error messages."""
    squeezed = " ".join(text.split())
    return squeezed[-limit:]
