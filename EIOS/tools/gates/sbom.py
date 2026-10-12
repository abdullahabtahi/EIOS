"""SBOM generation (T049, FR-011): a CycloneDX document of every locked dependency.

The generator is ``uv export --format cyclonedx1.5`` run offline against ``uv.lock``, so the
document describes exactly what the lockfile pins. The file lands under
``evals/reports/sbom/`` and its repo-relative path is the ``sbom_ref`` of the run record.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path

from eios.common.errors import ToolError
from tools.common.cli import run_tool
from tools.common.findings import Finding
from tools.gates import _exec

SBOM_DIR = Path("evals") / "reports" / "sbom"
_NAME_DIGEST_LENGTH = 12
_EXPORT_ARGS = (
    "export",
    "--format",
    "cyclonedx1.5",
    "--frozen",
    "--offline",
    "--all-groups",
    "--all-extras",
    "--preview-features",
    "sbom-export",
)


def _export(repo_root: Path) -> str:
    lock = repo_root / "uv.lock"
    if not lock.is_file():
        raise ToolError(f"uv.lock not found in {repo_root}; the SBOM is built from the lockfile")
    uv = _exec.require_executable("uv")
    result = _exec.run([uv, *_EXPORT_ARGS], repo_root)
    if result.returncode != 0:
        raise ToolError(f"uv export failed: {_exec.tail(result.stderr)}")
    return result.stdout


def _validate(document_text: str) -> None:
    try:
        document = json.loads(document_text)
    except ValueError as exc:
        raise ToolError(f"uv export produced invalid JSON: {exc}") from exc
    if not isinstance(document, dict) or document.get("bomFormat") != "CycloneDX":
        raise ToolError("uv export did not produce a CycloneDX document")


def _write_atomic(path: Path, text: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        Path(tmp_name).replace(path)
    except OSError as exc:
        raise ToolError(f"could not write SBOM {path}: {exc}") from exc


def generate_sbom(repo_root: Path) -> Path:
    """Write the SBOM for ``repo_root``'s lockfile and return its path.

    The file name carries a digest of ``uv.lock``, so one lockfile always maps to one name.
    """
    text = _export(repo_root)
    _validate(text)
    digest = hashlib.sha256((repo_root / "uv.lock").read_bytes()).hexdigest()
    path = repo_root / SBOM_DIR / f"sbom-{digest[:_NAME_DIGEST_LENGTH]}.cdx.json"
    _write_atomic(path, text)
    return path


def sbom_ref(repo_root: Path, sbom_path: Path) -> str:
    """The reference stored as ``sbom_ref``: a repo-relative POSIX path."""
    try:
        return sbom_path.relative_to(repo_root).as_posix()
    except ValueError as exc:
        raise ToolError(f"SBOM {sbom_path} is outside {repo_root}") from exc


def _run(args: argparse.Namespace) -> Sequence[Finding]:
    repo_root: Path = args.repo_root
    print(sbom_ref(repo_root, generate_sbom(repo_root)))
    return []


def main(argv: Sequence[str]) -> int:
    return run_tool("sbom", _run, argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
