"""Unit tests for single-pass template rendering with trusted and untrusted slots."""

from __future__ import annotations

import pytest

from eios.common.errors import BoundaryValidationError
from eios.common.untrusted_text import wrap_untrusted
from eios.llm_gateway.render import render_prompt, template_slots


def test_trusted_slots_are_filled_verbatim() -> None:
    assert render_prompt("Hi {{name}}!", {"name": "Ada"}) == "Hi Ada!"


def test_untrusted_slots_render_a_delimited_block() -> None:
    wrapped = wrap_untrusted("body text", source="ticket")
    out = render_prompt("Note:\n{{untrusted:body}}", {"body": wrapped})
    assert out == f"Note:\n{wrapped.render_block()}"


def test_substitution_is_single_pass_so_inputs_cannot_inject_slots() -> None:
    out = render_prompt("{{a}} {{b}}", {"a": "{{b}}", "b": "real"})
    assert out == "{{b}} real"


def test_template_slots_lists_names_and_trust() -> None:
    slots = template_slots("{{a}} {{untrusted:b}} {{a}}")
    assert slots == {"a": False, "b": True}


def test_a_name_used_both_trusted_and_untrusted_is_rejected() -> None:
    with pytest.raises(BoundaryValidationError):
        template_slots("{{a}} {{untrusted:a}}")


def test_missing_input_is_rejected_by_name_only() -> None:
    with pytest.raises(BoundaryValidationError) as caught:
        render_prompt("{{a}}", {})
    assert caught.value.field_paths == ("inputs.a",)


def test_unexpected_input_is_rejected() -> None:
    with pytest.raises(BoundaryValidationError):
        render_prompt("{{a}}", {"a": "x", "extra": "y"})


def test_wrong_trust_kind_is_rejected_and_never_echoes_the_value() -> None:
    with pytest.raises(BoundaryValidationError) as caught:
        render_prompt("{{untrusted:a}}", {"a": "plain-secret-value"})
    assert "plain-secret-value" not in str(caught.value)
    with pytest.raises(BoundaryValidationError):
        render_prompt("{{a}}", {"a": wrap_untrusted("x", source="ticket")})


def test_non_string_values_are_rejected() -> None:
    with pytest.raises(BoundaryValidationError):
        render_prompt("{{a}}", {"a": 5})  # type: ignore[dict-item]


def test_text_that_only_resembles_a_slot_is_left_alone() -> None:
    assert render_prompt("{ {a} } {{ a }} {{A}} {{}}", {}) == "{ {a} } {{ a }} {{A}} {{}}"
