"""Helpers every handler uses to fill the result envelope the same way."""

from typing import Any

from eios.ontology.config import SecurityMarking
from eios.ontology.omcp.port.contracts import DataOrigin
from eios.ontology.omcp.port.readmodels import ReadModels

FIXTURE_NOTE = "FIXTURE [ILLUSTRATIVE]"  # every current result is fixture data (data-strategy R1)


def envelope(
    ctx: ReadModels,
    capability: str,
    entity_id: str | None,
    source: str,
    units: dict[str, str],
    markings: tuple[SecurityMarking, ...] = (),
    untrusted: bool = False,
) -> dict[str, Any]:
    return {
        "capability": capability,
        "entity_id": entity_id,
        "as_of": ctx.clock(),
        "data_origin": DataOrigin.FIXTURE,
        "source": source,
        "markings": markings,
        "units": units,
        "untrusted": untrusted,
    }
