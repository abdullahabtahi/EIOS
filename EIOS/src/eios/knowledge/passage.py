"""A retrieved passage and the seam the assistant searches through.

The port tool depends on `RegulationIndex`, never on a vendor client, so the offline gates run on an in-memory index
and a deployed gateway on Agent Search. A passage carries exactly what a citation needs: the document, its issuer's
jurisdiction, the page span and the text as the document wrote it.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import Field

from eios.common.validation import StrictModel
from eios.ontology.omcp.port.contracts import DataOrigin

MAX_PASSAGE_CHARS = 2400  # [ASSUMPTION] a 500-token chunk is about 2000 characters; the cap bounds one result in the model's context


class Passage(StrictModel):
    passage_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{2,127}$")
    document_id: str
    title: str
    jurisdiction: str  # MT, LB, US, INTL
    kind: str  # legislation | regulator_guidance | typology | international_standard
    pages: str  # "41" or "41-42": text, because a page number is a label and not a figure
    text: str = Field(min_length=1, max_length=MAX_PASSAGE_CHARS)


class IndexUnavailable(Exception):
    """The index could not be reached or is not configured. Never answered with an empty hit list."""


class RegulationIndex(Protocol):
    origin: DataOrigin  # where the passages come from: LIVE for the acquired corpus, FIXTURE for a test double
    description: (
        str  # what the result's `source` field says, e.g. "agent_search:eios-regulations-dev"
    )

    def search(self, query: str, jurisdiction: str | None, limit: int) -> list[Passage]: ...
