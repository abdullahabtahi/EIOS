"""The structured answer an operator receives (spec 021 FR-004). Text plus everything needed to check it."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from eios.common.validation import StrictModel
from eios.ontology.omcp.port.contracts import DataOrigin


class FigureRef(StrictModel):
    """One figure shown in the text, with the governed result it was resolved from."""

    fact_id: str
    value: float
    unit: str
    as_of: datetime
    data_origin: DataOrigin
    source: str
    text: str


class SourceRef(StrictModel):
    """One passage shown in the answer: the document, where in it, and the text as the regulator wrote it."""

    passage_id: str
    document_id: str
    title: str
    jurisdiction: str
    pages: str
    text: str
    data_origin: DataOrigin


class Answer(StrictModel):
    text: str
    figures: tuple[FigureRef, ...] = ()
    citations: tuple[str, ...] = ()  # the sources of the results the figures came from
    sources: tuple[SourceRef, ...] = ()  # passages quoted in the text, in order of appearance
    proposed_actions: tuple[dict[str, Any], ...] = ()
    view_commands: tuple[
        dict[str, Any], ...
    ] = ()  # for the workstation; not acted on by this feature
    data_origin: DataOrigin = DataOrigin.FIXTURE
    is_replay_fallback: bool = False
    fallback_reason: str | None = None
    blocked: bool = False
    block_reason: str | None = None
    failed_closed: bool = (
        False  # no supportable answer after the bounded attempts; no figure is shown
    )
    attempts: int = Field(default=1, ge=0)
