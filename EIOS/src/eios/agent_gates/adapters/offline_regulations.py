"""Offline regulation passages for the scripted baseline.

They are invented test text, labelled as such in their titles, and the index that serves them reports the FIXTURE origin,
so an offline answer never claims to come from the acquired corpus. What the offline run shows is that routing, the quote
placeholder and the assembler work; retrieval quality is measured against the real index (`evals/knowledge`).
"""

from eios.knowledge.passage import Passage, RegulationIndex
from eios.knowledge.static_index import StaticIndex

PASSAGES = (
    Passage(
        passage_id="OFFLINE-FILING.c1",
        document_id="OFFLINE-FILING",
        title="Offline test passage: suspicious report filing",
        jurisdiction="MT",
        kind="regulator_guidance",
        pages="1",
        text="A subject person files a suspicious transaction report as soon as it knows or suspects that funds are the proceeds of criminal activity.",
    ),
    Passage(
        passage_id="OFFLINE-REDFLAGS.c1",
        document_id="OFFLINE-REDFLAGS",
        title="Offline test passage: red flag indicators",
        jurisdiction="LB",
        kind="typology",
        pages="1",
        text="Rapid movement of virtual assets between newly opened wallets with no apparent economic purpose is a red flag indicator for digital financial services.",
    ),
)


def offline_index() -> RegulationIndex:
    return StaticIndex(PASSAGES)
