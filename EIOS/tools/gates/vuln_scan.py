"""Dependency advisory gate (T050): audit the locked dependencies against published advisories.

``uv export`` renders ``uv.lock`` as pinned requirements; ``pip-audit`` checks each pin against
the advisory database (network required). Any advisory is a finding.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path

from eios.common.errors import ToolError
from tools.common.cli import run_tool
from tools.common.findings import Finding
from tools.gates import _exec

LOCK_NAME = "uv.lock"
_AUDIT_FLAGS = (
    "--no-deps",
    "--disable-pip",
    "--format",
    "json",
    "--progress-spinner",
    "off",
)

# Vulnerabilities that are blocked by upstream constraints and have been manually reviewed
_VULN_ALLOWLIST = {
    "CVE-2026-114603", # opentelemetry-api blocked by google-adk
    "PYSEC-2026-4320", # certifi
}


def _export_requirements(repo_root: Path) -> str:
    uv = _exec.require_executable("uv")
    argv = [uv, "export", "--format", "requirements.txt", "--frozen", "--offline"]
    argv += ["--no-hashes", "--no-emit-project", "--all-groups", "--all-extras"]
    result = _exec.run(argv, repo_root)
    if result.returncode != 0:
        raise ToolError(f"uv export failed: {_exec.tail(result.stderr)}")
    return result.stdout


def _run_pip_audit(requirements: str, repo_root: Path) -> str:
    """Return pip-audit's JSON. Exit status 1 means advisories were found, which is data."""
    with tempfile.TemporaryDirectory(prefix="eios-vuln-") as scratch:
        pins = Path(scratch) / "requirements.txt"
        pins.write_text(requirements, encoding="utf-8")
        argv = [sys.executable, "-m", "pip_audit", "--requirement", str(pins), *_AUDIT_FLAGS]
        result = _exec.run(argv, repo_root)
    if not result.stdout.strip():
        raise ToolError(f"pip-audit produced no output: {_exec.tail(result.stderr)}")
    return result.stdout


def _dependencies(text: str) -> list[dict[str, object]]:
    try:
        document = json.loads(text)
    except ValueError as exc:
        raise ToolError(f"pip-audit output is not JSON: {exc}") from exc
    deps = document.get("dependencies") if isinstance(document, dict) else None
    if not isinstance(deps, list) or not all(isinstance(d, dict) for d in deps):
        raise ToolError("pip-audit output has no 'dependencies' list")
    return deps


def parse_audit(text: str) -> list[Finding]:
    """One finding per advisory, located on ``uv.lock``."""
    findings: list[Finding] = []
    seen: set[tuple[object, object, object]] = set()
    for dep in _dependencies(text):
        vulns = dep.get("vulns") or []
        if not isinstance(vulns, list):
            raise ToolError(f"pip-audit 'vulns' for {dep.get('name')!r} is not a list")
        for vuln in vulns:
            key = (dep.get("name"), dep.get("version"), vuln["id"])
            if key in seen:
                continue
            seen.add(key)
            if vuln["id"] in _VULN_ALLOWLIST:
                continue
            fixes = ", ".join(str(v) for v in vuln.get("fix_versions") or []) or "no fix published"
            message = f"{dep.get('name')}=={dep.get('version')}: {vuln['id']} (fix: {fixes})"
            findings.append(Finding(LOCK_NAME, 0, str(vuln["id"]), message))
    return findings


def skipped_dependencies(text: str) -> list[str]:
    """Dependencies pip-audit could not audit, as ``name: reason``."""
    return [
        f"{d.get('name')}: {d['skip_reason']}" for d in _dependencies(text) if "skip_reason" in d
    ]


def audit(repo_root: Path) -> list[Finding]:
    if not (repo_root / LOCK_NAME).is_file():
        raise ToolError(f"{LOCK_NAME} not found in {repo_root}; nothing to audit")
    output = _run_pip_audit(_export_requirements(repo_root), repo_root)
    for skipped in skipped_dependencies(output):
        print(f"vuln_scan: warning: not audited: {skipped}", file=sys.stderr)
    return parse_audit(output)


def _run(args: argparse.Namespace) -> Sequence[Finding]:
    return audit(args.repo_root)


def main(argv: Sequence[str]) -> int:
    return run_tool("vuln_scan", _run, argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
