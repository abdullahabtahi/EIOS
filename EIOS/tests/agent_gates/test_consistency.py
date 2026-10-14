"""The assistant must agree with the workstation (FR-026): 78% on screen cannot be 0.84 in the answer."""

from typing import Any

from eios.agent_gates.core.consistency import compare_to_payload

PAYLOAD = {
    "partner_id": "PTR-882",
    "churn_hazard_probability": 0.78,
    "login_decay_pct": -68.0,
    "realized_volume_30d_usd": 1_240_000.0,
}


def _record(answer: str) -> dict[str, Any]:
    return {
        "answer": answer,
        "question": "Why is PTR-882 at risk?",
        "entity_context": {"entity_id": "PTR-882"},
        "tool_calls": [],
    }


def test_a_different_value_for_a_field_on_screen_is_a_disagreement_naming_both() -> None:
    (diff,) = compare_to_payload(
        _record("PTR-882 shows an elevated churn probability of 0.84."), PAYLOAD
    )
    assert diff["payload_value"] == 0.78
    assert diff["answer_text"] == "0.84"
    assert diff["payload_path"].endswith("churn_hazard_probability")


def test_the_same_value_in_any_unit_form_agrees() -> None:
    assert compare_to_payload(_record("The churn hazard is 78%."), PAYLOAD) == []
    assert compare_to_payload(_record("Login activity fell 68%."), PAYLOAD) == []


def test_a_figure_about_something_not_on_screen_is_not_a_disagreement() -> None:
    assert compare_to_payload(_record("Net deposit turnover was $482,000."), PAYLOAD) == []
