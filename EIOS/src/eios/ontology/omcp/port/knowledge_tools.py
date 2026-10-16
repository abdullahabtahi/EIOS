"""Regulation retrieval (Phase 3): the one capability that reads the acquired regulatory corpus.

The result is untrusted text by construction: the documents come from outside the system, so the port marks the result
and the assistant treats a passage as data. A passage has no figure fields; its page span is a label. The model never
types what a rule says: it shows a passage with `{{quote:<passage_id>}}` and the assembler prints the passage from
this turn's result, so a deadline or threshold in a regulation reaches the operator exactly as the regulator wrote it.
"""

from enum import StrEnum

from pydantic import Field, field_validator

from eios.common.validation import StrictModel
from eios.knowledge.highlight import body_sentences, highlight
from eios.knowledge.passage import IndexUnavailable, Passage
from eios.ontology.omcp.port.common import envelope
from eios.ontology.omcp.port.contracts import PortError, ToolErrorCode, ToolResult
from eios.ontology.omcp.port.principal import Principal, Workstation
from eios.ontology.omcp.port.readmodels import ReadModels
from eios.ontology.omcp.port.registry import ToolSpec

READERS = (Workstation.AML_INVESTIGATOR, Workstation.COMPLIANCE_AUDITOR, Workstation.GEOSPATIAL)


class Jurisdiction(StrEnum):
    """The issuers in data/corpus/regulatory/manifest.yaml: Malta, Labuan, the United States, international bodies."""

    MT = "MT"
    LB = "LB"
    US = "US"
    INTL = "INTL"


BUDGET_MS = 4000.0  # [ASSUMPTION] one managed-search round trip; measured on the live index before it is trusted


class RegulationArgs(StrictModel):
    query: str = Field(min_length=3, max_length=300)
    jurisdiction: Jurisdiction | None = None
    limit: int = Field(
        default=3, ge=1, le=8
    )  # recall at 3 is full on the retrieval cases, and fewer passages means a faster draft

    @field_validator("jurisdiction", mode="before")
    @classmethod
    def _upper(cls, value: object) -> object:
        return value.upper() if isinstance(value, str) else value


class RegulationHits(ToolResult):
    query: str
    jurisdiction: str | None
    passages: list[Passage]
    note: str


def _annotated(passage: Passage, query: str) -> Passage:
    """The passage with its body sentences numbered and a fallback excerpt for the query."""
    numbered = tuple(f"s{i}: {t}" for i, t in enumerate(body_sentences(passage.text), start=1))
    return passage.model_copy(
        update={"sentences": numbered, "highlight": highlight(passage.text, query)}
    )


def search_regulations(ctx: ReadModels, _who: Principal, args: RegulationArgs) -> RegulationHits:
    index = ctx.knowledge
    if index is None:
        raise PortError(ToolErrorCode.DATA_UNAVAILABLE, "the regulatory index is not configured")
    try:
        found = index.search(
            args.query, args.jurisdiction.value if args.jurisdiction else None, args.limit
        )
    except IndexUnavailable:
        raise PortError(
            ToolErrorCode.DATA_UNAVAILABLE,
            "the regulatory index could not be reached",
            retryable=True,
        ) from None
    return RegulationHits(
        **envelope(
            ctx,
            "knowledge.regulation",
            None,
            index.description,
            {},
            untrusted=True,
            origin=index.origin,
        ),
        query=args.query,
        jurisdiction=args.jurisdiction.value if args.jurisdiction else None,
        passages=[_annotated(p, args.query) for p in found],
        note=(
            "Passages from the acquired regulatory corpus, by relevance."
            if found
            else "No passage in the acquired corpus supports this question."
        ),
    )


TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        "search_regulations",
        "knowledge.regulation",
        "knowledge",
        READERS,
        RegulationArgs,
        RegulationHits,
        search_regulations,
        BUDGET_MS,
    ),
)
