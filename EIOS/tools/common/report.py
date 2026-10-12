"""Write ``evals/reports/<tool>.json`` without ever clobbering another tool's report."""

from __future__ import annotations

import json
import os
import re
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path

from eios.common.errors import ToolError
from tools.common.findings import Finding

_REPORT_DIR = Path("evals") / "reports"
_TOOL_NAME = re.compile(r"[a-z][a-z0-9_-]{0,63}")


def report_path(repo_root: Path, tool: str) -> Path:
    """Return the report location for ``tool``; the name alone decides the path."""
    if not _TOOL_NAME.fullmatch(tool):
        raise ToolError(f"invalid tool name for a report: {tool!r}")
    return repo_root / _REPORT_DIR / f"{tool}.json"


def _check_owner(path: Path, tool: str) -> None:
    """Refuse to replace a report that exists but was not written by ``tool``."""
    if not path.exists():
        return
    try:
        existing = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ToolError(f"refusing to overwrite unreadable report {path}: {exc}") from exc
    owner = existing.get("tool") if isinstance(existing, dict) else None
    if owner != tool:
        raise ToolError(f"refusing to overwrite {path}: it belongs to tool {owner!r}, not {tool!r}")


def _atomic_write(path: Path, text: str) -> None:
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        Path(tmp_name).replace(path)
    except OSError as exc:
        Path(tmp_name).unlink(missing_ok=True)
        raise ToolError(f"could not write report {path}: {exc}") from exc


_CORE_KEYS = frozenset({"tool", "exit_code", "finding_count", "findings"})


def write_report(
    repo_root: Path,
    tool: str,
    findings: Sequence[Finding],
    extra: Mapping[str, object] | None = None,
) -> Path:
    """Write the report for ``tool`` and return its path.

    Findings are sorted (file, line, rule) so reruns produce identical bytes. The input
    sequence is not modified. ``extra`` adds JSON-serialisable top-level keys; it can never
    replace the four core keys.
    """
    clash = _CORE_KEYS & set(extra or {})
    if clash:
        raise ToolError(f"report extras may not replace core keys: {sorted(clash)}")
    path = report_path(repo_root, tool)
    ordered = sorted(findings, key=lambda f: (f.file, f.line, f.rule_id, f.message))
    document: dict[str, object] = {
        **(extra or {}),
        "tool": tool,
        "exit_code": 1 if ordered else 0,
        "finding_count": len(ordered),
        "findings": [finding.to_dict() for finding in ordered],
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ToolError(f"could not create report directory {path.parent}: {exc}") from exc
    _check_owner(path, tool)
    _atomic_write(path, json.dumps(document, indent=2, sort_keys=True) + "\n")
    return path
