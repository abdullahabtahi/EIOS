"""Replay a sealed bundle: ask every recorded call again through the governed port and compare figure by figure.

The port applies the replaying operator's role and markings as it does to any call, in the bundle's workstation. The
replay equals the original when the bundle is intact and every figure every call returned is returned again with the
same value. A call that is refused or fails now is reported as such, never as a match. When the data has moved on
(a later as-of), the differences are listed rather than hidden: the bundle still holds what the decision saw.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any, Protocol

from eios.assistant.tools import figures_of
from eios.evidence.bundle import intact
from eios.ontology.omcp.port.principal import Principal

_MAX_DIFFERENCES = 50  # [ASSUMPTION] enough to see what moved; the count is always complete


class _Port(Protocol):
    def call(self, principal: Principal, tool: str, arguments: dict[str, Any]) -> Any: ...


def _same(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)


def _call_again(port: _Port, principal: Principal, call: Mapping[str, Any]) -> dict[str, Any]:
    recorded = call.get("result")
    row: dict[str, Any] = {"name": call["name"], "arguments": call.get("arguments") or {}}
    if not isinstance(recorded, dict):
        return {**row, "status": "not_replayed", "reason": "the call had no result when sealed"}
    outcome = port.call(principal, call["name"], dict(call.get("arguments") or {}))
    if outcome.error is not None:
        return {**row, "status": "failed", "reason": outcome.error.code.value}
    now = outcome.result.model_dump(mode="json")
    then_figures, now_figures = figures_of(recorded), figures_of(now)
    differences = [
        {"fact_id": fact_id, "then": value, "now": now_figures.get(fact_id)}
        for fact_id, value in sorted(then_figures.items())
        if fact_id not in now_figures or not _same(value, now_figures[fact_id])
    ]
    return {
        **row,
        "status": "equal" if not differences else "differs",
        "figures": len(then_figures),
        "differing": len(differences),
        "differences": differences[:_MAX_DIFFERENCES],
        "as_of_then": recorded.get("as_of"),
        "as_of_now": now.get("as_of"),
    }


def _flat(content: Mapping[str, Any], prefix: str = "") -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for key, value in content.items():
        path = f"{prefix}{key}"
        if isinstance(value, Mapping):
            flat.update(_flat(value, f"{path}."))
        else:
            flat[path] = value
    return flat


def compare_manifests(
    sealed: Mapping[str, Any] | None, current: Mapping[str, Any] | None
) -> dict[str, Any]:
    """Is the setup that produced the answer still the setup now? `changed` names each part that moved, by path.

    Not part of `equal`: that says whether the data came back the same. A different instruction, model or tool catalogue
    means the same question could end differently today, which a reader should see beside it. A bundle sealed before
    manifests were kept, or a setup that cannot be rebuilt now (a retired model), is said so, never called unchanged."""
    if sealed is None:
        return {"status": "unrecorded", "changed": []}
    if current is None:
        return {"status": "unavailable", "changed": []}
    then, now = _flat(sealed), _flat(current)
    changed = sorted(k for k in then.keys() | now.keys() if then.get(k) != now.get(k))
    return {"status": "changed" if changed else "unchanged", "changed": changed}


def replay(
    bundle: Mapping[str, Any],
    port: _Port,
    principal: Principal,
    current_manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if not intact(bundle):
        return {"bundle_id": bundle.get("bundle_id"), "intact": False, "equal": False, "calls": []}
    rows = [_call_again(port, principal, c) for c in bundle.get("calls", []) if not c.get("error")]
    compared = [r for r in rows if r["status"] in {"equal", "differs"}]
    return {
        "bundle_id": bundle["bundle_id"],
        "intact": True,
        "equal": bool(compared) and all(r["status"] == "equal" for r in rows),
        "figures": sum(r.get("figures", 0) for r in rows),
        "differing": sum(r.get("differing", 0) for r in rows),
        "manifest": compare_manifests(bundle.get("manifest"), current_manifest),
        "calls": rows,
    }
