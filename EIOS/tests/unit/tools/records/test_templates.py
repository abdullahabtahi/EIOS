"""The ADR and spike templates carry every required field and fail until filled in."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests.support import decisions_repo as dr
from tools.adr_check.repo import check_repo
from tools.common.findings import Finding

DOCS = Path(__file__).resolve().parents[4] / "docs" / "adr"
ADR_TEMPLATE = DOCS / "_template-adr.md"
SPIKE_TEMPLATE = DOCS / "_template-spike.md"
ADR_HEADINGS = (
    "Status",
    "Date",
    "Context",
    "Options considered",
    "Decision",
    "Consequences",
    "Evidence",
    "Revisit when",
)
SPIKE_HEADINGS = (
    "Id",
    "Question",
    "Time box",
    "Owner",
    "State",
    "Method",
    "Data",
    "Result",
    "Decision",
    "Date",
    "Outcome",
    "Linked ADR",
)
_ADR_FILLED = {
    "Status": "Accepted",
    "Date": "2026-02-01",
    "Context": "Why this is a decision.",
    "Options considered": "- A: one, drawback cost\n- B: two, drawback surface",
    "Decision": "Take option A.",
    "Consequences": "Simple.",
    "Evidence": "Backfilled from a decision taken before F00; see docs/foundry.md.",
    "Revisit when": "Constraints change.",
}
_SPIKE_FILLED = {
    "Id": "S-03",
    "Question": "Does it scale?",
    "Time box": "1 day [TARGET]",
    "Owner": "platform-team",
    "State": "closed",
    "Method": "Time it.",
    "Data": "Synthetic.",
    "Result": "Linear.",
    "Decision": "Keep it.",
    "Date": "2026-02-02",
    "Outcome": "Ceiling found.",
    "Linked ADR": "ADR-001",
}


def _fill(template: Path, values: dict[str, str], title: str) -> str:
    text = template.read_text(encoding="utf-8")
    text = re.sub(r"^# (ADR|S)-NN+: Title$", title, text, flags=re.MULTILINE)
    for heading, value in values.items():
        pattern = rf"(## {re.escape(heading)}\n\n)<!--.*?-->"
        text, count = re.subn(pattern, lambda m: m[1] + value, text, flags=re.DOTALL)  # noqa: B023
        assert count == 1, heading
    return text


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    return dr.materialise(tmp_path / "repo")


@pytest.mark.parametrize(
    ("template", "headings"), [(ADR_TEMPLATE, ADR_HEADINGS), (SPIKE_TEMPLATE, SPIKE_HEADINGS)]
)
def test_template_has_every_field_heading_and_an_instruction(
    template: Path, headings: tuple[str, ...]
) -> None:
    text = template.read_text(encoding="utf-8")
    for heading in headings:
        assert re.search(rf"^## {re.escape(heading)}\n\n<!-- .+ -->$", text, re.MULTILINE), heading


def test_adr_template_lists_status_values_and_honest_drawback_and_backfill_note() -> None:
    text = ADR_TEMPLATE.read_text(encoding="utf-8")
    assert "Proposed | Accepted | Superseded by ADR-XXX" in text
    assert "honest drawback" in text
    assert "backfilled" in text


def test_filled_adr_template_passes(repo: Path) -> None:
    text = _fill(ADR_TEMPLATE, _ADR_FILLED, "# ADR-007: Filled in")
    dr.write(repo, "docs/adr/007-filled-in.md", text)
    dr.replace(
        repo,
        "docs/spikes_and_adrs.md",
        "| ADR-006 | Ledger anchors | Proposed | — | — |",
        "| ADR-006 | Ledger anchors | Proposed | — | — |\n"
        "| ADR-007 | Filled in | Accepted | — | — |",
    )
    assert check_repo(repo) == []


def test_filled_spike_template_passes(repo: Path) -> None:
    dr.write(
        repo,
        "docs/adr/S-03-filled-in.md",
        _fill(SPIKE_TEMPLATE, _SPIKE_FILLED, "# S-03: Filled in"),
    )
    assert check_repo(repo) == []


def test_unfilled_adr_template_fails_with_empty_field_messages(repo: Path) -> None:
    dr.write(repo, "docs/adr/008-unfilled.md", ADR_TEMPLATE.read_text(encoding="utf-8"))
    found: list[Finding] = [f for f in check_repo(repo) if f.file.endswith("008-unfilled.md")]
    empty = {f.rule_id for f in found if "empty" in f.message}
    assert {
        "adr.field.status",
        "adr.field.date",
        "adr.field.context",
        "adr.field.options",
        "adr.field.consequences",
        "adr.field.revisit_when",
    } <= empty


def test_unfilled_spike_template_fails_with_empty_field_messages(repo: Path) -> None:
    dr.write(repo, "docs/adr/S-04-unfilled.md", SPIKE_TEMPLATE.read_text(encoding="utf-8"))
    found: list[Finding] = [f for f in check_repo(repo) if f.file.endswith("S-04-unfilled.md")]
    empty = {f.rule_id for f in found if "empty" in f.message}
    assert {"spike.field.question", "spike.field.time_box", "spike.field.owner"} <= empty
    assert "spike.field.state" in {f.rule_id for f in found}


def test_repo_check_skips_the_real_templates(repo: Path) -> None:
    dr.write(repo, "docs/adr/_template-adr.md", ADR_TEMPLATE.read_text(encoding="utf-8"))
    dr.write(repo, "docs/adr/_template-spike.md", SPIKE_TEMPLATE.read_text(encoding="utf-8"))
    assert check_repo(repo) == []
