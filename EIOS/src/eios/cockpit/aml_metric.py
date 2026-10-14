"""One governed figure in the shape the dossier's provenance popover reads (spec 031)."""

from __future__ import annotations

from typing import Any

STEWARD = "AMLComplianceSteward"
ENGINE_NAME = "EngineAMLService"
CITATION = "[COMPUTED]"


def metric(
    metric_id: str, formatted: str, raw: float, as_of: str, *, engine_name: str = ENGINE_NAME
) -> dict[str, Any]:
    return {
        "metric_id": metric_id,
        "formatted_value": formatted,
        "raw_value": raw,
        "semantic_definition_version": "v1.2",
        "as_of_timestamp": as_of,
        "origin_engine": engine_name,
        "steward_role": STEWARD,
        "citation": CITATION,
    }
