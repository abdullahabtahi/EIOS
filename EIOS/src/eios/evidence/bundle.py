"""Seal a decision turn's evidence: every governed result it read, the answer it gave, and a SHA-256 over all of it.

A hold or a SAR is only as good as what it was based on. When an assistant turn proposes a hold or drafts a SAR, the
turn is sealed: the question, the answer with its cited figures and map moves, and each tool call with its arguments
and its full result. The bundle's id is the SHA-256 of its canonical JSON, so the id is the integrity check: change one
byte and it no longer matches. Staging the hold puts that id into the intent's `evidence_refs`, which the intent hub
signs (KMS, ECDSA P-256), so the approved decision names exactly the evidence it rested on. A replay (`replay.py`)
asks every recorded call again and shows whether the figures still hold.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from typing import Any

SCHEMA = "eios.evidence_bundle/v2"  # v2 adds `manifest`; a v1 bundle stays valid: its id hashes its own content
REF_PREFIX = "evidence-bundle:sha256:"
# [ASSUMPTION] a turn's results are tens of kilobytes; the bound keeps a bundle inside one Firestore document (1 MiB).
MAX_BYTES = 900_000
DECISION_TOOLS = frozenset({"propose_hold", "draft_sar"})


class BundleTooLarge(ValueError):
    """The turn read more than one bundle can hold; it is refused rather than truncated."""


def canonical(content: Mapping[str, Any]) -> bytes:
    """One byte form for one content: sorted keys, no whitespace, UTF-8. What the hash is taken over."""
    return json.dumps(content, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def digest(content: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical(content)).hexdigest()


def is_decision(tool_names: Iterable[str]) -> bool:
    """A turn is sealed when it proposed an action or drafted a SAR: the turns a human then decides on."""
    return any(name in DECISION_TOOLS for name in tool_names)


def seal(  # noqa: PLR0913 - keyword-only: each part of the bundle is named at the call
    *,
    workstation: str,
    operator_id: str,
    question: str,
    answer: Mapping[str, Any],
    calls: Iterable[Mapping[str, Any]],
    model_key: str | None,
    manifest: Mapping[str, Any] | None = None,
    sealed_at: datetime | None = None,
) -> dict[str, Any]:
    """The sealed bundle: its content plus `bundle_id`, the SHA-256 of that content.

    `manifest` is what produced the answer (assistant/manifest.py); `answer`, `manifest` and each call's `result`
    must already be JSON-safe (a model dumped in JSON mode)."""
    content = {
        "schema": SCHEMA,
        "sealed_at": (sealed_at or datetime.now(UTC)).isoformat(),
        "workstation": workstation,
        "operator_id": operator_id,
        "question": question,
        "model_key": model_key,
        "manifest": dict(manifest) if manifest is not None else None,
        "answer": dict(answer),
        "calls": [
            {
                "name": c["name"],
                "arguments": dict(c.get("arguments") or {}),
                "result": c.get("result"),
                "error": c.get("error"),
            }
            for c in calls
        ],
    }
    size = len(canonical(content))
    if size > MAX_BYTES:
        raise BundleTooLarge(
            f"the turn's evidence is {size} bytes, over the {MAX_BYTES}-byte bound"
        )
    return {**content, "bundle_id": digest(content)}


def intact(bundle: Mapping[str, Any]) -> bool:
    """Does the bundle still hash to its own id? False means a byte changed after sealing."""
    content = {k: v for k, v in bundle.items() if k != "bundle_id"}
    return bundle.get("bundle_id") == digest(content)


def ref(bundle_id: str) -> str:
    """How a signed intent names the bundle in `evidence_refs`."""
    return f"{REF_PREFIX}{bundle_id}"
