"""Replay an answer's figures: derive each one again from its fact id, through the governed port, and compare.

An assistant answer shows only figures a tool returned in that turn. This check goes one step further for the reader:
it asks the same capability again, as the same operator in the same workstation, and reports whether every figure
comes back the same. A figure that cannot be derived again (the capability refuses, the data is gone) is reported as
such, never as a match.
"""

from __future__ import annotations

import functools
import logging
import math
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field

from eios.cockpit.auth import Operator, current_operator
from eios.cockpit.ratelimit import limit_verify
from eios.common.validation import StrictModel
from eios.dataplane.plane import read_models
from eios.ontology.omcp.port.catalogue import build_port
from eios.ontology.omcp.port.contracts import PortError
from eios.ontology.omcp.port.principal import principal_for
from eios.ontology.omcp.port.readmodels import ReadModels

_LOG = logging.getLogger("eios.cockpit.copilot_verify")
VERIFY_PATH = "/api/cockpit/copilot/verify"
# [ASSUMPTION] an answer cites a handful; the bound keeps one request to a few port calls.
MAX_FIGURES = 20

router = APIRouter(tags=["Cockpit Copilot"], dependencies=[Depends(current_operator)])


class ShownFigure(StrictModel):
    fact_id: str = Field(min_length=3, max_length=200)
    value: float


class VerifyRequest(StrictModel):
    role: str = Field(min_length=1, max_length=40)
    figures: list[ShownFigure] = Field(min_length=1, max_length=MAX_FIGURES)


@functools.cache
def _models() -> ReadModels:
    """The served read models, with their fact resolver bound to a port over them."""
    models = read_models()
    build_port(models)
    return models


def _same(shown: float, now: float) -> bool:
    return math.isclose(shown, now, rel_tol=1e-9, abs_tol=1e-9)


@router.post(VERIFY_PATH, dependencies=[Depends(limit_verify)])
def verify_figures(
    req: VerifyRequest, operator: Operator | None = Depends(current_operator)
) -> dict[str, Any]:
    try:
        principal = principal_for(operator.uid if operator else None, req.role.strip().lower())
    except PortError as exc:
        raise HTTPException(status_code=422, detail=exc.error.message) from exc
    facts = _models().facts
    rows: list[dict[str, Any]] = []
    for figure in req.figures:
        try:
            again = facts.resolve(principal, figure.fact_id)
        except PortError as exc:
            rows.append(
                {
                    "fact_id": figure.fact_id,
                    "shown": figure.value,
                    "now": None,
                    "match": False,
                    "error": exc.error.code.value,
                }
            )
            continue
        rows.append(
            {
                "fact_id": figure.fact_id,
                "shown": figure.value,
                "now": again.value,
                "unit": again.unit,
                "as_of": again.as_of.isoformat(),
                "data_origin": again.data_origin.value,
                "match": _same(figure.value, again.value),
                "error": None,
            }
        )
    matched = sum(1 for r in rows if r["match"])
    if matched < len(rows):
        _LOG.warning("replay: %s of %s figures did not match", len(rows) - matched, len(rows))
    return {"checked": len(rows), "matched": matched, "rows": rows}


def reset_for_testing() -> None:
    _models.cache_clear()
