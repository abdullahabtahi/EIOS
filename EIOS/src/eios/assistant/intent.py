"""What the operator is asking about and how much they want, read from the question before any model call.

Two facts decide most of an answer's usefulness and neither needs a model: which entity the question is about (the one
it names, else the one on screen) and whether it is a broad question ("expound", "tell me more", "what should I do")
that wants the full picture rather than one figure. Both are plain pattern matches, so they cost no time and cannot
invent a figure; the tools still return every value and the assembler still checks every figure.
"""

from __future__ import annotations

import re

from eios.ontology.omcp.port.principal import Workstation

BROAD_KEY = "temp:broad"  # this turn asks for the full picture
ON_SCREEN_KEY = (
    "temp:entity_on_screen"  # the entity on screen when the question names a different one
)

_ACCOUNT = re.compile(r"\bCR[-\s]?(\d{4,6})\b", re.IGNORECASE)
_PARTNER = re.compile(r"\b(PTR|AP|P)[-\s]?(\d{2,5})\b", re.IGNORECASE)
_BROAD = re.compile(
    r"\b(?:expound|elaborate|tell me more|more (?:detail|about|on)|explain|overview|summari[sz]e|"
    r"walk me through|deep.?dive|full picture|everything|what should i do|what do i do|what can i do|"
    r"next steps?|brief me|assess|analy[sz]e)\b",
    re.IGNORECASE,
)


def named_entity(workstation: Workstation, question: str) -> str | None:
    """The account or partner id the question names, written as the system writes it ("PTR 9699" is PTR-9699)."""
    if workstation in {Workstation.AML_INVESTIGATOR, Workstation.GEOSPATIAL}:
        found = _ACCOUNT.search(question)
        return f"CR{found.group(1)}" if found else None
    if workstation is Workstation.PARTNER_MANAGER:
        found = _PARTNER.search(question)
        return f"{found.group(1).upper()}-{found.group(2)}" if found else None
    return None


def resolve_entity(
    workstation: Workstation, question: str, on_screen: str | None
) -> tuple[str | None, str | None]:
    """(entity to answer about, entity named in the question when it differs from the one on screen)."""
    named = named_entity(workstation, question)
    if named and named.upper() != (on_screen or "").upper():
        return named, named
    return on_screen, None


def is_broad(question: str) -> bool:
    return bool(_BROAD.search(question))
