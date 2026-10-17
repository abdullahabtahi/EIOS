"""The structured answer an operator receives (spec 021 FR-004). Text plus everything needed to check it."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

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


class VisualColumn(StrictModel):
    key: str
    label: str
    kind: Literal["text", "number"]
    unit: str | None = None


class VisualChart(StrictModel):
    """How to plot a visual's rows: the category or time column, and the number columns that share one unit."""

    type: Literal["line", "bar"]
    x: str
    y: tuple[str, ...]
    unit: str | None = None


class Visual(StrictModel):
    """A table or chart of a list a tool returned this turn. Every cell is the tool's value; the model only named the list."""

    kind: Literal["table", "chart"]
    source: str  # `<tool>.<field>`, as the tool result named it in `visual_sources`
    label: str
    columns: tuple[VisualColumn, ...]
    rows: tuple[dict[str, Any], ...]
    fact_ids: tuple[
        dict[str, str], ...
    ] = ()  # per row, the fact id of each cell that has one (replay re-derives them)
    chart: VisualChart | None = None
    as_of: datetime
    data_origin: DataOrigin
    citation: str


class Answer(StrictModel):
    text: str
    figures: tuple[FigureRef, ...] = ()
    citations: tuple[str, ...] = ()  # the sources of the results the figures came from
    sources: tuple[SourceRef, ...] = ()  # passages quoted in the text, in order of appearance
    proposed_actions: tuple[dict[str, Any], ...] = ()
    visuals: tuple[
        Visual, ...
    ] = ()  # tables and charts, drawn from this turn's tool results (visuals.py)
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
