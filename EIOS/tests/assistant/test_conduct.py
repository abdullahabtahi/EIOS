"""A draft may never show the model's own reasoning or the wording of its instructions to the operator."""

from __future__ import annotations

import pytest

from eios.assistant.assembly import Assembled, Rejected, assemble_draft
from eios.assistant.conduct import ECHO_WORDS, conduct_problems

INSTRUCTION = (
    "You are the AML investigator assistant in the Enterprise Intelligence cockpit. Answer in plain language for that "
    "job only. A question about cause is answered from the causal evidence tool alone: do not add the briefing or a "
    "what-if run unless the operator asks for them. Use your tools for every fact."
)


@pytest.mark.parametrize(
    "draft",
    [
        "Wait, rule 7 says the briefing is not added.",
        "Let's check the dossier for CR17831 first.\nThe ring is large.",
        "Let me think about which tool to use.",
        "Okay, so the user is asking about the ring.",
        "I need to look at the causal evidence before answering.",
        "The user is asking whether the ring is causal.",
        "Hmm, the dossier says something else.",
    ],
)
def test_narrated_reasoning_is_rejected(draft: str) -> None:
    assert conduct_problems(draft, INSTRUCTION)


@pytest.mark.parametrize(
    "draft",
    [
        "Per my instructions I cannot show that.",
        "The system prompt says to use tools.",
        "Rule 7 says the briefing is left out.",
    ],
)
def test_talk_about_the_instructions_is_rejected(draft: str) -> None:
    assert conduct_problems(draft, INSTRUCTION)


def test_copying_the_instruction_wording_is_rejected() -> None:
    copied = " ".join(INSTRUCTION.split()[20 : 20 + ECHO_WORDS + 2])
    assert conduct_problems(f"The answer is brief. {copied}", INSTRUCTION)


def test_a_short_phrase_shared_with_the_instruction_is_allowed() -> None:
    assert not conduct_problems("Answer in plain language: the ring is causal.", INSTRUCTION)


@pytest.mark.parametrize(
    "draft",
    [
        "The mule ring is causal: the placebo refuter passed.",
        "Wait times at the cashier rose last week.",
        "I cannot answer that because no tool covers it.",
        "These are the open alerts, highest risk first.",
        "Let us look at the risk score: it is high.",
    ],
)
def test_ordinary_answers_pass(draft: str) -> None:
    assert conduct_problems(draft, INSTRUCTION) == ()


def test_the_problem_never_quotes_the_draft() -> None:
    reasons = conduct_problems("Wait, rule 7 says secret wording.", INSTRUCTION)
    assert reasons and all("secret wording" not in r and "rule 7" not in r for r in reasons)


def test_without_an_instruction_only_the_narration_checks_run() -> None:
    assert conduct_problems("Let's check the dossier.", "")
    assert not conduct_problems("Answer in plain language for that job only.", "")


def test_assembly_rejects_a_monologue_so_it_is_redrafted() -> None:
    result = assemble_draft(
        "Wait, rule 7 says to stop.\nThe ring is causal.", facts={}, instruction=INSTRUCTION
    )
    assert isinstance(result, Rejected)
    assert any("reasoning" in p for p in result.problems)


def test_assembly_is_unchanged_for_a_clean_draft() -> None:
    result = assemble_draft("The ring is causal.", facts={}, instruction=INSTRUCTION)
    assert isinstance(result, Assembled)


def test_assembly_without_an_instruction_does_not_run_the_echo_check() -> None:
    assert isinstance(
        assemble_draft("Answer in plain language for that job only.", facts={}), Assembled
    )


_REAL_INSTRUCTION = (
    "2. If a tool returns an error or the data is not available, say so plainly and show no figure. "
    "5. A greeting, what is EIOS is not such a question: answer in a few plain sentences. EIOS is the Enterprise "
    "Intelligence Operating System: governed data, evidence and proposed actions for this workstation, where every "
    "figure comes from a governed tool and any change needs a second operator's approval. "
    "If the tool returns no passage, say the regulatory corpus has nothing that supports an answer, and quote nothing."
)


def test_wording_the_instruction_tells_the_model_to_say_is_allowed() -> None:
    assert not conduct_problems(
        "EIOS is the Enterprise Intelligence Operating System: governed data, evidence and proposed actions for "
        "this workstation, where every figure comes from a governed tool and any change needs a second operator's "
        "approval.",
        _REAL_INSTRUCTION,
    )
    assert not conduct_problems(
        "No passage was returned, so the regulatory corpus has nothing that supports an answer, and quote nothing.",
        _REAL_INSTRUCTION,
    )


def test_an_instruction_rule_read_out_loud_is_still_rejected() -> None:
    assert conduct_problems(
        "If a tool returns an error or the data is not available, say so plainly and show no figure.",
        _REAL_INSTRUCTION,
    )
