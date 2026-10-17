"""Evidence bundles in the cockpit: seal a decision turn, read a bundle back, replay it, and check one before staging.

`seal_turn` runs after a successful assistant turn that proposed a hold or drafted a SAR. The bundle id goes back with
the answer and inside each proposal's stage request, so staging the hold signs the evidence reference with the intent
(`check_for_stage`). `GET /api/cockpit/evidence/{id}` shows what was sealed; `POST .../replay` asks every recorded call
again through the governed port and compares figure by figure (rate-limited like the figure check).
"""

from __future__ import annotations

import functools
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from eios.assistant.runtime import TurnOutcome
from eios.cockpit.auth import Operator, current_operator
from eios.cockpit.ratelimit import limit_verify
from eios.dataplane.plane import read_models
from eios.evidence.bundle import BundleTooLarge, canonical, is_decision, ref, seal
from eios.evidence.replay import replay
from eios.evidence.store import BUNDLE_ID, Tampered, evidence_store
from eios.ontology.omcp.port.catalogue import build_port
from eios.ontology.omcp.port.contracts import PortError
from eios.ontology.omcp.port.principal import Principal, principal_for
from eios.ontology.omcp.port.service import GovernedToolPort

_LOG = logging.getLogger("eios.cockpit.evidence")
EVIDENCE_PATH = "/api/cockpit/evidence/{bundle_id}"
REPLAY_PATH = "/api/cockpit/evidence/{bundle_id}/replay"

router = APIRouter(tags=["Cockpit Evidence"], dependencies=[Depends(current_operator)])


def _json(value: Any) -> Any:
    """A JSON-safe copy (dates as ISO strings), so the bundle hashes the same bytes it stores."""
    return json.loads(json.dumps(value, default=str))


def seal_turn(principal: Principal, question: str, outcome: TurnOutcome) -> str | None:
    """Seal a decision turn and return its bundle id; None for any other turn, or when the evidence is too large."""
    answer = outcome.answer
    if outcome.status != "ok" or answer.failed_closed or answer.blocked:
        return None
    if not is_decision(t.name for t in outcome.tool_calls):
        return None
    try:
        bundle = seal(
            workstation=principal.workstation.value,
            operator_id=principal.uid,
            question=question,
            answer=_json(answer.model_dump(mode="json")),
            calls=[
                {
                    "name": t.name,
                    "arguments": _json(t.arguments),
                    "result": _json(t.result),
                    "error": t.error_code,
                }
                for t in outcome.tool_calls
            ],
            model_key=outcome.model_key,
            manifest=_json(outcome.manifest) if outcome.manifest is not None else None,
        )
    except BundleTooLarge as exc:
        _LOG.warning("decision turn not sealed: %s", exc)
        return None
    return evidence_store().put(bundle)


def with_bundle(body: dict[str, Any], bundle_id: str | None) -> dict[str, Any]:
    """The answer body naming its sealed evidence, and each proposal's stage request carrying it to the hub."""
    if bundle_id is None:
        return {**body, "evidence_bundle_id": None}
    proposals = [
        {**p, "stage_request": {**p["stage_request"], "evidence_bundle_id": bundle_id}}
        if isinstance(p.get("stage_request"), dict)
        else p
        for p in body.get("proposals", [])
    ]
    return {**body, "proposals": proposals, "evidence_bundle_id": bundle_id}


def check_for_stage(bundle_id: str, target_entity_id: str) -> str:
    """The `evidence_refs` entry for staging with this bundle: it must exist, be intact, and be about the target."""
    try:
        bundle = evidence_store().get(bundle_id)
    except Tampered as exc:
        raise HTTPException(
            status_code=409, detail="the evidence bundle no longer matches its hash"
        ) from exc
    if bundle is None:
        raise HTTPException(status_code=422, detail="no such evidence bundle")
    if target_entity_id not in canonical(bundle).decode():
        raise HTTPException(status_code=422, detail="the evidence bundle is not about this entity")
    return ref(bundle_id)


@functools.cache
def _port() -> GovernedToolPort:
    return build_port(read_models())


def _bundle(bundle_id: str) -> dict[str, Any]:
    if not BUNDLE_ID.fullmatch(bundle_id):
        raise HTTPException(status_code=422, detail="a bundle id is 64 lowercase hex characters")
    try:
        bundle = evidence_store().get(bundle_id)
    except Tampered as exc:
        raise HTTPException(
            status_code=409, detail="the evidence bundle no longer matches its hash"
        ) from exc
    if bundle is None:
        raise HTTPException(status_code=404, detail="no such evidence bundle")
    return bundle


@router.get(EVIDENCE_PATH)
def read_bundle(bundle_id: str) -> dict[str, Any]:
    bundle = _bundle(bundle_id)
    return {
        "bundle_id": bundle["bundle_id"],
        "intact": True,
        "schema": bundle["schema"],
        "sealed_at": bundle["sealed_at"],
        "workstation": bundle["workstation"],
        "question": bundle["question"],
        "answer": bundle["answer"].get("text"),
        "manifest": bundle.get(
            "manifest"
        ),  # None on a v1 bundle, sealed before manifests were kept
        "calls": [
            {"name": c["name"], "arguments": c["arguments"], "error": c.get("error")}
            for c in bundle["calls"]
        ],
    }


@router.post(REPLAY_PATH, dependencies=[Depends(limit_verify)])
def replay_bundle(
    bundle_id: str, operator: Operator | None = Depends(current_operator)
) -> dict[str, Any]:
    bundle = _bundle(bundle_id)
    try:
        principal = principal_for(operator.uid if operator else None, bundle["workstation"])
    except PortError as exc:
        raise HTTPException(status_code=422, detail=exc.error.message) from exc
    report = replay(bundle, _port(), principal)
    if not report["equal"]:
        _LOG.warning(
            "evidence replay of %s differs: %s figures", bundle_id, report.get("differing")
        )
    return report


def reset_for_testing() -> None:
    _port.cache_clear()
