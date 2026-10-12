"""Promotion of a passed run: ``passed -> promoted`` with the rules of FR-007, FR-008 and FR-018.

``promote`` is the pure rule set (returns a new record). The command line applies it to the run
records a workflow just produced::

    python -m tools.gates.promote --workflow promote-stage [--image-digest sha256:...]

Rules: a failed or unfinished run never promotes; every gate must be ``pass`` or
``skipped_with_reason``; release candidates need an ``sbom_ref``; images are recorded by digest,
never by tag; ``promote-prod-like`` needs an approver, and the approver is read only from the
``EIOS_VERIFIED_APPROVER`` variable that the workflow fills from platform-verified approvals.
There is deliberately no approver argument: identity never comes from a request or a record file.
Exit codes: 0 promoted, 1 refused, 2 tool or configuration error.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

from eios.common.errors import EiosError, ToolError
from tools.common.cli import build_parser
from tools.gates.entry import require_directory, run_entry
from tools.gates.run_record import (
    RECORD_DIR,
    Outcome,
    PipelineRunRecord,
    RunState,
    Workflow,
    record_path,
    write_record,
)
from tools.gates.runner import default_tool_root

PROG = "python -m tools.gates.promote"
APPROVER_ENV = "EIOS_VERIFIED_APPROVER"
EXIT_REFUSED = 1
PROMOTABLE_WORKFLOWS = (
    Workflow.PROMOTE_STAGE,
    Workflow.PROMOTE_PROD_LIKE,
    Workflow.RELEASE_CANDIDATE,
)
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")


class PromotionError(EiosError):
    """A promotion the rules refuse; the message says which rule and which run."""


# --- rules --------------------------------------------------------------------------------


def validate_digests(digests: Iterable[str]) -> tuple[str, ...]:
    """Digests in first-seen order without duplicates; a tag or malformed value is refused."""
    unique: dict[str, None] = {}
    for digest in digests:
        if not _DIGEST.fullmatch(digest):
            raise PromotionError(
                f"image reference {digest!r} is not a sha256 digest; images are promoted "
                "by digest, never by tag"
            )
        unique.setdefault(digest)
    return tuple(unique)


def _check_state(record: PipelineRunRecord) -> None:
    if record.state is RunState.FAILED:
        raise PromotionError(f"run {record.run_id} failed; a failed run is never promoted")
    if record.state is not RunState.PASSED:
        raise PromotionError(
            f"run {record.run_id} is {record.state.value}; only a passed run can be promoted"
        )
    failing = [r.gate_id for r in record.gate_results if r.outcome is Outcome.FAIL]
    if failing:
        raise PromotionError(f"run {record.run_id} has failing gates: {', '.join(failing)}")


def _check_workflow_rules(record: PipelineRunRecord, approver: str | None) -> None:
    if record.workflow is Workflow.PROMOTE_PROD_LIKE:
        if approver is None:
            raise PromotionError(
                f"run {record.run_id}: prod-like promotion needs an approver from verified "
                "identity claims"
            )
    elif approver is not None:
        raise PromotionError(
            f"run {record.run_id}: an approver is only accepted for prod-like promotion"
        )
    if record.workflow is Workflow.RELEASE_CANDIDATE and not record.sbom_ref:
        raise PromotionError(f"run {record.run_id}: a release candidate needs an sbom_ref")
    if record.workflow is Workflow.PR:
        raise PromotionError(f"run {record.run_id}: pull-request runs are never promoted")


def promote(
    record: PipelineRunRecord,
    *,
    verified_approver: str | None = None,
    image_digests: Sequence[str] = (),
) -> PipelineRunRecord:
    """Return ``record`` promoted, or raise ``PromotionError``. The input is never changed."""
    approver = None if verified_approver is None else verified_approver.strip()
    if approver == "" and record.workflow is Workflow.PROMOTE_PROD_LIKE:
        approver = None
    _check_state(record)
    _check_workflow_rules(record, approver)
    digests = validate_digests((*record.artefact_digests, *image_digests))
    return record.with_artefact_digests(digests).promote(verified_approver=approver)


# --- command line -------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = build_parser("gates.promote", "Promote the passed run records of one workflow.")
    parser.add_argument(
        "--workflow",
        required=True,
        choices=[w.value for w in PROMOTABLE_WORKFLOWS],
        help="workflow whose run records are promoted",
    )
    parser.add_argument("--tool-root", type=Path, default=default_tool_root())
    parser.add_argument(
        "--image-digest",
        action="append",
        default=[],
        dest="image_digests",
        help="image digest (sha256:...) to record; repeatable",
    )
    return parser


def _read_record(path: Path) -> PipelineRunRecord:
    try:
        return PipelineRunRecord.from_document(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError, EiosError) as exc:
        raise ToolError(f"cannot read run record {path.name}: {exc}") from exc


def _load_records(repo_root: Path, workflow: Workflow) -> tuple[PipelineRunRecord, ...]:
    paths = sorted((repo_root / RECORD_DIR).glob("*.json"))
    records = tuple(r for r in map(_read_record, paths) if r.workflow is workflow)
    if not records:
        raise ToolError(
            f"no run record for workflow {workflow.value} under {RECORD_DIR.as_posix()}; "
            "run the gates first"
        )
    return records


def _promote_all(
    records: Iterable[PipelineRunRecord], approver: str | None, digests: Sequence[str]
) -> tuple[PipelineRunRecord, ...]:
    """All-or-nothing: every record is checked before any file is written."""
    return tuple(
        r
        if r.state is RunState.PROMOTED
        else promote(r, verified_approver=approver, image_digests=digests)
        for r in records
    )


def _handle(args: argparse.Namespace) -> int:
    repo_root = require_directory(args.repo_root, "repo root")
    workflow = Workflow(args.workflow)
    records = _load_records(repo_root, workflow)
    approver = os.environ.get(APPROVER_ENV) if workflow is Workflow.PROMOTE_PROD_LIKE else None
    try:
        promoted = _promote_all(records, approver, args.image_digests)
    except PromotionError as exc:
        print(f"{PROG}: refused: {exc}", file=sys.stderr)
        return EXIT_REFUSED
    for before, after in zip(records, promoted, strict=True):
        if before.state is not RunState.PROMOTED:
            write_record(after, repo_root, args.tool_root)
            path = record_path(repo_root, after.run_id)
            print(f"promoted run {after.run_id} ({workflow.value}): {path}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    return run_entry(PROG, _build_parser(), _handle, argv)


if __name__ == "__main__":
    sys.exit(main())
