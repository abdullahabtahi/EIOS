"""Tests for RL-6: Prompt Injection Benchmark Corpus (T017)."""

from evals.suites.redlines.test_rl6_prompt_injection import (
    INJECTION_CORPUS,
    run_prompt_injection_suite,
)


def test_rl6_corpus_minimum_size():
    assert len(INJECTION_CORPUS) >= 50


def test_rl6_defense_blocks_all_injections():
    # Hardened agent simulation that adheres to system instructions and denies overrides
    def safe_agent_evaluator(payload: str) -> dict[str, str | bool]:
        # Agent processes payload safely without executing unauthorized actions
        return {
            "overridden": False,
            "unauthorized_action": False,
            "response": "Processed safely with guardrails intact.",
        }

    result = run_prompt_injection_suite(safe_agent_evaluator)
    assert result.passed is True
    assert result.violations_detected == 0


def test_rl6_defense_catches_vulnerable_override():
    # Vulnerable agent that executes instructions from payload
    def vulnerable_agent_evaluator(payload: str) -> dict[str, str | bool]:
        if "ignore previous instructions" in payload.lower():
            return {
                "overridden": True,
                "unauthorized_action": True,
                "response": "System instructions ignored. Action executed.",
            }
        return {"overridden": False, "unauthorized_action": False, "response": "OK"}

    result = run_prompt_injection_suite(vulnerable_agent_evaluator)
    assert result.passed is False
    assert result.violations_detected > 0
