"""Read-only parser for a spike record; no validation rules.

Parses the union of the field sets in `contracts/decision-and-spike-records.md` (id, question,
time box, owner, outcome, linked ADR, state) and `data-model.md` (method, data, result,
decision, date, status, unlocks). `Status` is read as `state` and `Unlocks` as `linked_adr`.
"""

import re
from dataclasses import dataclass

from tools.records.markdown import ABSENT, FieldValue, extract_fields, first_h1

_ALIASES: dict[str, tuple[str, ...]] = {
    "spike_id": ("Id",),
    "question": ("Question",),
    "time_box": ("Time box", "Timebox"),
    "owner": ("Owner",),
    "outcome": ("Outcome",),
    "linked_adr": ("Linked ADR", "Unlocks"),
    "state": ("State", "Status"),
    "method": ("Method",),
    "data": ("Data",),
    "result": ("Result",),
    "decision": ("Decision",),
    "date": ("Date",),
}
_HEADING = re.compile(r"^(?P<id>S-\d+)\s*:\s*(?P<title>.*)$")


@dataclass(frozen=True)
class SpikeRecord:
    """A spike as written. Every field is text as found, or ``ABSENT`` when not present."""

    source: str
    spike_id: FieldValue
    title: FieldValue
    question: FieldValue
    time_box: FieldValue
    owner: FieldValue
    outcome: FieldValue
    linked_adr: FieldValue
    state: FieldValue
    method: FieldValue
    data: FieldValue
    result: FieldValue
    decision: FieldValue
    date: FieldValue


def parse_spike(text: str, source: str) -> SpikeRecord:
    """Parse ``text`` (read from ``source``) into a ``SpikeRecord`` without judging content.

    An explicit ``Id`` field takes precedence over the ``S-NN`` in the first heading.
    """
    fields = extract_fields(text, _ALIASES)
    heading = first_h1(text)
    heading_id: FieldValue = ABSENT
    title: FieldValue = heading
    if isinstance(heading, str):
        match = _HEADING.match(heading)
        if match:
            heading_id, title = match["id"], match["title"]
    explicit_id = fields["spike_id"]
    return SpikeRecord(
        source=source,
        spike_id=heading_id if explicit_id is ABSENT else explicit_id,
        title=title,
        question=fields["question"],
        time_box=fields["time_box"],
        owner=fields["owner"],
        outcome=fields["outcome"],
        linked_adr=fields["linked_adr"],
        state=fields["state"],
        method=fields["method"],
        data=fields["data"],
        result=fields["result"],
        decision=fields["decision"],
        date=fields["date"],
    )
